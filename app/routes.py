"""
ARGUS — API route blueprints.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request, render_template

from .models import Alert, AlertCreate, AlertStatus, Severity
from .s3_client import upload_alert, get_alert_from_s3

api = Blueprint("api", __name__)

# ── In-memory store (replaced by a DB in production) ────────────────────
_alerts: dict[str, Alert] = {}


def _clear_alerts() -> None:
    """Clear all alerts — used by test fixtures."""
    _alerts.clear()


# ── Health ───────────────────────────────────────────────────────────────
@api.route("/health", methods=["GET"])
def health():
    """Health check endpoint for load balancers / uptime monitors."""
    return jsonify({"status": "healthy", "version": "0.1.0"}), 200


# ── Dashboard ────────────────────────────────────────────────────────────
@api.route("/", methods=["GET"])
def dashboard():
    """Render the alert dashboard."""
    alerts_list = sorted(
        _alerts.values(),
        key=lambda a: a.created_at,
        reverse=True,
    )
    stats = {
        "total": len(alerts_list),
        "open": sum(1 for a in alerts_list if a.status == AlertStatus.OPEN),
        "critical": sum(1 for a in alerts_list if a.severity == Severity.CRITICAL),
        "resolved": sum(1 for a in alerts_list if a.status == AlertStatus.RESOLVED),
    }
    return render_template("dashboard.html", alerts=alerts_list, stats=stats)


# ── List alerts ──────────────────────────────────────────────────────────
@api.route("/alerts", methods=["GET"])
def list_alerts():
    """Return all alerts, newest first. Optional ?status= and ?severity= filters."""
    alerts_list = list(_alerts.values())

    # Filters
    status_filter = request.args.get("status")
    if status_filter:
        alerts_list = [a for a in alerts_list if a.status.value == status_filter]

    severity_filter = request.args.get("severity")
    if severity_filter:
        alerts_list = [a for a in alerts_list if a.severity.value == severity_filter]

    alerts_list.sort(key=lambda a: a.created_at, reverse=True)

    return jsonify({
        "count": len(alerts_list),
        "alerts": [a.model_dump() for a in alerts_list],
    }), 200


# ── Get single alert ────────────────────────────────────────────────────
@api.route("/alerts/<alert_id>", methods=["GET"])
def get_alert(alert_id: str):
    """Get a single alert by ID."""
    alert = _alerts.get(alert_id)
    if not alert:
        return jsonify({"error": "Alert not found"}), 404
    return jsonify(alert.model_dump()), 200


# ── Create alert ─────────────────────────────────────────────────────────
@api.route("/alerts", methods=["POST"])
def create_alert():
    """
    Create a new alert.
    Body: {"title": "...", "description": "...", "severity": "low|medium|high|critical", "source": "..."}
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        payload = AlertCreate(**data)
    except Exception as exc:
        return jsonify({"error": f"Validation failed: {exc}"}), 422

    alert = Alert(
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        source=payload.source,
    )
    _alerts[alert.id] = alert

    # Persist to S3 (or local fallback)
    storage_info = upload_alert(alert.model_dump())

    return jsonify({
        "alert": alert.model_dump(),
        "storage": storage_info,
    }), 201


# ── Update alert status ─────────────────────────────────────────────────
@api.route("/alerts/<alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert(alert_id: str):
    """Acknowledge an alert."""
    alert = _alerts.get(alert_id)
    if not alert:
        return jsonify({"error": "Alert not found"}), 404
    alert.acknowledge()
    return jsonify(alert.model_dump()), 200


@api.route("/alerts/<alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id: str):
    """Resolve an alert."""
    alert = _alerts.get(alert_id)
    if not alert:
        return jsonify({"error": "Alert not found"}), 404
    alert.resolve()
    return jsonify(alert.model_dump()), 200


# ── Delete alert ─────────────────────────────────────────────────────────
@api.route("/alerts/<alert_id>", methods=["DELETE"])
def delete_alert(alert_id: str):
    """Delete an alert by ID."""
    if alert_id not in _alerts:
        return jsonify({"error": "Alert not found"}), 404
    del _alerts[alert_id]
    return jsonify({"deleted": alert_id}), 200
