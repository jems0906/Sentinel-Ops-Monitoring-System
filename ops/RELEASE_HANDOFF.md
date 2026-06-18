# Sentinel Ops Monitoring System - Release Handoff

## 1. Current Release State

- Deployment script passed in strict mode with preflight enabled.
- Go-live verification passed for backend, frontend, Prometheus, Grafana, and Alertmanager.
- Backend smoke tests are passing.

## 2. Deploy Commands

From project root:

```powershell
./ops/deploy_production.ps1 -EnvFile .env.production
```

Fast restart without rebuild:

```powershell
./ops/deploy_production.ps1 -EnvFile .env.production -SkipBuild
```

Optional post-deploy drills:

```powershell
./ops/deploy_production.ps1 -EnvFile .env.production -RunDrills
```

## 3. Service Endpoints

- Frontend: http://localhost:5173
- Backend health: http://localhost:8001/health
- Backend docs: http://localhost:8001/docs
- Prometheus health: http://localhost:9090/-/healthy
- Grafana health: http://localhost:3000/api/health
- Alertmanager: http://localhost:9093

## 4. CI/CD Gates

- Backend smoke tests: .github/workflows/backend-smoke-tests.yml
- Runtime drill validation: .github/workflows/runtime-drill-validation.yml
- Container security gate: .github/workflows/container-security-gate.yml

Security gate behavior:

- Critical findings: blocking
- High/medium findings: non-blocking report artifact (container-security-reports)

## 5. Production Cutover Artifacts

- Cutover checklist: ops/PRODUCTION_CUTOVER_CHECKLIST.md
- Deployment runbook: ops/DEPLOYMENT_RUNBOOK_DOCKER_HOST.md
- Rollback plan: ops/ROLLBACK_PLAN.md
- Security exception log: ops/SECURITY_EXCEPTIONS_LOG.md
- Go-live verifier: ops/go_live_verify.ps1
- Production env template: .env.production.example

## 6. Rollback Quick Reference

```powershell
docker compose logs --no-color > ops/rollback_pre_logs.txt
docker compose down
./ops/deploy_production.ps1 -EnvFile .env.production
./ops/go_live_verify.ps1
```

## 7. Operations Notes

- Keep .env.production credentials out of source control.
- Preflight checks in deploy_production.ps1 block placeholder credentials by default.
- Use SkipPreflight only for controlled non-production testing.

## 8. Known Constraint

- Git repository metadata is not initialized in this workspace, so release tagging cannot be executed here until repository initialization is completed.
