from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Incident, IncidentNote, Target
from app.schemas import SimulationToggle
from app.simulation import simulation_registry

router = APIRouter(prefix="/api", tags=["simulation"])


@router.get("/simulations")
def list_simulations() -> dict:
    states = simulation_registry.snapshot()
    return {
        str(target_id): {"mode": state.mode, "latency_ms": state.latency_ms}
        for target_id, state in states.items()
    }


@router.post("/simulations/toggle")
def toggle_simulation(payload: SimulationToggle, db: Session = Depends(get_db)) -> dict:
    target = db.get(Target, payload.target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    if payload.mode == "none":
        simulation_registry.clear(payload.target_id)
        return {"message": "Simulation cleared"}

    if payload.mode not in {"server_down", "high_latency", "dns_failure", "service_crash"}:
        raise HTTPException(status_code=400, detail="Invalid simulation mode")

    simulation_registry.set(payload.target_id, payload.mode, payload.latency_ms)
    return {"message": f"Simulation '{payload.mode}' enabled"}


@router.post("/simulations/restart-service/{target_id}")
def restart_service(target_id: int, db: Session = Depends(get_db)) -> dict:
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    simulation_registry.clear(target_id)

    incident = (
        db.query(Incident)
        .filter(Incident.target_id == target_id, Incident.status == "open")
        .order_by(Incident.created_at.desc())
        .first()
    )
    if incident:
        db.add(IncidentNote(incident_id=incident.id, note="Service restart issued from simulation endpoint."))
    db.commit()

    return {"message": "Service restart command simulated and state cleared"}
