import asyncio
from contextlib import asynccontextmanager

from sqlalchemy import text

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.monitor import MonitorEngine, seed_targets_if_empty
from app.routers.health import router as health_router
from app.routers.external_alerts import router as external_alerts_router
from app.routers.incidents import router as incidents_router
from app.routers.monitoring import router as monitoring_router
from app.routers.simulation import router as simulation_router

monitor_task: asyncio.Task | None = None
monitor_engine = MonitorEngine(SessionLocal)


def _ensure_external_alert_columns() -> None:
    with engine.begin() as conn:
        existing_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(external_alert_events)")).fetchall()
        }
        if "acknowledged" not in existing_columns:
            conn.execute(
                text(
                    "ALTER TABLE external_alert_events ADD COLUMN acknowledged BOOLEAN NOT NULL DEFAULT 0"
                )
            )
        if "dedup_key" not in existing_columns:
            conn.execute(
                text(
                    "ALTER TABLE external_alert_events ADD COLUMN dedup_key VARCHAR(128) NOT NULL DEFAULT ''"
                )
            )
        if "repeat_count" not in existing_columns:
            conn.execute(
                text(
                    "ALTER TABLE external_alert_events ADD COLUMN repeat_count INTEGER NOT NULL DEFAULT 1"
                )
            )
        if "last_seen_at" not in existing_columns:
            conn.execute(
                text(
                    "ALTER TABLE external_alert_events ADD COLUMN last_seen_at DATETIME"
                )
            )
            conn.execute(
                text(
                    "UPDATE external_alert_events SET last_seen_at = created_at WHERE last_seen_at IS NULL"
                )
            )
        if "acknowledged_at" not in existing_columns:
            conn.execute(text("ALTER TABLE external_alert_events ADD COLUMN acknowledged_at DATETIME"))
        if "acknowledged_by" not in existing_columns:
            conn.execute(text("ALTER TABLE external_alert_events ADD COLUMN acknowledged_by VARCHAR(100)"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global monitor_task

    Base.metadata.create_all(bind=engine)
    _ensure_external_alert_columns()
    with SessionLocal() as db:
        seed_targets_if_empty(db)

    monitor_task = None
    if not settings.disable_monitor:
        monitor_task = asyncio.create_task(monitor_engine.run_forever())
    yield

    if monitor_task:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.state.monitor_engine = monitor_engine

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(monitoring_router)
app.include_router(incidents_router)
app.include_router(simulation_router)
app.include_router(external_alerts_router)


@app.get("/metrics")
def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
