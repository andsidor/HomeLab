terraform {
  required_version = ">= 1.10.0"

  backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.17"
    }
  }
}

variable "aws_region" {
  description = "Region AWS bucketa Velero."
  type        = string
  default     = "eu-north-1"
}

variable "backup_bucket_name" {
  description = "Nazwa bucketu utworzonego przez terraform/bootstrap."
  type        = string
}

variable "name_prefix" {
  description = "Prefiks nazwy dedykowanego użytkownika IAM Velero."
  type        = string
  default     = "homelab-sidor"

  validation {
    condition     = can(regex("^[a-z0-9]([a-z0-9-]{1,30}[a-z0-9])$", var.name_prefix))
    error_message = "name_prefix musi mieć 3-32 znaki: małe litery, cyfry lub myślniki; bez myślnika na końcu."
  }
}

variable "kubeconfig_path" {
  description = "Ścieżka do kubeconfig klastra RKE2."
  type        = string
  default     = "~/.kube/config"
}

variable "backup_schedule" {
  description = "Harmonogram Cron w UTC. 02:17 omija uruchomienia Garmina o pełnej i połówkowej godzinie."
  type        = string
  default     = "17 2 * * *"
}

variable "backup_ttl" {
  description = "Czas przechowywania backupu Velero."
  type        = string
  default     = "720h"
}

provider "aws" {
  region = var.aws_region
}

provider "helm" {
  kubernetes {
    config_path = pathexpand(var.kubeconfig_path)
  }
}

resource "aws_iam_user" "velero" {
  name = "${var.name_prefix}-velero-backup"
  path = "/homelab/"

  tags = {
    ManagedBy = "Terraform"
    Project   = "HomeLab"
    Purpose   = "VeleroS3Backup"
  }
}

resource "aws_iam_policy" "velero_s3" {
  name        = "${var.name_prefix}-velero-s3-backup"
  description = "Dostep Velero tylko do bucketu backupowego HomeLab."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket",
          "s3:ListBucketMultipartUploads"
        ]
        Resource = "arn:aws:s3:::${var.backup_bucket_name}"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:AbortMultipartUpload",
          "s3:DeleteObject",
          "s3:GetObject",
          "s3:ListMultipartUploadParts",
          "s3:PutObject"
        ]
        Resource = "arn:aws:s3:::${var.backup_bucket_name}/*"
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "velero_s3" {
  user       = aws_iam_user.velero.name
  policy_arn = aws_iam_policy.velero_s3.arn
}

resource "aws_iam_access_key" "velero" {
  user = aws_iam_user.velero.name
}

locals {
  aws_credentials_file = join("\n", [
    "[default]",
    "aws_access_key_id = ${aws_iam_access_key.velero.id}",
    "aws_secret_access_key = ${aws_iam_access_key.velero.secret}"
  ])

  velero_values = {
    namespace = {
      labels = {
        "pod-security.kubernetes.io/enforce" = "privileged"
      }
    }
    initContainers = [{
      name            = "velero-plugin-for-aws"
      image           = "velero/velero-plugin-for-aws:v1.14.0"
      imagePullPolicy = "IfNotPresent"
      volumeMounts = [{
        mountPath = "/target"
        name      = "plugins"
      }]
    }]
    credentials = {
      useSecret = true
      name      = "velero-aws-credentials"
      secretContents = {
        cloud = local.aws_credentials_file
      }
    }
    configuration = {
      backupStorageLocation = [{
        name     = "default"
        provider = "aws"
        bucket   = var.backup_bucket_name
        default  = true
        config   = { region = var.aws_region }
      }]
      volumeSnapshotLocation       = []
      defaultBackupStorageLocation = "default"
      defaultBackupTTL             = var.backup_ttl
    }
    snapshotsEnabled         = false
    deployNodeAgent          = true
    defaultVolumesToFsBackup = true
    nodeAgent = {
      podVolumePath = "/var/lib/kubelet/pods"
      podSecurityContext = {
        runAsUser = 0
      }
      containerSecurityContext = {
        privileged = true
      }
      tolerations = [{ operator = "Exists" }]
    }
    schedules = {
      daily = {
        schedule = var.backup_schedule
        template = {
          ttl                      = var.backup_ttl
          storageLocation          = "default"
          includedNamespaces       = ["*"]
          includeClusterResources  = true
          snapshotVolumes          = false
          defaultVolumesToFsBackup = true
        }
      }
    }
  }
}

resource "helm_release" "velero" {
  name             = "velero"
  repository       = "https://vmware-tanzu.github.io/helm-charts"
  chart            = "velero"
  version          = "12.2.2"
  namespace        = "velero"
  create_namespace = true
  wait             = true
  atomic           = true
  timeout          = 600

  values = [yamlencode(local.velero_values)]

  depends_on = [aws_iam_user_policy_attachment.velero_s3]
}

output "velero_backup_bucket" {
  description = "Bucket z kopiami klastra."
  value       = var.backup_bucket_name
}

output "velero_schedule" {
  description = "Codzienny harmonogram kopii w UTC."
  value       = var.backup_schedule
}