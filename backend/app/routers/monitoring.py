import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AlertEvent, CheckResult, ExternalAlertEvent, Incident, Target
from app.monitor import uptime_percent_24h
from app.schemas import CheckResultRead, SummaryResponse, TargetCreate, TargetRead

router = APIRouter(prefix="/api", tags=["monitoring"])


@router.get("/targets", response_model=list[TargetRead])
def list_targets(db: Session = Depends(get_db)) -> list[TargetRead]:
    targets = db.execute(select(Target).order_by(Target.id)).scalars().all()
    return [
        TargetRead(
            id=t.id,
            name=t.name,
            target_type=t.target_type,
            address=t.address,
            interval_seconds=t.interval_seconds,
            enabled=t.enabled,
            extra=json.loads(t.extra_json or "{}"),
        )
        for t in targets
    ]


@router.post("/targets", response_model=TargetRead)
def create_target(payload: TargetCreate, db: Session = Depends(get_db)) -> TargetRead:
    target = Target(
        name=payload.name,
        target_type=payload.target_type,
        address=payload.address,
        interval_seconds=payload.interval_seconds,
        enabled=payload.enabled,
        extra_json=json.dumps(payload.extra),
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return TargetRead(
        id=target.id,
        name=target.name,
        target_type=target.target_type,
        address=target.address,
        interval_seconds=target.interval_seconds,
        enabled=target.enabled,
        extra=json.loads(target.extra_json or "{}"),
    )


@router.get("/checks", response_model=list[CheckResultRead])
def list_checks(limit: int = 100, db: Session = Depends(get_db)) -> list[CheckResultRead]:
    checks = db.execute(select(CheckResult).order_by(desc(CheckResult.created_at)).limit(limit)).scalars().all()
    return [
        CheckResultRead(
            id=c.id,
            target_id=c.target_id,
            status=c.status,
            latency_ms=c.latency_ms,
            message=c.message,
            details=json.loads(c.details or "{}"),
            created_at=c.created_at,
        )
        for c in checks
    ]


@router.get("/summary", response_model=SummaryResponse)
def summary(db: Session = Depends(get_db)) -> SummaryResponse:
    targets = db.scalar(select(func.count(Target.id))) or 0

    latest = db.execute(
        select(CheckResult)
        .order_by(CheckResult.target_id, desc(CheckResult.created_at))
    ).scalars().all()

    latest_by_target: dict[int, CheckResult] = {}
    for check in latest:
        latest_by_target.setdefault(check.target_id, check)

    up_targets = sum(1 for c in latest_by_target.values() if c.status == "up")
    degraded_targets = sum(1 for c in latest_by_target.values() if c.status == "degraded")
    down_targets = sum(1 for c in latest_by_target.values() if c.status == "down")

    open_incidents = db.scalar(select(func.count(Incident.id)).where(Incident.status == "open")) or 0
    recent_alerts = db.scalar(select(func.count(AlertEvent.id))) or 0

    ext_firing = db.scalar(select(func.count(ExternalAlertEvent.id)).where(ExternalAlertEvent.status == "firing")) or 0
    ext_unacked = db.scalar(
        select(func.count(ExternalAlertEvent.id)).where(
            ExternalAlertEvent.status == "firing",
            ExternalAlertEvent.acknowledged.is_(False),
        )
    ) or 0
    ext_auto_acked = db.scalar(
        select(func.count(ExternalAlertEvent.id)).where(
            ExternalAlertEvent.acknowledged_by == "auto-rule"
        )
    ) or 0

    return SummaryResponse(
        total_targets=targets,
        up_targets=up_targets,
        degraded_targets=degraded_targets,
        down_targets=down_targets,
        open_incidents=open_incidents,
        recent_alerts=recent_alerts,
        uptime_percent_24h=uptime_percent_24h(db),
        ext_firing=ext_firing,
        ext_unacked=ext_unacked,
        ext_auto_acked=ext_auto_acked,
    )


@router.post("/admin/run-cycle")
async def run_cycle(request: Request, force: bool = False) -> dict[str, str]:
    await request.app.state.monitor_engine.run_cycle(force=force)
    return {"status": "cycle_completed"}
