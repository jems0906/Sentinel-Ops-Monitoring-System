import json
import hashlib
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from prometheus_client import Counter, Gauge
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ExternalAlertEvent

router = APIRouter(prefix="/api/external-alerts", tags=["external-alerts"])

EXT_ALERTS_TOTAL = Counter(
    "sentinel_external_alerts_total",
    "Total external alerts ingested",
    ["alert_name", "severity", "status"],
)
EXT_ALERTS_UNACKED_GAUGE = Gauge(
    "sentinel_external_alerts_unacknowledged",
    "Current unacknowledged firing external alerts",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _should_auto_ack(severity: str, repeat_count: int) -> bool:
    threshold = settings.auto_ack_repeat_threshold
    if threshold <= 0:
        return False
    severities = {
        value.strip().lower()
        for value in settings.auto_ack_severities.split(",")
        if value.strip()
    }
    return severity.lower() in severities and repeat_count >= threshold


def _update_unacked_gauge(db: Session) -> None:
    count = db.scalar(
        select(func.count(ExternalAlertEvent.id)).where(
            ExternalAlertEvent.status == "firing",
            ExternalAlertEvent.acknowledged.is_(False),
        )
    ) or 0
    EXT_ALERTS_UNACKED_GAUGE.set(count)


@router.post("/prometheus")
def ingest_prometheus_alert(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    status = str(payload.get("status", "unknown"))
    first = (payload.get("alerts") or [{}])[0]
    labels = first.get("labels") or {}
    annotations = first.get("annotations") or {}

    alert_name = str(labels.get("alertname", payload.get("receiver", "unknown")))
    severity = str(labels.get("severity", "unknown"))
    summary = str(annotations.get("summary", ""))
    now = _utc_now()

    if first.get("fingerprint"):
        dedup_key = str(first.get("fingerprint"))
    else:
        dedup_basis = {
            "status": status,
            "alert_name": alert_name,
            "severity": severity,
            "labels": labels,
        }
        dedup_key = hashlib.sha256(json.dumps(dedup_basis, sort_keys=True).encode("utf-8")).hexdigest()

    existing = (
        db.execute(
            select(ExternalAlertEvent)
            .where(ExternalAlertEvent.dedup_key == dedup_key, ExternalAlertEvent.acknowledged.is_(False))
            .order_by(desc(ExternalAlertEvent.created_at))
            .limit(1)
        )
        .scalars()
        .first()
    )

    if existing:
        existing.status = status
        existing.severity = severity
        existing.summary = summary
        existing.payload = json.dumps(payload)
        existing.repeat_count = existing.repeat_count + 1
        existing.last_seen_at = now
        if _should_auto_ack(existing.severity, existing.repeat_count):
            existing.acknowledged = True
            existing.acknowledged_at = now
            existing.acknowledged_by = "auto-rule"
        db.commit()
        db.refresh(existing)
        EXT_ALERTS_TOTAL.labels(alert_name=alert_name, severity=severity, status="collapsed").inc()
        _update_unacked_gauge(db)
        return {
            "status": "collapsed",
            "id": existing.id,
            "alert_name": existing.alert_name,
            "severity": existing.severity,
            "repeat_count": existing.repeat_count,
            "acknowledged": existing.acknowledged,
            "acknowledged_by": existing.acknowledged_by,
            "received_at": now.isoformat(),
        }

    event = ExternalAlertEvent(
        source="alertmanager",
        status=status,
        alert_name=alert_name,
        severity=severity,
        summary=summary,
        payload=json.dumps(payload),
        dedup_key=dedup_key,
        repeat_count=1,
        last_seen_at=now,
    )
    if _should_auto_ack(event.severity, event.repeat_count):
        event.acknowledged = True
        event.acknowledged_at = now
        event.acknowledged_by = "auto-rule"
    db.add(event)
    db.commit()
    EXT_ALERTS_TOTAL.labels(alert_name=alert_name, severity=severity, status="stored").inc()
    _update_unacked_gauge(db)

    return {"status": "stored", "alert_name": alert_name, "severity": severity, "received_at": now.isoformat()}


@router.get("", response_model=list[dict[str, Any]])
def list_external_alerts(limit: int = 100, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(select(ExternalAlertEvent).order_by(desc(ExternalAlertEvent.created_at)).limit(limit)).scalars().all()
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "id": row.id,
                "source": row.source,
                "status": row.status,
                "alert_name": row.alert_name,
                "severity": row.severity,
                "summary": row.summary,
                "repeat_count": row.repeat_count,
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else row.created_at.isoformat(),
                "acknowledged": row.acknowledged,
                "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
                "acknowledged_by": row.acknowledged_by,
                "created_at": row.created_at.isoformat(),
            }
        )
    return result


@router.patch("/{event_id}/acknowledge", response_model=dict[str, Any])
def acknowledge_external_alert(event_id: int, payload: dict[str, Any] | None = None, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.get(ExternalAlertEvent, event_id)
    if not row:
        raise HTTPException(status_code=404, detail="External alert event not found")

    if not row.acknowledged:
        acknowledged_by = "ops-user"
        if payload and isinstance(payload.get("acknowledged_by"), str) and payload.get("acknowledged_by").strip():
            acknowledged_by = payload.get("acknowledged_by").strip()

        row.acknowledged = True
        row.acknowledged_at = _utc_now()
        row.acknowledged_by = acknowledged_by
        db.commit()
        db.refresh(row)

    return {
        "id": row.id,
        "acknowledged": row.acknowledged,
        "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "acknowledged_by": row.acknowledged_by,
    }


@router.patch("/{event_id}/unacknowledge", response_model=dict[str, Any])
def unacknowledge_external_alert(event_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.get(ExternalAlertEvent, event_id)
    if not row:
        raise HTTPException(status_code=404, detail="External alert event not found")

    if row.acknowledged:
        row.acknowledged = False
        row.acknowledged_at = None
        row.acknowledged_by = None
        db.commit()
        db.refresh(row)

    return {
        "id": row.id,
        "acknowledged": row.acknowledged,
        "acknowledged_at": row.acknowledged_at,
        "acknowledged_by": row.acknowledged_by,
    }
