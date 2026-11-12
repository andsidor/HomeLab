# HomeLab

English | [Polski](#homelab-wersja-polska)

[![My Skills](https://skillicons.dev/icons?i=kubernetes,aws,docker,vim,bash,git,github,terraform,python,js,gpt&theme=light)](https://skillicons.dev)

**Also comfortable with**: SQL (Postgres, SQLite), CI/CD pipelines, Networking and Security (VPC, IAM), ChatGPT, Claude

## Overview

This repository describes a home Kubernetes (RKE2) environment managed declaratively with GitOps. Argo CD watches the `main` branch, deploys applications from Kustomize manifests and keeps the cluster in sync with the repository.

The project combines core cluster services with a Garmin data collector and a smart home stack built on Zigbee2MQTT and an MQTT broker. MetalLB exposes services on a local LAN address pool, Local Path Provisioner provides local volumes, and External Secrets Operator (ESO) syncs selected secrets from AWS Secrets Manager. Prometheus collects metrics and Grafana displays metrics and logs. Alloy collects Kubernetes pod logs and sends them to Loki, where they can be searched with LogQL. Zigbee sensors publish measurements over MQTT, and an exporter turns them into Prometheus metrics. Cloudflare Tunnel exposes Grafana, or a single public dashboard, outside the home network without opening router ports.

```mermaid
flowchart LR
  Git[GitHub: main] --> Root[Argo CD: root Application]
  Root --> Infra[MetalLB, storage, ESO]
  Root --> Monitor[Prometheus and Grafana]
  Root --> Garmin[Garmin CronJob]
  Garmin --> AWS[AWS Secrets Manager]
  Garmin --> PVC[(SQLite on PVC)]
  Garmin --> Pushgateway[Prometheus Pushgateway]
  Pushgateway --> Prometheus[Prometheus]
  Prometheus --> Grafana[Grafana]
  Root --> Loki[Loki log storage]
  Root --> Alloy[Alloy log collector]
  Alloy --> Loki
  Loki --> Grafana
  Root --> Z2M[Zigbee2MQTT + Mosquitto]
  Sensor[Zigbee sensor] --> Dongle[Sonoff dongle] --> Z2M
  Z2M -->|MQTT| Exporter[mqtt2prometheus]
  Exporter --> Prometheus
  Root --> CF[cloudflared]
  CF --> Grafana
  Terraform[Terraform] --> StateS3[(S3 Terraform state)]
  Terraform --> Velero[Velero on RKE2]
  Velero --> BackupS3[(S3 cluster backups)]
```

## Technologies

| Technology | Purpose |
| --- | --- |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> Kubernetes / RKE2 | Runs the cluster services. |
| <img src="https://cdn.simpleicons.org/argo" alt="" width="20" height="20" /> Argo CD | GitOps and automatic sync of applications from the repository. |
| <img src="https://cdn.simpleicons.org/argo" alt="" width="20" height="20" /> Argo Rollouts | Progressive delivery controller for Kubernetes Rollout resources. |
| <img src="https://cdn.simpleicons.org/renovate" alt="" width="20" height="20" /> Renovate | Checks dependencies weekly and opens GitHub pull requests; runs as a Kubernetes CronJob. |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> Kustomize | Composes Kubernetes manifests. |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> MetalLB | Exposes `LoadBalancer` services on the LAN. |
| <img src="https://cdn.simpleicons.org/rancher" alt="" width="20" height="20" /> Rancher Local Path Provisioner | Local volumes for applications. |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> External Secrets Operator | Syncs secrets from AWS Secrets Manager. |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> cert-manager | Manages TLS certificates for Kubernetes resources. |
| <img src="https://cdn.simpleicons.org/traefikproxy" alt="" width="20" height="20" /> Traefik | Ingress controller exposed through MetalLB. |
| <img src="https://cdn.simpleicons.org/istio" alt="" width="20" height="20" /> Istio | Service mesh control plane; workloads opt in to sidecar injection individually. |
| <img src="https://cdn.simpleicons.org/prometheus" alt="" width="20" height="20" /> <img src="https://cdn.simpleicons.org/grafana" alt="" width="20" height="20" /> Prometheus and Grafana | Metrics, dashboards, and email alerting through Alertmanager. |
| <img src="https://cdn.simpleicons.org/grafana" alt="" width="20" height="20" /> Loki and Alloy | Kubernetes pod log collection, storage, and search in Grafana. |
| <img src="https://cdn.simpleicons.org/terraform" alt="" width="20" height="20" /> Terraform | Manages AWS backup resources and installs Velero in the existing RKE2 cluster. |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> Velero | Backs up Kubernetes resources and mounted PVC data to Amazon S3. |
| <img src="https://cdn.simpleicons.org/python" alt="" width="20" height="20" /> <img src="https://cdn.simpleicons.org/garmin" alt="" width="20" height="20" /> Python and Garmin Connect Personal API | Fetches Garmin data, stores it in SQLite and publishes metrics. |
| <img src="https://cdn.simpleicons.org/zigbee2mqtt" alt="" width="20" height="20" /> Zigbee2MQTT | Handles Zigbee sensors through a Sonoff USB dongle and publishes readings to MQTT. |
| <img src="https://cdn.simpleicons.org/eclipsemosquitto" alt="" width="20" height="20" /> <img src="https://cdn.simpleicons.org/mqtt" alt="" width="20" height="20" /> Mosquitto (MQTT) | MQTT broker with authentication; credentials come from AWS through ESO. |
| <img src="https://cdn.simpleicons.org/prometheus" alt="" width="20" height="20" /> <img src="https://cdn.simpleicons.org/mqtt" alt="" width="20" height="20" /> mqtt2prometheus | Converts MQTT readings into Prometheus metrics. |
| <img src="https://cdn.simpleicons.org/cloudflare" alt="" width="20" height="20" /> Cloudflare Tunnel (`cloudflared`) | Remote access to Grafana without opening router ports. |

## Repository structure

| Path | Contents |
| --- | --- |
| `argocd/root-app.yaml` | Main Argo CD "app of apps" Application. |
| `argocd/kustomization.yaml` | List of applications and infrastructure managed by Argo CD. |
| `argocd/applications/` | Application definitions deployed from this repository. |
| `argocd/infrastructure/` | Cluster services and infrastructure configuration. |
| `argocd/infrastructure/loki.yaml` and `alloy.yaml` | Loki log storage and Alloy Kubernetes pod log collection. |
| `files/` | Screenshots used in this README. |
| `k8s/garmin-app/` | CronJob, PVC and secret configuration of the Garmin app. |
| `k8s/zigbee2mqtt/` | Zigbee2MQTT, Mosquitto, the `mqtt2prometheus` exporter and MQTT credentials. |
| `k8s/cloudflared/` | Cloudflare tunnel and the token secret pulled from AWS. |
| `k8s/argocd-access/` | Internal CA, Argo CD TLS certificate and direct MetalLB service. |
| `terraform/` | S3 buckets, remote Terraform state, Velero IAM credentials, and Helm release. |
| `garmin_app.py` | Fetches and stores Garmin data and publishes metrics. |

## GitOps

Once the cluster and Argo CD are ready, start the root application:

```bash
kubectl apply -f argocd/root-app.yaml
```

The root Application watches the `argocd/` directory. To add a new application, put its manifest in `argocd/applications/` or `argocd/infrastructure/` and list it in `argocd/kustomization.yaml`; without that entry Argo CD will not deploy it. Argo CD syncs changes from `main` automatically, removes resources deleted from the configuration (`prune`) and corrects manual drift (`selfHeal`).

## Services

- **Grafana** is exposed through MetalLB at `192.168.0.200`; Prometheus is the default data source. The `Zigbee`, `Zigbee3`, `Garmin`, and `Alerty` dashboards are provisioned from `argocd/infrastructure/grafana.yaml`.
- **Traefik** is exposed through MetalLB at `192.168.0.202`; use `ingressClassName: traefik` on Ingress resources. Its IngressClass is not the cluster default.
- **Argo CD** is reachable at `https://argocd.andrzejsidor.uk` through Traefik (`192.168.0.202`) or directly at `https://192.168.0.203`. cert-manager issues both DNS and IP SANs from an internal HomeLab CA; trust the CA root certificate on client devices.
- **Istio and Kiali** run in `istio-system`; workloads are not automatically injected and no Istio gateway is installed. Open Kiali at `http://192.168.0.204:20001`. Traefik remains the ingress controller.
- **Argo Rollouts** is installed in namespace `argo-rollouts` with its CRDs. Existing Deployments are unchanged; progressive delivery starts when an application is migrated to a `Rollout` resource.
- **cert-manager** is installed with its CRDs and issues Argo CD's certificate from the internal `homelab-internal-ca` ClusterIssuer. No public ACME issuer is configured.
- **Renovate** runs every Monday at 06:00 Europe/Warsaw in namespace `renovate` and opens PRs for `andsidor/HomeLab`. External Secrets reads the `GIT_KEY` token from `homelab/secrets` in AWS Secrets Manager.
- **Prometheus** keeps metrics for 90 days on a persistent volume (`local-path-retain` class, 10Gi).
- **Operational alerts** cover high node CPU, memory and filesystem usage, unavailable or pending Kubernetes workloads, Velero backup failures/staleness, Argo CD `OutOfSync`, and certificate expiry. Alertmanager is configured to send email through Gmail SMTP; its SMTP password is synced from AWS Secrets Manager (`homelab/secrets`, `smtp-auth-password`) by ESO into `alertmanager-smtp`. The local-path storage alert measures node filesystem usage, not individual PVC usage; per-PVC usage metrics are unavailable. Configuration is in Git, but successful email delivery should be verified in the cluster.
- **Loki and Alloy** collect Kubernetes pod logs and make them searchable in Grafana. Loki stores logs on a 10Gi `local-path-retain` volume with 14-day retention; Alloy runs as a DaemonSet and reads logs through the Kubernetes API.
- **Zigbee2MQTT** runs on the `debian` node with a Sonoff dongle, and its UI is exposed through MetalLB at `192.168.0.201:8080`. Readings go to the **Mosquitto** MQTT broker on topic `zigbee2mqtt/<device>`, and `mqtt2prometheus` exposes them to Prometheus.
- **MQTT credentials** (`mqtt-user`, `mqtt-password`) live in AWS Secrets Manager (`homelab/secrets`) and reach the cluster as the `mqtt-credentials` secret; anonymous access is disabled.
- **Cloudflare Tunnel** connects the cluster to Cloudflare using a token from AWS (`cloudflared-token`). The public route targets `http://grafana.monitoring.svc.cluster.local:80`; protect it with Cloudflare Access or expose only the public dashboard paths.
- **Garmin** runs as a CronJob every 30 minutes. The Personal API key is synced from AWS by ESO, data goes to SQLite on a 1Gi PVC (`garmin-data`), and metrics are pushed to the Pushgateway. The PVC was migrated with checksum and SQLite integrity verification; the previous 5Gi PV is retained for rollback.
- **Velero** runs in namespace `velero` and backs up cluster resources to S3 every 30 minutes at :07 and :37 UTC, with 7-day retention. It still skips Garmin PVC files: Velero reports the local-path `hostPath` volume as unsupported. Garmin files are not currently protected by Velero; CSI/EBS snapshots are also disabled.

## Log Analysis

In Grafana, open **Explore**, select the **Loki** data source, and run a LogQL query such as:

```logql
{namespace="zigbee2mqtt"}
{namespace="zigbee2mqtt"} |= "error"
```

Alloy runs as a DaemonSet and collects pod logs through the Kubernetes API. Loki is internal-only; logs are stored on a 10Gi `local-path-retain` volume for 14 days. Host journal logs and Kubernetes events are not collected. Treat logs as potentially sensitive and do not expose Loki or log queries through public Grafana dashboards.

## Screenshots / Zrzuty ekranu

Argo CD statuses and Grafana values change over time. The Secrets Manager image shows names and descriptions only, not secret values. Statusy Argo CD i wartości Grafany zmieniają się w czasie. Obraz Secrets Manager pokazuje tylko nazwy i opisy, bez wartości sekretów.

![AWS Secrets Manager inventory / Lista sekretów AWS Secrets Manager](files/sekret.png)

![Argo CD applications / Aplikacje Argo CD](files/argo.jpg)

![Terraform and Velero S3 buckets / Buckety S3 Terraform i Velero](files/s3.jpg)

![Grafana Zigbee dashboard / Dashboard Zigbee w Grafanie](files/grafana.png)

## Notes and commands

Debugging commands and lessons learned are collected in [HL-NOTE.md](HL-NOTE.md) (Polish and English sections). Never commit secrets or tokens; keep them in AWS Secrets Manager.

## Garmin app (Python)

```bash
pip install -r requirements.txt
python garmin_app.py --days 7 --activities 10 --out garmin_data
python garmin_app.py --download-fit        # also download activity files
```

- Authentication: a personal Garmin Connect Personal API key in `GARMIN_PERSONAL_API_KEY`.
- The API key is exchanged for a bearer token automatically; the token cache is stored in `~/.config/garmin`.
- Create the key in the [Garmin Connect settings](https://connect.garmin.com/app/settings/personalApiToken) and treat it like a password.

## Docker / Podman

Docker:

```bash
docker build -t garmin-app .
docker run -it --rm \
  --env GARMIN_PERSONAL_API_KEY \
  -v "$PWD/garmin_data:/data" \
  garmin-app --days 7
```

Podman:

```bash
podman build -t garmin-app .
podman run --rm -it \
  -e GARMIN_PERSONAL_API_KEY \
  -v "$PWD/garmin_data:/data:Z" \
  garmin-app --days 7
```

The `:Z` volume option relabels the directory for SELinux hosts. Set `GARMIN_PERSONAL_API_KEY` in the environment before running the container.

## Git / GitHub

```bash
git remote set-url origin https://github.com/andsidor/HomeLab.git
git add . && git commit -m "message" && git push -u origin main
```

## CI (`.github/workflows/ci.yml`)

- `codeql` - Python code analysis
- `python-security` - `bandit -r garmin_app.py`, `pip-audit -r requirements.txt`
- `podman-build` - builds the image with Podman and publishes `ghcr.io/andsidor/homelab:podman` and `podman-<commit-sha>` tags to GHCR on pushes and scheduled runs; pull requests build but do not publish
- `docker` - build, non-blocking Trivy SARIF scan for `CRITICAL` and `HIGH`, push to `ghcr.io/andsidor/homelab`

Notes:
- Actions use Node 24-compatible versions (checkout v7, setup-python v7, codeql v4, docker/* v4-v7, `create-github-app-token` v3.3.0).
- `aquasecurity/trivy-action` tags have a `v` prefix (e.g. `v0.36.0`).
- Trivy findings are uploaded as SARIF and appear in the Security tab. The CRITICAL blocking gate is currently commented out, so findings do not fail the build.
- Minimum required versions: `urllib3>=2.8.0`, `msgpack>=1.2.1`, `setuptools>=78.1.1` (in the Dockerfile).

## RKE2

```bash
curl -sfL https://get.rke2.io | sudo sh -
sudo systemctl enable --now rke2-server.service

mkdir -p ~/.kube
sudo cp /etc/rancher/rke2/rke2.yaml ~/.kube/config && sudo chown $USER ~/.kube/config
export PATH=$PATH:/var/lib/rancher/rke2/bin
kubectl get nodes

# token for joining nodes (rke2-agent)
sudo cat /var/lib/rancher/rke2/server/node-token
```

## Argo CD

```bash
kubectl create namespace argocd
kubectl apply -n argocd --server-side -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# initial password (user: admin)
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# UI: https://localhost:8080
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

Add a new application as an `Application` manifest in `argocd/applications/` or `argocd/infrastructure/`, then list its path in `argocd/kustomization.yaml`. In the manifest set `repoURL` to `https://github.com/andsidor/HomeLab.git` and `path` to the Kustomize directory. Start once with `kubectl apply -f argocd/root-app.yaml`; the root app deploys further applications after their manifests are added to Kustomize and pushed to Git.

Grafana (Helm chart in Argo CD) uses the existing Kubernetes secret `grafana-admin-local` (keys `admin-user` and `admin-password`). Access it with:

```bash
kubectl -n monitoring port-forward svc/grafana 3000:80
```

The UI is then available at `http://localhost:3000`.

Open the Istio dashboard at `http://192.168.0.204:20001` and authenticate with a Kubernetes token.

## External Secrets Operator + AWS

The `aws-secretsmanager` `ClusterSecretStore` connects ESO to AWS Secrets Manager in `eu-north-1` through the existing Kubernetes Secret `awssm-secret` in the `external-secrets` namespace. The store expects the keys `aws_access_key_id` and `aws_secret_access_key` in it; credentials must never be committed to Git.

Use IAM keys with `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret`, restricted to the ARNs of the required secrets in `eu-north-1`. With a custom KMS key also add a restricted `kms:Decrypt`. After syncing, check the store with `kubectl get clustersecretstore aws-secretsmanager`.

Secrets Manager inventory (names only; never document secret values):
- `homelab/secrets` contains workload values for Garmin, MQTT, Cloudflare Tunnel and the Renovate classic GitHub token (`GIT_KEY`).
- `homelab/velero-backup` contains the dedicated Velero IAM user's credentials.
- `homelab/rke2-etcd-backup` contains credentials for RKE2 etcd snapshots in S3.

Notes:
- Do not commit secrets (use Sealed Secrets / SOPS / External Secrets).
- A private GHCR package requires an `imagePullSecret` (token with `read:packages`).
- Grafana's `grafana-admin-local` Secret is synchronized from AWS `homelab/secrets` (`admin-user` and `admin-password`) by ESO.
- After the first Argo CD login change the admin password and delete `argocd-initial-admin-secret`.

## Terraform and Velero (AWS)

Terraform manages two separate S3 buckets in `eu-north-1`: `homelab-sidor-tfstate-265d7dd5` for remote state and `homelab-sidor-velero-265d7dd5` for Velero backups. Both use encryption, versioning, public access blocking, and a TLS-only bucket policy. Terraform state is locked with S3 lockfiles. Do not commit `terraform.tfstate`, `.terraform/`, plan files, or credentials.

The bootstrap stack first creates the buckets using a local state, then migrates its state to S3. The Velero stack uses a separate key in the state bucket. AWS access for Terraform uses IAM Identity Center; the dedicated IAM user `homelab-sidor-velero-backup` has access only to the backup bucket. Its key is stored in Secrets Manager (`homelab/velero-backup`) and synced to namespace `velero` by External Secrets. The key value is not stored in Terraform state.

Configure and sign in to the AWS profile:

```bash
aws configure sso --profile homelab
AWS_PROFILE=homelab aws sso login
AWS_PROFILE=homelab aws sts get-caller-identity
```

Create the buckets and migrate the bootstrap state:

```bash
AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap init
AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap plan
AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap apply

cp terraform/bootstrap/backend.tf.example terraform/bootstrap/backend.tf
AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap init -migrate-state -force-copy \
  -backend-config="bucket=$(AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap output -raw state_bucket_name)" \
  -backend-config="key=bootstrap/terraform.tfstate" \
  -backend-config="region=eu-north-1" \
  -backend-config="use_lockfile=true"
```

Plan and install Velero:

```bash
AWS_PROFILE=homelab terraform -chdir=terraform/velero init \
  -backend-config="bucket=$(AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap output -raw state_bucket_name)" \
  -backend-config="key=velero/terraform.tfstate" \
  -backend-config="region=eu-north-1" \
  -backend-config="use_lockfile=true"

AWS_PROFILE=homelab terraform -chdir=terraform/velero plan \
  -var="backup_bucket_name=$(AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap output -raw backup_bucket_name)"

AWS_PROFILE=homelab terraform -chdir=terraform/velero apply \
  -var="backup_bucket_name=$(AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap output -raw backup_bucket_name)"
```

Create the Velero IAM access key once and pipe it directly to Secrets Manager. This requires `jq`; the key is not printed. Do not rerun without checking active keys, because IAM users can have at most two access keys.

```bash
set -o pipefail
AWS_PROFILE=homelab aws iam create-access-key \
  --user-name "$(AWS_PROFILE=homelab terraform -chdir=terraform/velero output -raw velero_iam_user_name)" \
  --output json \
| jq -c '{access_key: .AccessKey.AccessKeyId, secret_access_key: .AccessKey.SecretAccessKey}' \
| AWS_PROFILE=homelab aws secretsmanager put-secret-value \
    --secret-id "$(AWS_PROFILE=homelab terraform -chdir=terraform/velero output -raw velero_credentials_secret_name)" \
    --secret-string file:///dev/stdin
```

Verify Velero and its backup location:

```bash
kubectl -n velero get pods
kubectl -n velero get externalsecret,backupstoragelocation,schedules
kubectl -n velero get backups
```

To run a one-time backup and inspect PVC file-system backups:

```bash
velero backup create manual-check --include-namespaces '*' \
  --include-cluster-resources --default-volumes-to-fs-backup --ttl 168h
velero backup describe manual-check --details
kubectl -n velero get podvolumebackups -l velero.io/backup-name=manual-check -o wide
```

Velero can back up PVC files only when a pod has the volume mounted. The Garmin PVC uses local-path, so Terraform also creates `velero-volume-mounter` in namespace `garmin`. The cluster/resource backup completed, but a `PodVolumeBackup` for `garmin-data` was not confirmed in the validation runs on 2026-10-31. Do not consider Garmin files protected until a completed PVB for `garmin/garmin-data` is visible and a restore to an isolated PVC has been tested. File-system backup reads a live filesystem and is not an atomic SQLite snapshot.

---

# HomeLab (wersja polska)
Repozytorium opisuje domowe środowisko Kubernetes zarządzane deklaratywnie przez GitOps. Argo CD obserwuje gałąź `main`, wdraża aplikacje z manifestów Kustomize i utrzymuje stan klastra zgodny z konfiguracją w repozytorium.

## Przegląd

Projekt łączy podstawowe usługi klastra z aplikacją do pobierania danych Garmin oraz z systemem smart home opartym na Zigbee2MQTT i brokerze MQTT. MetalLB udostępnia usługi przez adresy z lokalnej puli LAN, Local Path Provisioner zapewnia lokalne wolumeny, a External Secrets Operator synchronizuje wybrane sekrety z AWS Secrets Manager. Prometheus zbiera metryki, a Grafana umożliwia przeglądanie metryk i logów. Alloy zbiera logi podów Kubernetes i wysyła je do Loki, gdzie można je przeszukiwać przez LogQL. Czujniki Zigbee publikują pomiary przez MQTT, a eksporter zamienia je na metryki Prometheusa. Cloudflare Tunnel pozwala bezpiecznie udostępnić Grafanę lub wybrany dashboard poza siecią domową.

```mermaid
flowchart LR
  Git[GitHub: main] --> Root[Argo CD: root Application]
  Root --> Infra[MetalLB, storage, ESO]
  Root --> Monitor[Prometheus i Grafana]
  Root --> Garmin[CronJob Garmin]
  Garmin --> AWS[AWS Secrets Manager]
  Garmin --> PVC[(SQLite na PVC)]
  Garmin --> Pushgateway[Prometheus Pushgateway]
  Pushgateway --> Prometheus[Prometheus]
  Prometheus --> Grafana[Grafana]
  Root --> Loki[Loki: logi]
  Root --> Alloy[Alloy: zbieranie logów]
  Alloy --> Loki
  Loki --> Grafana
  Root --> Z2M[Zigbee2MQTT + Mosquitto]
  Sensor[Czujnik Zigbee] --> Dongle[Dongle Sonoff] --> Z2M
  Z2M -->|MQTT| Exporter[mqtt2prometheus]
  Exporter --> Prometheus
  Root --> CF[cloudflared]
  CF --> Grafana
  Terraform[Terraform] --> StateS3[(S3 state Terraform)]
  Terraform --> Velero[Velero w RKE2]
  Velero --> BackupS3[(Backup klastra w S3)]
```

## Technologie

| Technologia | Zastosowanie |
| --- | --- |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> Kubernetes / RKE2 | Uruchamianie usług klastra; instrukcje instalacji znajdują się niżej. |
| <img src="https://cdn.simpleicons.org/argo" alt="" width="20" height="20" /> Argo CD | GitOps i automatyczna synchronizacja aplikacji z repozytorium. |
| <img src="https://cdn.simpleicons.org/argo" alt="" width="20" height="20" /> Argo Rollouts | Kontroler wdrożeń progresywnych dla zasobów Kubernetes `Rollout`. |
| <img src="https://cdn.simpleicons.org/renovate" alt="" width="20" height="20" /> Renovate | Cotygodniowo sprawdza zależności i otwiera pull requesty GitHuba; działa jako Kubernetes CronJob. |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> Kustomize | Składanie manifestów Kubernetes. |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> MetalLB | Udostępnianie usług typu `LoadBalancer` w sieci LAN. |
| <img src="https://cdn.simpleicons.org/rancher" alt="" width="20" height="20" /> Rancher Local Path Provisioner | Lokalne wolumeny dla aplikacji. |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> External Secrets Operator | Synchronizacja sekretów z AWS Secrets Manager. |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> cert-manager | Zarządzanie certyfikatami TLS dla zasobów Kubernetes. |
| <img src="https://cdn.simpleicons.org/traefikproxy" alt="" width="20" height="20" /> Traefik | Kontroler Ingress udostępniony przez MetalLB. |
| <img src="https://cdn.simpleicons.org/istio" alt="" width="20" height="20" /> Istio | Control plane service mesh; workloady dołączają do sidecar injection indywidualnie. |
| <img src="https://cdn.simpleicons.org/prometheus" alt="" width="20" height="20" /> <img src="https://cdn.simpleicons.org/grafana" alt="" width="20" height="20" /> Prometheus i Grafana | Metryki, dashboardy i powiadomienia e-mail przez Alertmanager. |
| <img src="https://cdn.simpleicons.org/grafana" alt="" width="20" height="20" /> Loki i Alloy | Zbieranie logów podów Kubernetes, ich przechowywanie i wyszukiwanie w Grafanie. |
| <img src="https://cdn.simpleicons.org/terraform" alt="" width="20" height="20" /> Terraform | Zarządzanie zasobami AWS do backupu i instalacja Velero w istniejącym klastrze RKE2. |
| <img src="https://cdn.simpleicons.org/kubernetes" alt="" width="20" height="20" /> Velero | Backup zasobów Kubernetes i danych zamontowanych PVC do Amazon S3. |
| <img src="https://cdn.simpleicons.org/python" alt="" width="20" height="20" /> <img src="https://cdn.simpleicons.org/garmin" alt="" width="20" height="20" /> Python i Garmin Connect Personal API | Pobieranie danych Garmin, zapis w SQLite i publikowanie metryk. |
| <img src="https://cdn.simpleicons.org/zigbee2mqtt" alt="" width="20" height="20" /> Zigbee2MQTT | Obsługa czujników Zigbee przez dongle USB Sonoff i publikowanie pomiarów w MQTT. |
| <img src="https://cdn.simpleicons.org/eclipsemosquitto" alt="" width="20" height="20" /> <img src="https://cdn.simpleicons.org/mqtt" alt="" width="20" height="20" /> Mosquitto (MQTT) | Broker wiadomości MQTT z logowaniem; dane logowania pochodzą z AWS przez ESO. |
| <img src="https://cdn.simpleicons.org/prometheus" alt="" width="20" height="20" /> <img src="https://cdn.simpleicons.org/mqtt" alt="" width="20" height="20" /> mqtt2prometheus | Zamiana pomiarów z MQTT na metryki Prometheusa. |
| <img src="https://cdn.simpleicons.org/cloudflare" alt="" width="20" height="20" /> Cloudflare Tunnel (`cloudflared`) | Zdalny dostęp do Grafany bez otwierania portów w routerze. |

## Struktura repozytorium

| Ścieżka | Zawartość |
| --- | --- |
| `argocd/root-app.yaml` | Główna aplikacja Argo CD typu „app of apps”. |
| `argocd/kustomization.yaml` | Lista aplikacji i elementów infrastruktury zarządzanych przez Argo CD. |
| `argocd/applications/` | Definicje aplikacji wdrażanych z tego repozytorium. |
| `argocd/infrastructure/` | Konfiguracja usług i infrastruktury klastra. |
| `argocd/infrastructure/loki.yaml` i `alloy.yaml` | Magazyn logów Loki i zbieranie logów podów Kubernetes przez Alloy. |
| `k8s/garmin-app/` | CronJob, PVC i konfiguracja sekretu aplikacji Garmin. |
| `k8s/zigbee2mqtt/` | Zigbee2MQTT, Mosquitto, eksporter `mqtt2prometheus` i dane logowania MQTT. |
| `k8s/cloudflared/` | Tunel Cloudflare i sekret z tokenem pobierany z AWS. |
| `k8s/argocd-access/` | Wewnętrzny CA, certyfikat TLS Argo CD i bezpośrednia usługa MetalLB. |
| `terraform/` | Buckety S3, zdalny state Terraform, uprawnienia Velero i release Helm. |
| `garmin_app.py` | Pobieranie i zapisywanie danych Garmin oraz publikowanie metryk. |

## GitOps

Po przygotowaniu klastra i Argo CD uruchom główną aplikację:

```bash
kubectl apply -f argocd/root-app.yaml
```

Root Application obserwuje katalog `argocd/`. Dodanie nowej aplikacji wymaga dodania jej manifestu do `argocd/applications/` lub `argocd/infrastructure/` i dopisania go do `argocd/kustomization.yaml`. Argo CD automatycznie synchronizuje zmiany z gałęzi `main`, w tym usuwa zasoby usunięte z konfiguracji (`prune`) i koryguje ręczne rozbieżności (`selfHeal`).

## Usługi

- **Grafana** jest udostępniana przez MetalLB pod adresem `192.168.0.200`; domyślnym źródłem danych jest Prometheus. Dashboardy `Zigbee`, `Zigbee3`, `Garmin` i `Alerty` są provisionowane z `argocd/infrastructure/grafana.yaml`.
- **Traefik** jest udostępniony przez MetalLB pod adresem `192.168.0.202`; zasoby Ingress powinny wskazywać `ingressClassName: traefik`. Klasa Traefika nie jest domyślną klasą klastra.
- **Argo CD** jest dostępne pod `https://argocd.andrzejsidor.uk` przez Traefika (`192.168.0.202`) albo bezpośrednio pod `https://192.168.0.203`. cert-manager wystawia SAN dla nazwy DNS i IP z wewnętrznego CA HomeLab; zaufaj certyfikatowi root CA na urządzeniach klienckich.
- **Istio i Kiali** działają w namespace `istio-system`; workloads nie są automatycznie wstrzykiwane, a gateway Istio nie jest zainstalowany. Panel Kiali jest dostępny pod `http://192.168.0.204:20001`; logowanie odbywa się tokenem Kubernetes. Kontrolerem Ingress pozostaje Traefik.
- **Argo Rollouts** jest zainstalowany w namespace `argo-rollouts` razem z CRD. Istniejące Deploymenty pozostają bez zmian; wdrożenia progresywne wymagają migracji aplikacji do zasobu `Rollout`.
- **cert-manager** jest zainstalowany razem z CRD i wystawia certyfikat Argo CD przez wewnętrzny ClusterIssuer `homelab-internal-ca`. Publiczny issuer ACME nie jest skonfigurowany.
- **Renovate** działa w namespace `renovate` w każdy poniedziałek o 06:00 czasu Europe/Warsaw i otwiera PR-y dla `andsidor/HomeLab`. External Secrets pobiera z AWS token `GIT_KEY` z `homelab/secrets`.
- **Prometheus** przechowuje metryki przez 90 dni na trwałym wolumenie (klasa `local-path-retain`, 10Gi).
- **Alerty operacyjne Prometheusa** obejmują wysokie użycie CPU, RAM i systemu plików węzłów, niedostępne lub oczekujące workloady Kubernetes, błędy lub opóźnienie backupu Velero, aplikacje Argo CD `OutOfSync` i wygasające certyfikaty. Alertmanager jest skonfigurowany do wysyłania e-maili przez Gmail SMTP; hasło SMTP jest synchronizowane przez ESO z AWS Secrets Manager (`homelab/secrets`, `smtp-auth-password`) do sekretu `alertmanager-smtp`. Alert storage mierzy zajętość dysku węzła, a nie pojedynczego PVC local-path; metryki per-PVC są niedostępne. Konfiguracja jest w repozytorium, ale dostarczenie wiadomości należy potwierdzić w klastrze.
- **Loki i Alloy** zbierają logi podów Kubernetes i udostępniają je do wyszukiwania w Grafanie. Loki przechowuje logi przez 14 dni na wolumenie `local-path-retain` o pojemności 10Gi; Alloy działa jako DaemonSet i pobiera logi przez Kubernetes API.
- **Zigbee2MQTT** działa na węźle `debian` z donglem Sonoff, a panel jest dostępny przez MetalLB pod `192.168.0.201:8080`. Pomiary trafiają do brokera **Mosquitto** (MQTT) w temacie `zigbee2mqtt/<urządzenie>`, a `mqtt2prometheus` udostępnia je Prometheusowi.
- **Cloudflare Tunnel** łączy klaster z Cloudflare przez token z AWS; trasa publiczna wskazuje na Grafanę, a dostęp warto chronić przez Cloudflare Access.
- **Garmin** działa jako CronJob co 30 minut. Klucz Personal API jest synchronizowany z AWS przez ESO, dane trafiają do SQLite na PVC `garmin-data` o pojemności 1Gi, a metryki są wysyłane do Pushgateway. Migrację zweryfikowano sumami plików i testem integralności SQLite; poprzedni PV 5Gi zachowano do ewentualnego rollbacku.
- **Velero** działa w namespace `velero` i co 30 minut, o :07 i :37 UTC, zapisuje zasoby klastra do S3; retencja wynosi 7 dni. Nadal pomija pliki PVC Garmina: Velero zgłasza wolumen local-path typu `hostPath` jako nieobsługiwany. Pliki Garmin nie są obecnie chronione przez Velero; snapshoty CSI/EBS również są wyłączone.

## Analiza logów

W Grafanie otwórz **Explore**, wybierz źródło danych **Loki** i uruchom zapytanie LogQL, na przykład:

```logql
{namespace="zigbee2mqtt"}
{namespace="zigbee2mqtt"} |= "error"
```

Alloy działa jako DaemonSet i zbiera logi podów przez Kubernetes API. Loki jest dostępny tylko wewnątrz klastra; logi są przechowywane przez 14 dni na wolumenie `local-path-retain` o pojemności 10Gi. Logi systemowego journala hostów i eventy Kubernetes nie są zbierane. Traktuj logi jako potencjalnie poufne i nie udostępniaj Loki ani zapytań do logów w publicznych dashboardach Grafany.

## Notatki i komendy

Aplikacja `garmin_app.py` pobiera dane z Garmin Connect Personal API. Komendy diagnostyczne i notatki operacyjne znajdują się w [HL-NOTE.md](HL-NOTE.md).

## Aplikacja Garmin (Python)

```bash
pip install -r requirements.txt
python garmin_app.py --days 7 --activities 10 --out garmin_data
python garmin_app.py --download-fit        # dodatkowo pliki aktywności
```

- Uwierzytelnianie: osobisty klucz Garmin Connect Personal API w `GARMIN_PERSONAL_API_KEY`.
- Klucz API wymienia się automatycznie na bearer token; cache tokenu trafia do `~/.config/garmin`.
- Klucz Personal API utworzysz w [ustawieniach Garmin Connect](https://connect.garmin.com/app/settings/personalApiToken). Traktuj go jak hasło.

## Docker / Podman

Docker:

```bash
docker build -t garmin-app .
docker run -it --rm \
  --env GARMIN_PERSONAL_API_KEY \
  -v "$PWD/garmin_data:/data" \
  garmin-app --days 7
```

Podman:

```bash
podman build -t garmin-app .
podman run --rm -it \
  -e GARMIN_PERSONAL_API_KEY \
  -v "$PWD/garmin_data:/data:Z" \
  garmin-app --days 7
```

Opcja wolumenu `:Z` dostosowuje etykiety katalogu na systemach z SELinux. Przed uruchomieniem ustaw `GARMIN_PERSONAL_API_KEY` w środowisku.

## Git / GitHub

```bash
git remote set-url origin https://github.com/andsidor/HomeLab.git
git add . && git commit -m "opis" && git push -u origin main
```

## CI (`.github/workflows/ci.yml`)

- `codeql` - analiza kodu Pythona
- `python-security` - `bandit -r garmin_app.py`, `pip-audit -r requirements.txt`
- `podman-build` - buduje obraz Podmanem i publikuje `ghcr.io/andsidor/homelab:podman` oraz `podman-<commit-sha>` przy pushu i uruchomieniu harmonogramu; pull requesty budują obraz, ale go nie publikują
- `docker` - build, nieblokujący skan Trivy SARIF dla `CRITICAL` i `HIGH`, push do `ghcr.io/andsidor/homelab`

Notatki:
- Akcje zgodne z Node 24 (checkout v7, setup-python v7, codeql v4, docker/* v4-v7, `create-github-app-token` v3.3.0).
- Tagi `aquasecurity/trivy-action` mają prefiks `v` (np. `v0.36.0`).
- Wyniki Trivy trafiają jako SARIF do zakładki Security. Blokująca bramka CRITICAL jest obecnie zakomentowana, więc podatności nie przerywają builda.
- Wymagane minimalne wersje: `urllib3>=2.8.0`, `msgpack>=1.2.1`, `setuptools>=78.1.1` (w Dockerfile).

## RKE2

```bash
curl -sfL https://get.rke2.io | sudo sh -
sudo systemctl enable --now rke2-server.service

mkdir -p ~/.kube
sudo cp /etc/rancher/rke2/rke2.yaml ~/.kube/config && sudo chown $USER ~/.kube/config
export PATH=$PATH:/var/lib/rancher/rke2/bin
kubectl get nodes

# token do dołączania węzłów (rke2-agent)
sudo cat /var/lib/rancher/rke2/server/node-token
```

## Argo CD

```bash
kubectl create namespace argocd
kubectl apply -n argocd --server-side -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# hasło początkowe (użytkownik: admin)
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# panel: https://localhost:8080
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

Nową aplikację dodaj jako manifest `Application` w `argocd/applications/`
albo `argocd/infrastructure/`, a następnie dopisz jej ścieżkę do
`argocd/kustomization.yaml`. W manifeście ustaw `repoURL` na
`https://github.com/andsidor/HomeLab.git` i `path` na katalog z Kustomize.

Struktura w repo:
- `argocd/root-app.yaml` - Application "app of apps", obserwuje `argocd/`
- `argocd/kustomization.yaml` - lista aplikacji oraz elementów infrastruktury zarządzanych przez root app
- `argocd/applications/` - po jednym Application na aplikację
- `argocd/infrastructure/` - aplikacje i konfiguracja elementów klastra
- `k8s/<app>/` - manifesty (Kustomize)

Start (raz): `kubectl apply -f argocd/root-app.yaml`; kolejne aplikacje wdroży root app po dodaniu manifestu do Kustomize i wysłaniu zmian do Gita.

Grafana (Helm chart w Argo CD) korzysta z istniejącego sekretu Kubernetes `grafana-admin-local`. Po synchronizacji:

```bash
kubectl -n monitoring port-forward svc/grafana 3000:80
```

Panel będzie dostępny pod `http://localhost:3000`. ESO synchronizuje pola `admin-user` i `admin-password` z AWS secret `homelab/secrets` do Kubernetes Secret `grafana-admin-local`, używanego przez chart Helm.

Dashboard Istio (Kiali) jest dostępny po synchronizacji pod `http://192.168.0.204:20001`. Zaloguj się tokenem Kubernetes.

## External Secrets Operator + AWS

`ClusterSecretStore` `aws-secretsmanager` łączy ESO z AWS Secrets Manager w regionie `eu-north-1` przez istniejący Kubernetes Secret `awssm-secret` w namespace `external-secrets`. Store oczekuje w nim kluczy `aws_access_key_id` i `aws_secret_access_key`; wartości credentiali nie powinny trafiać do Gita.

Użyj kluczy IAM z uprawnieniami `secretsmanager:GetSecretValue` i `secretsmanager:DescribeSecret`, ograniczonymi do ARN potrzebnych sekretów w `eu-north-1`. Przy własnym kluczu KMS dodaj także ograniczone `kms:Decrypt`. Po synchronizacji sprawdź store: `kubectl get clustersecretstore aws-secretsmanager`.

Sekrety w Secrets Manager (same nazwy; nigdy nie dokumentuj ich wartości):
- `homelab/secrets` zawiera dane workloadów Garmin, MQTT, Cloudflare Tunnel, dane logowania Grafany (`admin-user`, `admin-password`), hasło SMTP Alertmanagera (`smtp-auth-password`) oraz classic GitHub PAT dla Renovate (`GIT_KEY`).
- `homelab/velero-backup` zawiera poświadczenia dedykowanego użytkownika IAM dla Velero.
- `homelab/rke2-etcd-backup` zawiera poświadczenia do zapisu snapshotów etcd RKE2 w S3.

`k8s/garmin-app/cronjob.yaml` pobiera dane z Garmin Connect Personal API; klucz pochodzi z AWS przez ESO, a SQLite i cache bearer tokenu są przechowywane na PVC.

Uwagi:
- Sekretów nie commitować (Sealed Secrets / SOPS / External Secrets).
- Prywatny pakiet GHCR wymaga `imagePullSecret` (token `read:packages`).
- Po zalogowaniu zmienić hasło admina i usunąć `argocd-initial-admin-secret`.

## Terraform i Velero (AWS)

Terraform zarządza dwoma osobnymi bucketami S3 w `eu-north-1`: `homelab-sidor-tfstate-265d7dd5` przechowuje zdalny state, a `homelab-sidor-velero-265d7dd5` backupy Velero. Oba mają szyfrowanie, wersjonowanie, blokadę publicznego dostępu i politykę wymuszającą TLS. Blokada state używa S3 lockfiles. Nie commituj `terraform.tfstate`, `.terraform/`, planów ani credentiali.

Stos bootstrap najpierw tworzy buckety z lokalnym state, a następnie migruje state do S3. Stos Velero używa osobnego klucza w bucketcie state. Terraform loguje się przez IAM Identity Center. Dedykowany IAM user `homelab-sidor-velero-backup` ma dostęp tylko do bucketa backupowego. Jego klucz jest zapisany w Secrets Manager (`homelab/velero-backup`) i synchronizowany przez External Secrets do namespace `velero`; wartość klucza nie trafia do Terraform state.

Konfiguracja i logowanie profilu AWS:

```bash
aws configure sso --profile homelab
AWS_PROFILE=homelab aws sso login
AWS_PROFILE=homelab aws sts get-caller-identity
```

Utworzenie bucketów i migracja state bootstrapu:

```bash
AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap init
AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap plan
AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap apply

cp terraform/bootstrap/backend.tf.example terraform/bootstrap/backend.tf
AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap init -migrate-state -force-copy \
  -backend-config="bucket=$(AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap output -raw state_bucket_name)" \
  -backend-config="key=bootstrap/terraform.tfstate" \
  -backend-config="region=eu-north-1" \
  -backend-config="use_lockfile=true"
```

Plan i instalacja Velero:

```bash
AWS_PROFILE=homelab terraform -chdir=terraform/velero init \
  -backend-config="bucket=$(AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap output -raw state_bucket_name)" \
  -backend-config="key=velero/terraform.tfstate" \
  -backend-config="region=eu-north-1" \
  -backend-config="use_lockfile=true"

AWS_PROFILE=homelab terraform -chdir=terraform/velero plan \
  -var="backup_bucket_name=$(AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap output -raw backup_bucket_name)"

AWS_PROFILE=homelab terraform -chdir=terraform/velero apply \
  -var="backup_bucket_name=$(AWS_PROFILE=homelab terraform -chdir=terraform/bootstrap output -raw backup_bucket_name)"
```

Utwórz klucz IAM Velero tylko raz i przekaż go potokiem bezpośrednio do Secrets Manager. Wymaga to `jq`; klucz nie jest wypisywany. Nie uruchamiaj ponownie bez sprawdzenia aktywnych kluczy, ponieważ IAM user może mieć maksymalnie dwa.

```bash
set -o pipefail
AWS_PROFILE=homelab aws iam create-access-key \
  --user-name "$(AWS_PROFILE=homelab terraform -chdir=terraform/velero output -raw velero_iam_user_name)" \
  --output json \
| jq -c '{access_key: .AccessKey.AccessKeyId, secret_access_key: .AccessKey.SecretAccessKey}' \
| AWS_PROFILE=homelab aws secretsmanager put-secret-value \
    --secret-id "$(AWS_PROFILE=homelab terraform -chdir=terraform/velero output -raw velero_credentials_secret_name)" \
    --secret-string file:///dev/stdin
```

Weryfikacja Velero i lokalizacji backupu:

```bash
kubectl -n velero get pods
kubectl -n velero get externalsecret,backupstoragelocation,schedules
kubectl -n velero get backups
```

Jednorazowy backup i kontrola plikowych kopii PVC:

```bash
velero backup create manual-check --include-namespaces '*' \
  --include-cluster-resources --default-volumes-to-fs-backup --ttl 168h
velero backup describe manual-check --details
kubectl -n velero get podvolumebackups -l velero.io/backup-name=manual-check -o wide
```

Velero kopiuje pliki PVC tylko wtedy, gdy pod ma zamontowany wolumen. PVC Garmina używa local-path, dlatego Terraform tworzy też `velero-volume-mounter` w namespace `garmin`. Backup zasobów klastra zakończył się, ale w testach z 2026-10-31 nie potwierdzono `PodVolumeBackup` dla `garmin-data`. Nie uznawaj plików Garmin za zabezpieczone, dopóki nie pojawi się ukończony PVB dla `garmin/garmin-data` i nie zostanie przetestowane odtworzenie na odizolowanym PVC. Backup plikowy czyta aktywny system plików i nie jest atomowym snapshotem SQLite.
