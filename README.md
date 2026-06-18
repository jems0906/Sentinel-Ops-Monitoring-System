# Sentinel Ops Monitoring System

This project demonstrates networking, uptime monitoring, root cause analysis, and production support workflows.

## What this proves

- Monitoring server/device availability and latency (ping checks)
- Monitoring service health (HTTP up/down checks)
- DNS resolution chain verification (resolver + record checks)
- Automatic incident logging and timeline notes
- Alerting through dashboard feed and optional SMTP email
- Root cause analysis documentation and incident closure process
- Real failure simulation workflows used in production support drills

## Tech stack

- Python + FastAPI (monitoring backend and APIs)
- React + Vite (operations dashboard)
- Docker + Docker Compose
- Prometheus + Grafana (optional, included and wired)
- SQLite (local incident/check persistence)

## Project structure

- `backend/`: FastAPI app, monitoring loop, incident engine, Prometheus metrics
- `frontend/`: React operations dashboard
- `prometheus/`: scrape configuration
- `ops/`: PowerShell scripts to trigger and document incidents

## Prerequisites

- Docker Desktop
- PowerShell (Windows)

## Step-by-step setup and run

1. Open a terminal at the project root.
2. Start all services:

```powershell
docker compose up --build -d
```

3. Verify backend is healthy:

```powershell
Invoke-RestMethod http://localhost:8001/health
```

4. Open dashboards:

- React dashboard: http://localhost:5173
- FastAPI docs: http://localhost:8001/docs
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093
- Grafana: http://localhost:3000 (admin/admin)

## Core APIs you can test

- `GET /api/summary`
- `GET /api/targets`
- `GET /api/checks`
- `GET /api/incidents`
- `GET /api/alerts`
- `GET /api/external-alerts`
- `POST /api/external-alerts/prometheus` (Alertmanager webhook receiver)
- `POST /api/simulations/toggle`
- `POST /api/simulations/restart-service/{target_id}`
- `POST /api/admin/run-cycle?force=true` (deterministic test/demo cycle trigger)
- `PATCH /api/incidents/{incident_id}`
- `POST /api/incidents/{incident_id}/notes`

## One-command full drill

Run all four failure scenarios in sequence and produce a JSON evidence report:

```powershell
.\ops\run_all_drills.ps1
```

Output:

- `ops/drill_report.json` with summary, incidents, and alerts after the full scenario set.
- `scenario_results` section with pass/fail status for:
	- `server_down`
	- `high_latency`
	- `dns_failure`
	- `service_crash_restart`

## Failure simulation playbook

### 1) Server goes down -> alert triggered

```powershell
.\ops\simulate_failures.ps1 -Mode server_down -TargetId 1
```

Expected:

- Target status becomes `down`
- New open incident appears
- Alert event appears in alert feed

### 2) High latency -> investigate network

```powershell
.\ops\simulate_failures.ps1 -Mode high_latency -TargetId 1 -LatencyMs 1200
```

Expected:

- Target status becomes `degraded`
- Incident opened (if no open incident exists)
- Latency spike visible in dashboard and Prometheus metrics

### 3) DNS failure -> debug resolution chain

```powershell
.\ops\simulate_failures.ps1 -Mode dns_failure -TargetId 3
```

Expected:

- DNS target check fails
- Incident and alert generated
- Root cause notes can document resolver path and suspected fault domain

### 4) Service crash -> restart + log

```powershell
.\ops\simulate_failures.ps1 -Mode service_crash -TargetId 2
.\ops\incident_note.ps1 -IncidentId 1 -Note "Service process crash confirmed from synthetic probe"
Invoke-RestMethod -Method Post -Uri "http://localhost:8001/api/simulations/restart-service/2"
```

Expected:

- Service target marked down
- Incident note appended to timeline
- Restart endpoint clears simulation and logs restart action
- Target returns healthy after checks recover

### Clear any active simulation

```powershell
.\ops\simulate_failures.ps1 -Mode none -TargetId 1
```

## Incident root cause workflow

1. Open incident from dashboard timeline.
2. Add notes as investigation progresses (symptoms, commands run, findings).
3. Save root cause statement with failure domain and corrective action.
4. Resolve incident once target is healthy.
5. Confirm closure alert appears.

## RCA note templates

Use these concise templates in incident notes and root cause fields:

- Symptom: `User-visible impact, start time, affected target(s)`
- Detection: `How monitor detected failure (check type + threshold)`
- Scope: `Blast radius (service, region, dependency)`
- Immediate fix: `What action restored service (restart, rollback, route change)`
- Root cause: `Primary technical cause and why protections did not prevent it`
- Preventive action: `Permanent control to avoid recurrence`

Example root cause statement:

`Frontend process terminated due to simulated crash condition; synthetic checks detected HTTP failure; restart restored service; added auto-restart policy and startup probe tuning to reduce recurrence risk.`

## Backend smoke tests

From the `backend` folder:

```powershell
pip install -r requirements-dev.txt
pytest -q
```

Current smoke coverage:

- `/health` endpoint
- target create/list API path
- deterministic monitor cycle endpoint (`/api/admin/run-cycle`)

## CI smoke testing

GitHub Actions workflow runs backend smoke tests on push and pull requests touching backend files:

- `.github/workflows/backend-smoke-tests.yml`

## Runtime drill CI

GitHub Actions workflow can run full Docker runtime validation with the four failure drills and fail the pipeline if any scenario does not pass:

- `.github/workflows/runtime-drill-validation.yml`

It uploads `ops/drill_report.json` as a build artifact.

## Container security CI

GitHub Actions workflow builds backend/frontend images and enforces a critical-severity vulnerability gate. It also uploads non-blocking high/medium JSON scan reports for triage:

- `.github/workflows/container-security-gate.yml`

### PR security checklist

- `container-security-gate` passes with no critical findings in backend/frontend images.
- If high/medium findings exist, review uploaded artifact `container-security-reports` and log acceptance/remediation notes in the PR.
- For accepted risk, include reason, impact, and planned remediation target release.
- For remediation work, link the exact dependency/image change in the PR description.

## Production cutover artifacts

- Cutover checklist: `ops/PRODUCTION_CUTOVER_CHECKLIST.md`
- Security exceptions log: `ops/SECURITY_EXCEPTIONS_LOG.md`
- Production environment template: `.env.production.example`
- Go-live verification script: `ops/go_live_verify.ps1`
- Deployment runbook: `ops/DEPLOYMENT_RUNBOOK_DOCKER_HOST.md`
- Rollback plan: `ops/ROLLBACK_PLAN.md`
- Deployment command script: `ops/deploy_production.ps1`

`ops/deploy_production.ps1` enforces preflight checks for required environment values and blocks deployment when placeholder credentials are detected.

## Email alert configuration (optional)

Set these environment variables for backend service in `docker-compose.yml`:

- `SENTINEL_SMTP_HOST`
- `SENTINEL_SMTP_PORT`
- `SENTINEL_SMTP_USERNAME`
- `SENTINEL_SMTP_PASSWORD`
- `SENTINEL_ALERT_TO_EMAIL`
- `SENTINEL_ALERT_FROM_EMAIL`

If not set, dashboard alerts still work.

## Prometheus metrics

Exposed on backend `/metrics`:

- `sentinel_checks_total`
- `sentinel_target_status`
- `sentinel_target_latency_ms`
- `sentinel_open_incidents`
- `sentinel_incidents_total_by_status`
- `sentinel_alert_events_total`

## Prometheus alert rules

Alert rules are defined in:

- `prometheus/alerts.yml`

Current rule set:

- `SentinelTargetDown`
- `SentinelTargetDegradedHighLatency`
- `SentinelOpenIncidentBacklog`

## Alertmanager routing

Alertmanager routes Prometheus alerts to backend webhook receiver:

- `alertmanager/alertmanager.yml`
- Receiver URL: `http://backend:8000/api/external-alerts/prometheus`

External alerts can be queried from:

- `GET /api/external-alerts`
- `PATCH /api/external-alerts/{id}/acknowledge` to mark an event as acknowledged
- `PATCH /api/external-alerts/{id}/unacknowledge` to reopen triage on an event
- External alerts are also shown in the React dashboard panel: `External Alerts (Alertmanager)`.
- Dashboard supports one-click acknowledge/unacknowledge toggle per external alert event.
- Repeated unacknowledged alerts with the same dedup key are collapsed into a single row (`repeat_count`, `last_seen_at`) to reduce noise.

Optional auto-ack rule can be enabled with environment variables:

- `SENTINEL_AUTO_ACK_REPEAT_THRESHOLD` (default `0`, disabled)
- `SENTINEL_AUTO_ACK_SEVERITIES` (default `warning,info`)

Example: auto-ack warning/info alerts after 3 repeats:

```powershell
$env:SENTINEL_AUTO_ACK_REPEAT_THRESHOLD = "3"
$env:SENTINEL_AUTO_ACK_SEVERITIES = "warning,info"
```

### Manual synthetic alert injection

To test the alert pipeline manually, write the payload with **UTF-8 without BOM** (PowerShell `Set-Content` adds a BOM by default — use `[System.IO.File]::WriteAllText` with `UTF8Encoding($false)`):

```powershell
$payload = Join-Path $env:TEMP 'sentinel-test-alert.json'
$start   = (Get-Date).ToUniversalTime().ToString('o')
$end     = (Get-Date).ToUniversalTime().AddMinutes(10).ToString('o')
$json    = @"
[
  {
    "labels":      { "alertname": "SyntheticPipelineAlert", "severity": "warning", "team": "ops" },
    "annotations": { "summary": "Synthetic alert injection", "description": "Manual test" },
    "startsAt": "$start",
    "endsAt":   "$end"
  }
]
"@
[System.IO.File]::WriteAllText($payload, $json, (New-Object System.Text.UTF8Encoding($false)))
curl.exe -X POST http://localhost:9093/api/v2/alerts -H "Content-Type: application/json" --data-binary "@$payload"
# After ~30 seconds (Alertmanager route interval) the alert appears in:
Invoke-RestMethod http://localhost:8001/api/external-alerts | Where-Object { $_.alert_name -eq 'SyntheticPipelineAlert' }
```

## Grafana auto-provisioning

Grafana starts with a preconfigured Prometheus datasource and a dashboard named `Sentinel Ops Overview`.

Provisioning files:

- `grafana/provisioning/datasources/prometheus.yml`
- `grafana/provisioning/dashboards/dashboards.yml`
- `grafana/dashboards/sentinel-overview.json`

Open Grafana and navigate to folder `Sentinel Ops` to view the dashboard.

## Stop system

```powershell
docker compose down
```

## Notes

- Seed monitoring targets are loaded from `backend/config/targets.example.json` on first boot.
- SQLite DB file persists at `backend/data/sentinel_ops.db`.
