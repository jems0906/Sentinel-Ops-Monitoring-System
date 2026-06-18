# Production Cutover Checklist

## 1. Release Identity

- Confirm planned release version (example: v1.0.0).
- If Git is initialized, create and push a release tag.
- Confirm rollback target version is known before cutover.

## 2. Security Gate

- Run container security gate workflow:
  - .github/workflows/container-security-gate.yml
- Block release if critical findings exist.
- For high/medium findings, review uploaded artifact: container-security-reports.
- Log accepted risks in ops/SECURITY_EXCEPTIONS_LOG.md.

## 3. Environment and Secrets Validation

- Create deployment environment file from .env.production.example.
- Verify SMTP secrets are set if email alerts are required.
- Verify Grafana admin credentials are NOT defaults.
- Verify backend DB path and persistence strategy are correct for target environment.

## 4. Deployment Execution

- Build and deploy stack with target environment values.
- Verify services are healthy:
  - Backend: http://<host>:8001/health
  - Frontend: http://<host>:5173
  - Prometheus: http://<host>:9090/-/healthy
  - Grafana: http://<host>:3000/api/health
  - Alertmanager: http://<host>:9093

## 5. Post-Deployment Validation

- Run backend smoke tests against deployed API.
- Run ops/run_all_drills.ps1 in the target environment and confirm all scenarios pass.
- Confirm metrics are visible in Prometheus and dashboards load in Grafana.
- Confirm external alerts can be ingested and triaged.

## 6. Go/No-Go Decision

Go criteria:
- No critical security findings.
- Smoke tests pass.
- Drill scenarios pass.
- Health endpoints are green.
- Rollback plan validated.

No-go criteria:
- Any critical security finding.
- Failed smoke or drill validation.
- Missing secret configuration.
- Rollback path not available.
