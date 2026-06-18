import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone

import dns.resolver
import httpx
from ping3 import ping
from prometheus_client import Counter, Gauge
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AlertEvent, CheckResult, Incident, IncidentNote, Target
from app.notifications import send_email_alert
from app.simulation import simulation_registry

CHECK_COUNTER = Counter("sentinel_checks_total", "Total checks run", ["target", "status"])
TARGET_STATUS_GAUGE = Gauge("sentinel_target_status", "Target state (1 up, 0.5 degraded, 0 down)", ["target"])
LATENCY_GAUGE = Gauge("sentinel_target_latency_ms", "Target latency in ms", ["target"])
OPEN_INCIDENTS_GAUGE = Gauge("sentinel_open_incidents", "Open incidents by severity", ["severity"])
INCIDENTS_BY_STATUS_GAUGE = Gauge("sentinel_incidents_total_by_status", "Total incidents by status", ["status"])
ALERTS_BY_CHANNEL_GAUGE = Gauge("sentinel_alert_events_total", "Total alert events by channel", ["channel"])
logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MonitorEngine:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory
        self._last_run_by_target: dict[int, float] = {}

    async def run_forever(self) -> None:
        while True:
            try:
                await self.run_cycle()
            except Exception:
                logger.exception("Monitor cycle failed")
            await asyncio.sleep(settings.monitor_interval_seconds)

    async def run_cycle(self, force: bool = False) -> None:
        with self.session_factory() as db:
            targets = db.execute(select(Target).where(Target.enabled.is_(True))).scalars().all()
            for target in targets:
                try:
                    if not force and not self._is_due(target):
                        continue
                    result = await self._check_target(target)
                    saved = self._save_check_result(db, target, result)
                    self._update_metrics(target.name, saved.status, saved.latency_ms)
                    self._process_incident_logic(db, target, saved)
                    self._last_run_by_target[target.id] = time.time()
                except Exception:
                    logger.exception("Check processing failed for target_id=%s name=%s", target.id, target.name)

            self._update_incident_metrics(db)
            db.commit()

    def _is_due(self, target: Target) -> bool:
        last = self._last_run_by_target.get(target.id, 0)
        return (time.time() - last) >= target.interval_seconds

    async def _check_target(self, target: Target) -> dict:
        simulation = simulation_registry.get(target.id)
        extra = self._safe_json(target.extra_json)

        if simulation.mode == "server_down":
            return {"status": "down", "latency_ms": None, "message": "Simulated server outage", "details": {"simulated": True}}
        if simulation.mode == "dns_failure" and target.target_type == "dns":
            return {"status": "down", "latency_ms": None, "message": "Simulated DNS resolution failure", "details": {"simulated": True}}
        if simulation.mode == "service_crash" and target.target_type == "http":
            return {"status": "down", "latency_ms": None, "message": "Simulated service crash", "details": {"simulated": True}}

        try:
            if target.target_type == "ping":
                return await self._check_ping(target.address, extra)
            if target.target_type == "http":
                return await self._check_http(target.address, extra)
            if target.target_type == "dns":
                return await self._check_dns(target.address, extra)
            return {"status": "down", "latency_ms": None, "message": "Unsupported target type", "details": {}}
        except Exception as exc:
            return {"status": "down", "latency_ms": None, "message": str(exc), "details": {"error": type(exc).__name__}}

    async def _check_ping(self, address: str, extra: dict) -> dict:
        timeout = float(extra.get("timeout", 2))
        latency_sec = await asyncio.to_thread(ping, address, timeout=timeout)
        if latency_sec is None:
            return {"status": "down", "latency_ms": None, "message": "Ping timeout", "details": {"address": address}}

        latency_ms = round(latency_sec * 1000, 2)
        if latency_ms > 250:
            status = "degraded"
            message = f"High latency detected: {latency_ms}ms"
        else:
            status = "up"
            message = f"Ping success: {latency_ms}ms"
        return {"status": status, "latency_ms": latency_ms, "message": message, "details": {"address": address}}

    async def _check_http(self, url: str, extra: dict) -> dict:
        timeout = float(extra.get("timeout", 5))
        expected_status = int(extra.get("expected_status", 200))
        start = time.time()
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)

        latency_ms = round((time.time() - start) * 1000, 2)
        status = "up" if response.status_code == expected_status else "down"
        if status == "up" and latency_ms > 700:
            status = "degraded"

        return {
            "status": status,
            "latency_ms": latency_ms,
            "message": f"HTTP {response.status_code} from {url}",
            "details": {"expected_status": expected_status, "actual_status": response.status_code},
        }

    async def _check_dns(self, domain: str, extra: dict) -> dict:
        resolver_ip = extra.get("resolver", "8.8.8.8")
        record_type = extra.get("record_type", "A")

        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [resolver_ip]

        start = time.time()
        answers = await asyncio.to_thread(resolver.resolve, domain, record_type)
        latency_ms = round((time.time() - start) * 1000, 2)
        resolved = [r.to_text() for r in answers]

        status = "up" if resolved else "down"
        if latency_ms > 300 and status == "up":
            status = "degraded"

        return {
            "status": status,
            "latency_ms": latency_ms,
            "message": f"DNS {record_type} lookup for {domain}",
            "details": {"resolver": resolver_ip, "records": resolved},
        }

    def _save_check_result(self, db: Session, target: Target, result: dict) -> CheckResult:
        simulation = simulation_registry.get(target.id)
        if simulation.mode == "high_latency":
            result["status"] = "degraded"
            result["latency_ms"] = float(simulation.latency_ms or 900)
            result["message"] = f"Simulated high latency: {result['latency_ms']}ms"
            result.setdefault("details", {})["simulated"] = True

        check = CheckResult(
            target_id=target.id,
            status=result["status"],
            latency_ms=result.get("latency_ms"),
            message=result["message"],
            details=json.dumps(result.get("details", {})),
        )
        db.add(check)
        db.flush()
        return check

    def _process_incident_logic(self, db: Session, target: Target, check: CheckResult) -> None:
        open_incident = db.execute(
            select(Incident).where(Incident.target_id == target.id, Incident.status == "open").order_by(Incident.created_at.desc())
        ).scalars().first()

        if check.status in {"down", "degraded"} and not open_incident:
            severity = "high" if check.status == "down" else "medium"
            incident = Incident(
                target_id=target.id,
                title=f"{target.name} is {check.status}",
                severity=severity,
                status="open",
                trigger_result_id=check.id,
            )
            db.add(incident)
            db.flush()
            db.add(IncidentNote(incident_id=incident.id, note=check.message))
            self._emit_alert(db, incident, f"ALERT: {incident.title}", check.message)
            return

        if check.status == "up" and open_incident:
            open_incident.status = "resolved"
            open_incident.resolved_at = _utc_now()
            db.add(IncidentNote(incident_id=open_incident.id, note="Auto-resolved after healthy check."))
            self._emit_alert(db, open_incident, f"RESOLVED: {open_incident.title}", "Service recovered.")

    def _emit_alert(self, db: Session, incident: Incident, subject: str, body: str) -> None:
        dashboard_alert = AlertEvent(incident_id=incident.id, channel="dashboard", subject=subject, body=body)
        db.add(dashboard_alert)

        email_sent = False
        try:
            email_sent = send_email_alert(subject, body)
        except Exception:
            email_sent = False

        if email_sent:
            db.add(AlertEvent(incident_id=incident.id, channel="email", subject=subject, body=body))

    def _update_metrics(self, target_name: str, status: str, latency_ms: float | None) -> None:
        CHECK_COUNTER.labels(target=target_name, status=status).inc()
        state_value = 1 if status == "up" else 0.5 if status == "degraded" else 0
        TARGET_STATUS_GAUGE.labels(target=target_name).set(state_value)
        if latency_ms is not None:
            LATENCY_GAUGE.labels(target=target_name).set(latency_ms)

    def _update_incident_metrics(self, db: Session) -> None:
        severities = ["low", "medium", "high"]
        for severity in severities:
            count = db.scalar(
                select(func.count(Incident.id)).where(Incident.status == "open", Incident.severity == severity)
            ) or 0
            OPEN_INCIDENTS_GAUGE.labels(severity=severity).set(count)

        for status in ["open", "resolved"]:
            count = db.scalar(select(func.count(Incident.id)).where(Incident.status == status)) or 0
            INCIDENTS_BY_STATUS_GAUGE.labels(status=status).set(count)

        for channel in ["dashboard", "email"]:
            count = db.scalar(select(func.count(AlertEvent.id)).where(AlertEvent.channel == channel)) or 0
            ALERTS_BY_CHANNEL_GAUGE.labels(channel=channel).set(count)

    @staticmethod
    def _safe_json(raw: str) -> dict:
        try:
            return json.loads(raw)
        except Exception:
            return {}


def seed_targets_if_empty(db: Session, seed_file: str = "./config/targets.example.json") -> None:
    count = db.scalar(select(func.count(Target.id))) or 0
    if count > 0:
        return

    try:
        with open(seed_file, "r", encoding="utf-8") as file:
            targets = json.load(file)
    except FileNotFoundError:
        targets = []

    for item in targets:
        db.add(
            Target(
                name=item["name"],
                target_type=item["target_type"],
                address=item["address"],
                interval_seconds=item.get("interval_seconds", 15),
                enabled=item.get("enabled", True),
                extra_json=json.dumps(item.get("extra", {})),
            )
        )
    db.commit()


def uptime_percent_24h(db: Session) -> float:
    since = _utc_now() - timedelta(hours=24)
    rows = db.execute(select(CheckResult.status).where(CheckResult.created_at >= since)).all()
    if not rows:
        return 100.0

    healthy = sum(1 for row in rows if row[0] == "up")
    return round((healthy / len(rows)) * 100, 2)
