"""
ARGUS — AWS CloudWatch Metrics & Monitoring Integration.
Publishes custom metrics to CloudWatch for incoming alerts.
"""

from __future__ import annotations

import os
from typing import Optional


def _get_cloudwatch_client():
    """Return a boto3 CloudWatch client, or None if unavailable."""
    try:
        import boto3
        region = os.getenv("AWS_REGION", "ap-southeast-2")
        return boto3.client("cloudwatch", region_name=region)
    except Exception:
        return None


def publish_alert_metric(severity: str, source: str) -> bool:
    """
    Publish an AlertCount custom metric to AWS CloudWatch.
    Namespace: ARGUS/Security
    Dimensions: Severity, Source
    """
    cw = _get_cloudwatch_client()
    if not cw:
        return False

    try:
        cw.put_metric_data(
            Namespace="ARGUS/Security",
            MetricData=[
                {
                    "MetricName": "AlertTriggered",
                    "Dimensions": [
                        {"Name": "Severity", "Value": severity.upper()},
                        {"Name": "Source", "Value": source},
                    ],
                    "Value": 1.0,
                    "Unit": "Count",
                }
            ],
        )
        return True
    except Exception:
        return False
