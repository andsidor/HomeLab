# Terraform: AWS state i kopie Velero

Ten katalog konfiguruje dwa osobne buckety S3: zdalny stan Terraform oraz kopie Velero. Stos `bootstrap` tworzy buckety, a `velero` tworzy ograniczone uprawnienia IAM i instaluje Velero w istniejącym klastrze RKE2 przez Helm.

Velero zapisuje zasoby Kubernetes ze wszystkich namespace'ów oraz zawartość wolumenów zamontowanych w podach przez file-system backup node-agent. Harmonogram to codziennie 02:17 UTC, retencja 30 dni. Nie są używane snapshoty EBS/CSI. Kopie obejmują PVC używane przez pody, nie dowolne pliki hosta ani warstwy obrazów kontenerów.

## Wymagania

- Terraform 1.10 lub nowszy, z dostępem do providerów AWS i Helm.
- Poświadczenia AWS lokalnie przez profil lub standardowy chain providera. Nie zapisuj kluczy w repozytorium.
- Działający kubeconfig RKE2, domyślnie `~/.kube/config`.

## Uruchomienie

Bootstrap musi utworzyć bucket, zanim można przenieść jego własny stan do S3. Pierwsze `apply` używa więc lokalnego stanu; zaraz potem migrujemy go do bucketa.

```bash
terraform -chdir=terraform/bootstrap init -backend=false
terraform -chdir=terraform/bootstrap apply
```

Po zatwierdzeniu planu migracja stanu bootstrap do S3:

```bash
terraform -chdir=terraform/bootstrap init -migrate-state \
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

Po przejrzeniu planu wykonaj `terraform apply` z tym samym argumentem `-var`.

Jeśli zmienisz region albo `name_prefix` w bootstrap, podaj te same wartości stosowi `velero` i odpowiednio zmień argument `region` w konfiguracji backendu.

## Sprawdzenie

```bash
kubectl -n velero get pods
kubectl -n velero get backupstoragelocation,schedules
kubectl -n velero get backups
```

Przy pierwszej kopii sprawdź, czy powstał `PodVolumeBackup` dla PVC, i wykonaj próbne odtworzenie do osobnego namespace/PVC. File-system backup kopiuje aktywny system plików, a nie atomowy snapshot; harmonogram jest ustawiony poza zwykłymi uruchomieniami CronJoba Garmina.

## Bezpieczeństwo

Dedykowany użytkownik IAM ma dostęp tylko do bucketu backupowego. Jego klucz jest tworzony przez Terraform i przekazywany do sekretu Kubernetes przez chart Helm, dlatego secret znajduje się także w stanie Terraform. Stan jest szyfrowany przez S3 i wersjonowany; ogranicz dostęp IAM do obu bucketów, bo odczyt stanu ujawnia klucz. Zasoby Terraform nie są wdrażane przez Argo CD.

Terraform nie przejmuje zarządzania pozostałymi aplikacjami HomeLab. Velero tworzy niezależny backup ich bieżących zasobów klastra i zamontowanych PVC.