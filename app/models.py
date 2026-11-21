"""
ARGUS — Pydantic models for alerts and system health.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertCreate(BaseModel):
    """Payload for creating a new alert."""
    title: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="")
    severity: Severity = Field(default=Severity.MEDIUM)
    source: str = Field(default="manual", max_length=128)


class Alert(BaseModel):
    """Full alert object stored and returned by the API."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str
    description: str = ""
    severity: Severity = Severity.MEDIUM
    status: AlertStatus = AlertStatus.OPEN
    source: str = "manual"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    resolved_at: Optional[str] = None

    def resolve(self) -> None:
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc).isoformat()

    def acknowledge(self) -> None:
        self.status = AlertStatus.ACKNOWLEDGED
