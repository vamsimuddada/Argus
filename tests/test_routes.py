"""
ARGUS — Tests for API routes.
"""

import json
import pytest

from app.main import create_app


@pytest.fixture
def client():
    """Create a Flask test client with fresh state."""
    from app.routes import _clear_alerts
    app = create_app()
    app.config["TESTING"] = True
    _clear_alerts()
    with app.test_client() as client:
        yield client


# ── Health ───────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"


# ── Dashboard ────────────────────────────────────────────────────────────

def test_dashboard_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"ARGUS" in resp.data


# ── Create alert ─────────────────────────────────────────────────────────

def test_create_alert(client):
    resp = client.post(
        "/alerts",
        data=json.dumps({"title": "SSH brute force detected", "severity": "high", "source": "ids"}),
        content_type="application/json",
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["alert"]["title"] == "SSH brute force detected"
    assert data["alert"]["severity"] == "high"
    assert data["alert"]["status"] == "open"
    assert "storage" in data


def test_create_alert_validation_error(client):
    resp = client.post(
        "/alerts",
        data=json.dumps({"title": ""}),
        content_type="application/json",
    )
    assert resp.status_code == 422


def test_create_alert_no_body(client):
    resp = client.post("/alerts")
    assert resp.status_code == 400


# ── List alerts ──────────────────────────────────────────────────────────

def test_list_alerts_empty(client):
    resp = client.get("/alerts")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 0


def test_list_alerts_after_create(client):
    client.post(
        "/alerts",
        data=json.dumps({"title": "Alert 1", "severity": "low"}),
        content_type="application/json",
    )
    client.post(
        "/alerts",
        data=json.dumps({"title": "Alert 2", "severity": "critical"}),
        content_type="application/json",
    )
    resp = client.get("/alerts")
    data = resp.get_json()
    assert data["count"] == 2


def test_list_alerts_filter_severity(client):
    client.post(
        "/alerts",
        data=json.dumps({"title": "Low alert", "severity": "low"}),
        content_type="application/json",
    )
    client.post(
        "/alerts",
        data=json.dumps({"title": "Critical alert", "severity": "critical"}),
        content_type="application/json",
    )
    resp = client.get("/alerts?severity=critical")
    data = resp.get_json()
    assert data["count"] == 1
    assert data["alerts"][0]["severity"] == "critical"


# ── Get single alert ────────────────────────────────────────────────────

def test_get_alert(client):
    create_resp = client.post(
        "/alerts",
        data=json.dumps({"title": "Find me"}),
        content_type="application/json",
    )
    alert_id = create_resp.get_json()["alert"]["id"]

    resp = client.get(f"/alerts/{alert_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Find me"


def test_get_alert_not_found(client):
    resp = client.get("/alerts/nonexistent")
    assert resp.status_code == 404


# ── Acknowledge / Resolve ────────────────────────────────────────────────

def test_acknowledge_alert(client):
    create_resp = client.post(
        "/alerts",
        data=json.dumps({"title": "Ack me"}),
        content_type="application/json",
    )
    alert_id = create_resp.get_json()["alert"]["id"]

    resp = client.post(f"/alerts/{alert_id}/acknowledge")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "acknowledged"


def test_resolve_alert(client):
    create_resp = client.post(
        "/alerts",
        data=json.dumps({"title": "Resolve me"}),
        content_type="application/json",
    )
    alert_id = create_resp.get_json()["alert"]["id"]

    resp = client.post(f"/alerts/{alert_id}/resolve")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None


# ── Delete alert ─────────────────────────────────────────────────────────

def test_delete_alert(client):
    create_resp = client.post(
        "/alerts",
        data=json.dumps({"title": "Delete me"}),
        content_type="application/json",
    )
    alert_id = create_resp.get_json()["alert"]["id"]

    resp = client.delete(f"/alerts/{alert_id}")
    assert resp.status_code == 200

    # Confirm it's gone
    resp = client.get(f"/alerts/{alert_id}")
    assert resp.status_code == 404


def test_delete_alert_not_found(client):
    resp = client.delete("/alerts/nonexistent")
    assert resp.status_code == 404
