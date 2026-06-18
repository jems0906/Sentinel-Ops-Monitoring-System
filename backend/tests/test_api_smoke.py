import os

from fastapi.testclient import TestClient

# Keep monitor loop mostly idle during tests.
os.environ["SENTINEL_MONITOR_INTERVAL_SECONDS"] = "3600"
os.environ["SENTINEL_DATABASE_URL"] = "sqlite:///./data/test_sentinel_ops.db"
os.environ["SENTINEL_DISABLE_MONITOR"] = "true"

from app.main import app  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.config import settings  # noqa: E402


def _reset_test_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_health_endpoint() -> None:
    _reset_test_db()
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_target_create_and_list() -> None:
    _reset_test_db()
    with TestClient(app) as client:
        payload = {
            "name": "Test HTTP",
            "target_type": "http",
            "address": "http://example.com",
            "interval_seconds": 30,
            "enabled": True,
            "extra": {"expected_status": 200, "timeout": 5},
        }
        created = client.post("/api/targets", json=payload)
        assert created.status_code == 200

        listed = client.get("/api/targets")
        assert listed.status_code == 200
        data = listed.json()
        assert isinstance(data, list)
        assert any(item["name"] == "Test HTTP" for item in data)


def test_admin_run_cycle_endpoint() -> None:
    _reset_test_db()
    with TestClient(app) as client:
        response = client.post("/api/admin/run-cycle", params={"force": "true"})
        assert response.status_code == 200
        assert response.json().get("status") == "cycle_completed"


def test_external_alert_acknowledge_flow() -> None:
    _reset_test_db()
    with TestClient(app) as client:
        payload = {
            "status": "firing",
            "receiver": "backend-webhook",
            "alerts": [
                {
                    "labels": {"alertname": "SyntheticPipelineAlert", "severity": "warning", "team": "ops"},
                    "annotations": {"summary": "Synthetic alert injection"},
                }
            ],
        }

        ingest = client.post("/api/external-alerts/prometheus", json=payload)
        assert ingest.status_code == 200

        listed = client.get("/api/external-alerts", params={"limit": 1})
        assert listed.status_code == 200
        event = listed.json()[0]
        assert event["acknowledged"] is False

        ack = client.patch(f"/api/external-alerts/{event['id']}/acknowledge", json={"acknowledged_by": "ops-test"})
        assert ack.status_code == 200

        listed_after = client.get("/api/external-alerts", params={"limit": 1})
        assert listed_after.status_code == 200
        event_after = listed_after.json()[0]
        assert event_after["acknowledged"] is True
        assert event_after["acknowledged_by"] == "ops-test"
        assert event_after["acknowledged_at"] is not None

        unack = client.patch(f"/api/external-alerts/{event['id']}/unacknowledge")
        assert unack.status_code == 200

        listed_unack = client.get("/api/external-alerts", params={"limit": 1})
        assert listed_unack.status_code == 200
        event_unack = listed_unack.json()[0]
        assert event_unack["acknowledged"] is False
        assert event_unack["acknowledged_by"] is None
        assert event_unack["acknowledged_at"] is None


def test_external_alert_deduplication_flow() -> None:
    _reset_test_db()
    with TestClient(app) as client:
        payload = {
            "status": "firing",
            "receiver": "backend-webhook",
            "alerts": [
                {
                    "labels": {"alertname": "SentinelTargetDown", "severity": "critical", "team": "ops"},
                    "annotations": {"summary": "Target down: Public DNS Check"},
                }
            ],
        }

        first = client.post("/api/external-alerts/prometheus", json=payload)
        assert first.status_code == 200
        assert first.json()["status"] == "stored"

        second = client.post("/api/external-alerts/prometheus", json=payload)
        assert second.status_code == 200
        assert second.json()["status"] == "collapsed"

        listed = client.get("/api/external-alerts", params={"limit": 10})
        assert listed.status_code == 200
        data = listed.json()
        assert len(data) == 1
        assert data[0]["repeat_count"] == 2
        assert data[0]["alert_name"] == "SentinelTargetDown"


def test_external_alert_auto_ack_rule_flow() -> None:
    _reset_test_db()
    previous_threshold = settings.auto_ack_repeat_threshold
    previous_severities = settings.auto_ack_severities
    settings.auto_ack_repeat_threshold = 2
    settings.auto_ack_severities = "warning"

    try:
        with TestClient(app) as client:
            payload = {
                "status": "firing",
                "receiver": "backend-webhook",
                "alerts": [
                    {
                        "labels": {"alertname": "AutoAckRuleCheck", "severity": "warning", "team": "ops"},
                        "annotations": {"summary": "Auto ack rule check"},
                    }
                ],
            }

            first = client.post("/api/external-alerts/prometheus", json=payload)
            assert first.status_code == 200
            assert first.json()["status"] == "stored"

            second = client.post("/api/external-alerts/prometheus", json=payload)
            assert second.status_code == 200
            assert second.json()["status"] == "collapsed"

            listed = client.get("/api/external-alerts", params={"limit": 10})
            assert listed.status_code == 200
            data = listed.json()
            assert len(data) == 1
            assert data[0]["repeat_count"] == 2
            assert data[0]["acknowledged"] is True
            assert data[0]["acknowledged_by"] == "auto-rule"
            assert data[0]["acknowledged_at"] is not None
    finally:
        settings.auto_ack_repeat_threshold = previous_threshold
        settings.auto_ack_severities = previous_severities
