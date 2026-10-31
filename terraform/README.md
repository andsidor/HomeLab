# Terraform: AWS state i kopie Velero

Ten katalog konfiguruje dwa osobne buckety S3: zdalny stan Terraform oraz kopie Velero. Stos `bootstrap` tworzy buckety, a `velero` tworzy ograniczone uprawnienia IAM i instaluje Velero w istniejącym klastrze RKE2 przez Helm.

Velero zapisuje zasoby Kubernetes ze wszystkich namespace'ów oraz zawartość wolumenów zamontowanych w podach przez file-system backup node-agent. Harmonogram to codziennie 02:17 UTC, retencja 30 dni. Nie są używane snapshoty EBS/CSI. Kopie obejmują PVC używane przez pody, nie dowolne pliki hosta ani warstwy obrazów kontenerów. Release Velero utrzymuje w namespace `garmin` mały pod `velero-volume-mounter`, który montuje PVC `garmin-data`; jest potrzebny, bo krótkotrwały CronJob Garmin zwykle nie działa w chwili backupu.

## Wymagania

- Terraform 1.10 lub nowszy, z dostępem do providerów AWS i Helm.
- Poświadczenia AWS lokalnie przez profil lub standardowy chain providera. Nie zapisuj kluczy w repozytorium.
- Działający kubeconfig RKE2, domyślnie `~/.kube/config`.

## Uruchomienie

Bootstrap musi utworzyć bucket, zanim można przenieść jego własny stan do S3. Pierwszy `apply` używa lokalnego stanu. Po utworzeniu bucketa dodajemy lokalną deklarację backendu i migrujemy state.

```bash
terraform -chdir=terraform/bootstrap init
terraform -chdir=terraform/bootstrap plan
terraform -chdir=terraform/bootstrap apply
```

Po zatwierdzeniu planu i utworzeniu bucketów, z katalogu repozytorium:

```bash
cp terraform/bootstrap/backend.tf.example terraform/bootstrap/backend.tf
terraform -chdir=terraform/bootstrap init -migrate-state -force-copy \\
  -backend-config="bucket=$(terraform -chdir=terraform/bootstrap output -raw state_bucket_name)" \
  -backend-config="key=bootstrap/terraform.tfstate" \
  -backend-config="region=eu-north-1" \
  -backend-config="use_lockfile=true"
```

Inicjalizacja stosu Velero z osobnym kluczem stanu i utworzenie planu:

```bash
terraform -chdir=terraform/velero init \
  -backend-config="bucket=$(terraform -chdir=terraform/bootstrap output -raw state_bucket_name)" \
  -backend-config="key=velero/terraform.tfstate" \
  -backend-config="region=eu-north-1" \
  -backend-config="use_lockfile=true"

terraform -chdir=terraform/velero plan \
  -var="backup_bucket_name=$(terraform -chdir=terraform/bootstrap output -raw backup_bucket_name)"
```

Po przejrzeniu planu wykonaj `terraform apply` z tym samym argumentem `-var`. Stos utworzy dedykowanego IAM usera, politykę ograniczoną do bucketa backupowego i pusty sekret Secrets Manager. Nie tworzy klucza IAM, więc jego wartość nie trafia do Terraform state.

## Dodanie klucza IAM do Secrets Manager

Najpierw sprawdź nazwę usera i sekretu z outputów Terraform. Użytkownik IAM nie powinien mieć innych polityk niż ta przypięta przez ten stos.

Utwórz klucz i przekaż jego dane bezpośrednio do Secrets Manager. Wymaga to `aws` CLI i `jq`; potok nie wypisuje wartości klucza na terminal:

```bash
terraform -chdir=terraform/velero output -raw velero_iam_user_name
terraform -chdir=terraform/velero output -raw velero_credentials_secret_name

aws iam create-access-key \\
  --user-name "$(terraform -chdir=terraform/velero output -raw velero_iam_user_name)" \\
  --output json \\
| jq -c '{access_key: .AccessKey.AccessKeyId, secret_access_key: .AccessKey.SecretAccessKey}' \\
| aws secretsmanager put-secret-value \\
    --secret-id "$(terraform -chdir=terraform/velero output -raw velero_credentials_secret_name)" \\
    --secret-string file:///dev/stdin
```

Klucz AWS używany przez External Secrets Operator (`awssm-secret`) musi mieć `secretsmanager:GetSecretValue` i `secretsmanager:DescribeSecret` dla sekretu `homelab/velero-backup`. Po zapisaniu wartości ESO zsynchronizuje ją do `velero/velero-aws-credentials`; chart Velero używa tego sekretu.

Nie zapisuj Access Key ID ani Secret Access Key w plikach `.tfvars`, zmiennych Terraform, logach CI ani repozytorium. AWS pozwala mieć maksymalnie dwa aktywne klucze na IAM usera; przy rotacji dodaj nowy, zaktualizuj sekret, poczekaj na synchronizację ESO, zweryfikuj backup, a następnie dezaktywuj i usuń poprzedni klucz.

Jeśli zmienisz region albo `name_prefix` w bootstrap, podaj te same wartości stosowi `velero` i odpowiednio zmień argument `region` w konfiguracji backendu.

## Sprawdzenie

```bash
kubectl -n velero get pods
kubectl -n velero get backupstoragelocation,schedules
kubectl -n velero get backups
```

Przy pierwszej kopii sprawdź, czy powstał `PodVolumeBackup` dla PVC, i wykonaj próbne odtworzenie do osobnego namespace/PVC. File-system backup kopiuje aktywny system plików, a nie atomowy snapshot; harmonogram jest ustawiony poza zwykłymi uruchomieniami CronJoba Garmina.

## Bezpieczeństwo

Dedykowany użytkownik IAM ma dostęp tylko do bucketu backupowego. Jego klucz przechowuje AWS Secrets Manager, a External Secrets Operator synchronizuje go do namespace `velero`; wartość klucza nie trafia do Terraform state. Ogranicz dostęp do bucketa ze stanem i sekretu w Secrets Manager. Zasoby Terraform nie są wdrażane przez Argo CD.

Terraform nie przejmuje zarządzania pozostałymi aplikacjami HomeLab. Velero tworzy niezależny backup ich bieżących zasobów klastra i zamontowanych PVC.