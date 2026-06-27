# Infrastructure

IaC for local development, CI, and production deployments.

- `docker-compose.yml` — Local dev stack (MongoDB, Redis, Qdrant, API, UI)
- `nginx/` — TLS termination & reverse-proxy
- `helm/` — Kubernetes Helm charts
- `terraform/` — Cloud infrastructure stubs
- `scripts/` — Deployment entry points

See [`docs/project_structure.md`](../docs/project_structure.md) §10.
