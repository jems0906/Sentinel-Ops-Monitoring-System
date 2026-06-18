# Deployment Runbook (Docker Host)

## Scope

This runbook deploys Sentinel Ops Monitoring System on a single Docker host using Docker Compose.

## Preconditions

- Docker and Docker Compose are installed on target host.
- Project files are present on target host.
- Production environment file exists as `.env.production`.
- Security gate status is reviewed before deployment.

## 1. Prepare environment

1. Copy `.env.production.example` to `.env.production`.
2. Set production values for credentials and alerting secrets.
3. Ensure default Grafana credentials are replaced.

## 2. Deploy

From project root:

```powershell
./ops/deploy_production.ps1 -EnvFile .env.production
```

The deployment command runs preflight validation and blocks deploy when required values are missing or placeholder credentials are detected.

For controlled non-production testing only, you can bypass preflight checks:

```powershell
./ops/deploy_production.ps1 -EnvFile .env.production -SkipPreflight
```

This command:

- builds and starts services using compose
- runs health validation via `ops/go_live_verify.ps1`
- optionally runs drill tests when requested

## 3. Post-deploy checks

- Backend health endpoint returns `{"status":"ok"}`.
- Frontend loads at host port 5173 (or configured ingress).
- Prometheus, Grafana, and Alertmanager health endpoints return HTTP 200.
- Incident and alert APIs respond from frontend and backend docs.

## 4. Rollback

Use the rollback plan in `ops/ROLLBACK_PLAN.md`.

## 5. Evidence to keep

- Deployment timestamp and operator name
- Security gate result links
- Go-live verification output
- Any accepted-risk entry in `ops/SECURITY_EXCEPTIONS_LOG.md`
