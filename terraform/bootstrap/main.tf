terraform {
  required_version = ">= 1.10.0"

  backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

variable "aws_region" {
  description = "Region AWS dla bucketów i zasobów."
  type        = string
  default     = "eu-north-1"
}

variable "name_prefix" {
  description = "Mały prefiks nazw; suffix random_id zapewnia globalną unikalność bucketów."
  type        = string
  default     = "homelab-sidor"

  validation {
    condition     = can(regex("^[a-z0-9]([a-z0-9-]{1,30}[a-z0-9])$", var.name_prefix))
    error_message = "name_prefix musi mieć 3-32 znaki: małe litery, cyfry lub myślniki; bez myślnika na końcu."
  }
}

provider "aws" {
  region = var.aws_region
}

resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  bucket_names = {
    state  = "${var.name_prefix}-tfstate-${random_id.suffix.hex}"
    backup = "${var.name_prefix}-velero-${random_id.suffix.hex}"
  }
}

resource "aws_s3_bucket" "this" {
  for_each = local.bucket_names

  bucket = each.value

  tags = {
    ManagedBy = "Terraform"
    Project   = "HomeLab"
    Purpose   = each.key
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_ownership_controls" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each = aws_s3_bucket.this

  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  dynamic "rule" {
    for_each = each.key == "state" ? [true] : []

    content {
      id     = "expire-old-state-versions"
      status = "Enabled"

      filter {
        prefix = ""
      }

      noncurrent_version_expiration {
        noncurrent_days = 365
      }
    }
  }

  dynamic "rule" {
    for_each = each.key == "backup" ? [true] : []

    content {
      id     = "expire-old-backup-object-versions"
      status = "Enabled"

      filter {
        prefix = ""
      }

      noncurrent_version_expiration {
        noncurrent_days = 60
      }
    }
  }
}

resource "aws_s3_bucket_policy" "require_tls" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource = [
        each.value.arn,
        "${each.value.arn}/*"
      ]
      Condition = {
        Bool = {
          "aws:SecureTransport" = "false"
        }
      }
    }]
  })
}

output "state_bucket_name" {
  description = "Bucket dla zdalnego stanu Terraform."
  value       = aws_s3_bucket.this["state"].bucket
}

output "backup_bucket_name" {
  description = "Bucket dla kopii Velero."
  value       = aws_s3_bucket.this["backup"].bucket
}