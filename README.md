# HomeLab

Notatki i komendy. Aplikacja `garmin_app.py` pobiera dane z Garmin Connect.

## Aplikacja Garmin (Python)

```bash
pip install -r requirements.txt
python garmin_app.py --days 7 --activities 10 --out garmin_data
python garmin_app.py --download-fit        # dodatkowo pliki aktywności
```

- Logowanie: `GARMIN_EMAIL` / `GARMIN_PASSWORD` lub prompt (z MFA).
- Tokeny: `~/.garminconnect` (kolejne uruchomienia bez hasła).

## Docker

```bash
docker build -t garmin-app .
docker run -it --rm \
  -v garmin_tokens:/home/app/.garminconnect \
  -v "$PWD/garmin_data:/data" \
  garmin-app --days 7
```

## Git / GitHub

```bash
git remote set-url origin https://github.com/andsidor/HomeLab.git
git add . && git commit -m "opis" && git push -u origin main
```

## CI (`.github/workflows/ci.yml`)

- `codeql` - analiza kodu Pythona
- `python-security` - `bandit -r garmin_app.py`, `pip-audit -r requirements.txt`
- `docker` - build, Trivy (SARIF + bramka tylko na CRITICAL), push do `ghcr.io/andsidor/homelab`

Notatki:
- Akcje w wersjach Node 24 (checkout v7, setup-python v7, codeql v4, docker/* v4-v7).
- Tagi `aquasecurity/trivy-action` mają prefiks `v` (np. `v0.36.0`).
- Podatności HIGH nie blokują builda, są widoczne w zakładce Security.
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

Dodanie aplikacji: `kubectl apply -f argocd/applications/<app>.yaml`
(`repoURL: https://github.com/andsidor/HomeLab.git`, `path: k8s/<app>`).

Struktura w repo:
- `argocd/root-app.yaml` - Application "app of apps", obserwuje `argocd/applications/`
- `argocd/applications/` - po jednym Application na aplikację
- `k8s/<app>/` - manifesty (Kustomize)

Start (raz): `kubectl apply -f argocd/root-app.yaml`; kolejne aplikacje wystarczy dodać do Gita.

Uwagi dot. `k8s/garmin-app/cronjob.yaml`: CronJob codziennie 6:00, tokeny i dane w `emptyDir`
(nietrwałe, logowanie Garmin wymaga interaktywnego MFA, więc docelowo potrzebny PVC z tokenami).

Uwagi:
- Sekretów nie commitować (Sealed Secrets / SOPS / External Secrets).
- Prywatny pakiet GHCR wymaga `imagePullSecret` (token `read:packages`).
- Po zalogowaniu zmienić hasło admina i usunąć `argocd-initial-admin-secret`.
