"""
ARGUS — S3 integration for alert log storage.
Uploads alert JSON to S3 and retrieves it.
Falls back to local file storage when S3 is unavailable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

LOCAL_STORAGE_DIR = Path(__file__).resolve().parent.parent / "data" / "alerts"


def _get_s3_client():
    """Return a boto3 S3 client, or None if AWS isn't configured."""
    try:
        import boto3
        region = os.getenv("AWS_REGION", "us-east-1")
        return boto3.client("s3", region_name=region)
    except Exception:
        return None


def _bucket_name() -> str:
    return os.getenv("S3_BUCKET_NAME", "argus-alert-logs")


def upload_alert(alert_dict: dict) -> dict:
    """
    Upload an alert JSON to S3.
    Falls back to local file if S3 is unavailable.
    Returns metadata about where it was stored.
    """
    alert_id = alert_dict.get("id", "unknown")
    key = f"alerts/{alert_id}.json"
    body = json.dumps(alert_dict, indent=2)

    s3 = _get_s3_client()
    if s3:
        try:
            s3.put_object(
                Bucket=_bucket_name(),
                Key=key,
                Body=body,
                ContentType="application/json",
            )
            return {"storage": "s3", "bucket": _bucket_name(), "key": key}
        except Exception as exc:
            # Fall through to local storage
            pass

    # Local fallback
    LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    local_path = LOCAL_STORAGE_DIR / f"{alert_id}.json"
    local_path.write_text(body, encoding="utf-8")
    return {"storage": "local", "path": str(local_path)}


def get_alert_from_s3(alert_id: str) -> Optional[dict]:
    """Retrieve an alert JSON from S3 by its ID."""
    s3 = _get_s3_client()
    if not s3:
        # Try local fallback
        local_path = LOCAL_STORAGE_DIR / f"{alert_id}.json"
        if local_path.exists():
            return json.loads(local_path.read_text(encoding="utf-8"))
        return None

    try:
        response = s3.get_object(
            Bucket=_bucket_name(),
            Key=f"alerts/{alert_id}.json",
        )
        return json.loads(response["Body"].read().decode("utf-8"))
    except Exception:
        # Try local fallback
        local_path = LOCAL_STORAGE_DIR / f"{alert_id}.json"
        if local_path.exists():
            return json.loads(local_path.read_text(encoding="utf-8"))
        return None


def list_alerts_s3(max_keys: int = 100) -> list[str]:
    """List alert IDs stored in S3."""
    s3 = _get_s3_client()
    if not s3:
        # Local fallback
        if LOCAL_STORAGE_DIR.exists():
            return [f.stem for f in LOCAL_STORAGE_DIR.glob("*.json")]
        return []

    try:
        response = s3.list_objects_v2(
            Bucket=_bucket_name(),
            Prefix="alerts/",
            MaxKeys=max_keys,
        )
        keys = [obj["Key"] for obj in response.get("Contents", [])]
        return [k.split("/")[-1].replace(".json", "") for k in keys if k.endswith(".json")]
    except Exception:
        if LOCAL_STORAGE_DIR.exists():
            return [f.stem for f in LOCAL_STORAGE_DIR.glob("*.json")]
        return []
