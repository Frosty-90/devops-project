# StockPilot — Inventory Management

StockPilot tracks a warehouse's products: what is in stock, what is running low, and what the stock is worth. Staff receive and ship units straight from the dashboard, and products that fall to their reorder level show up as reorder alerts.

It is also a full DevOps capstone: every push to `main` is tested, built into containers, security-scanned, pushed to GHCR and deployed to AWS EKS with Helm, then monitored with Prometheus and Grafana.

```text
git push → GitHub Actions ─┬─ pytest + frontend build
                           ├─ docker build → Trivy scan (fail on HIGH/CRITICAL) → push to GHCR (tag = commit SHA)
                           └─ assume AWS role via OIDC → helm upgrade --install → EKS
                                                                    │
            Traefik Ingress ── /     → React frontend (nginx, non-root)
                            └─ /api  → FastAPI backend ── PostgreSQL (EBS volume)
                                              │
                                   Prometheus (ServiceMonitor) → Grafana
```

## Features

- Product catalogue with SKU, category, supplier, unit price and reorder level
- Stock status computed from quantity: **In stock**, **Low stock** (at or below reorder level), **Out of stock**
- Receive / ship stock with atomic adjustments that can never take stock below zero
- KPIs: product count, units on hand, low/out-of-stock counts, total inventory value
- Reorder alerts panel, status filters, responsive layout

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness: the process is up |
| GET | `/ready` | Readiness: the database is reachable |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/products` | List products (sorted by name) |
| GET | `/api/products/{id}` | Get one product |
| POST | `/api/products` | Create a product (409 on duplicate SKU) |
| PUT | `/api/products/{id}` | Update product details |
| POST | `/api/products/{id}/adjust` | Receive (`{"delta": 5}`) or ship (`{"delta": -2}`) stock; 400 if it would go negative |
| DELETE | `/api/products/{id}` | Delete a product |
| GET | `/api/products/stats` | Inventory KPIs |

Interactive docs: `/docs` on the backend.

## Tech stack

React + Vite · FastAPI · SQLAlchemy · Alembic · PostgreSQL · Pytest · Docker · GitHub Actions · Trivy · GHCR · Terraform · AWS VPC + EKS · Helm · Traefik Ingress · HPA · Prometheus + Grafana

## Repository layout

```text
backend/              FastAPI app, Alembic migrations, pytest suite
frontend/             React app, nginx config, multi-stage Dockerfile
docker-compose.yml    Full local stack
.github/workflows/    CI/CD pipeline
terraform/            AWS VPC, EKS, GitHub OIDC deploy role
k8s/                  Namespace and gp3 StorageClass
helm/taskboard/       Helm chart (backend, frontend, PostgreSQL, Ingress, HPA, ServiceMonitor)
monitoring/           kube-prometheus-stack values and the Grafana dashboard
scripts/              seed data and load test
troubleshooting/      deliberately broken manifests for the debugging lab
```

> The Kubernetes namespace, Helm chart, EKS cluster and image names keep the `taskboard` prefix from the course's reference architecture; renaming them would mean recreating the cluster.

## Run locally

```bash
docker compose up --build
./scripts/seed.sh            # optional sample products
```

- App: http://localhost:3000
- API docs: http://localhost:8000/docs

`docker compose down -v` stops everything and deletes the database volume.

### Backend without Docker

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://taskboard:taskboard@localhost:5432/taskboard'
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Tests

```bash
cd backend && pytest -v
```

Tests run against a throwaway SQLite database, never PostgreSQL. They cover CRUD, duplicate SKUs, validation, stock-status thresholds, stock adjustments (including refusing to oversell), 404s and the KPI maths.

## CI/CD

`.github/workflows/ci-cd.yml` runs on every push and pull request to `main`:

1. **test** — pytest, then the frontend production build
2. **build-scan-push** — builds both images, scans them with Trivy (fails on fixable HIGH/CRITICAL CVEs), pushes to GHCR tagged with the commit SHA
3. **deploy** — `main` only: assumes an AWS IAM role through GitHub OIDC (no AWS keys stored in GitHub), then `helm upgrade --install --wait`

The deploy job is skipped until the `AWS_ROLE_ARN` repository variable is set.

## Infrastructure (Terraform)

```bash
cd terraform
terraform init
terraform plan
terraform apply                # VPC, NAT, EKS 1.36 + 2× t3.medium nodes, add-ons, OIDC deploy role
$(terraform output -raw configure_kubectl)
gh variable set AWS_ROLE_ARN --body "$(terraform output -raw github_actions_role_arn)"
```

See `terraform/terraform.tfvars.example` for the variables. Region: `ap-south-1`.

## Cluster setup (once per cluster)

```bash
kubectl apply -f k8s/namespace.yaml -f k8s/storageclass.yaml
helm repo add traefik https://traefik.github.io/charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install traefik traefik/traefik -n traefik --create-namespace
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/prometheus-values.yaml
kubectl apply -f monitoring/taskboard-dashboard.yaml
```

The app itself is deployed by the pipeline. The public URL is the Traefik load balancer:

```bash
kubectl get svc -n traefik traefik -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

## Autoscaling

The backend HPA scales from 2 to 6 pods at 60% CPU (metrics from the EKS metrics-server add-on). To demo it:

```bash
kubectl run loadgen -n taskboard --image=busybox:1.37 --restart=Never -- sh -c \
  'for w in $(seq 20); do (while true; do wget -q -O /dev/null http://backend:8000/api/products; done) & done; sleep 300'
kubectl get hpa -n taskboard -w
kubectl delete pod loadgen -n taskboard
```

## Monitoring

```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090   # http://localhost:9090/targets
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3001:80        # http://localhost:3001
kubectl get secret -n monitoring kube-prometheus-stack-grafana -o jsonpath='{.data.admin-password}' | base64 -d
```

Grafana user `admin`; open **Dashboards → StockPilot API** for request rate, p95 latency, 5xx rate, and backend CPU vs. replica count.

## Troubleshooting lab

```bash
kubectl apply -f troubleshooting/broken-image.yaml     # ImagePullBackOff: wrong image tag
kubectl apply -f troubleshooting/broken-service.yaml   # Service selects no pods: no endpoints
kubectl describe pod <pod> -n taskboard
kubectl get endpoints -n taskboard
kubectl get events -n taskboard --sort-by=.lastTimestamp
```

## Tear down

```bash
helm uninstall traefik -n traefik   # delete the load balancer first so the VPC can be removed
cd terraform && terraform destroy
```
