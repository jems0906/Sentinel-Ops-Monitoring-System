from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import AlertEvent, Incident, IncidentNote
from app.schemas import AlertEventRead, IncidentNoteCreate, IncidentRead, IncidentUpdate

router = APIRouter(prefix="/api", tags=["incidents"])


@router.get("/incidents", response_model=list[IncidentRead])
def list_incidents(db: Session = Depends(get_db)) -> list[IncidentRead]:
    incidents = (
        db.execute(select(Incident).options(joinedload(Incident.notes)).order_by(desc(Incident.created_at)))
        .unique()
        .scalars()
        .all()
    )
    return incidents


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> IncidentRead:
    incident = (
        db.execute(select(Incident).options(joinedload(Incident.notes)).where(Incident.id == incident_id))
        .unique()
        .scalars()
        .first()
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.patch("/incidents/{incident_id}", response_model=IncidentRead)
def update_incident(incident_id: int, payload: IncidentUpdate, db: Session = Depends(get_db)) -> IncidentRead:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if payload.status is not None:
        incident.status = payload.status
    if payload.root_cause is not None:
        incident.root_cause = payload.root_cause

    db.commit()
    db.refresh(incident)
    return incident


@router.post("/incidents/{incident_id}/notes", response_model=IncidentRead)
def add_note(incident_id: int, payload: IncidentNoteCreate, db: Session = Depends(get_db)) -> IncidentRead:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    db.add(IncidentNote(incident_id=incident.id, note=payload.note))
    db.commit()
    incident = (
        db.execute(select(Incident).options(joinedload(Incident.notes)).where(Incident.id == incident_id))
        .unique()
        .scalars()
        .first()
    )
    assert incident is not None
    return incident


@router.get("/alerts", response_model=list[AlertEventRead])
def list_alerts(limit: int = 100, db: Session = Depends(get_db)) -> list[AlertEventRead]:
    alerts = db.execute(select(AlertEvent).order_by(desc(AlertEvent.created_at)).limit(limit)).scalars().all()
    return alerts
