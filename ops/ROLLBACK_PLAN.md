# Rollback Plan

## Trigger conditions

Rollback immediately if one or more conditions occur after deployment:

- Backend health endpoint fails repeatedly.
- Frontend is unavailable or major API paths fail.
- Critical incident generation is broken.
- Monitoring stack (Prometheus/Grafana/Alertmanager) is unavailable.

## Fast rollback (same host)

1. Capture current logs:

```powershell
docker compose logs --no-color > ops/rollback_pre_logs.txt
```

2. Stop current release:

```powershell
docker compose down
```

3. Restore prior known-good release source/artifacts.

4. Re-deploy prior release:

```powershell
./ops/deploy_production.ps1 -EnvFile .env.production
```

5. Validate with:

```powershell
./ops/go_live_verify.ps1
```

## Data considerations

- If using SQLite volume bind, verify database compatibility before reusing with prior release.
- Keep backup copy of `backend/data` before major version upgrades.

## Incident handling

- Log rollback event in incident notes.
- Add root cause summary for failed rollout.
- Open remediation task before next release attempt.
