"""
Campaign ORM Model.
Stores active and historical multi-vendor competitive takeout campaigns.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Boolean, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), index=True)
    original_objective: Mapped[str] = mapped_column(Text)
    
    # Target and alternative technologies
    target_vendors: Mapped[List[str]] = mapped_column(JSON, default=list)  # e.g. ["Datadog"] or ["Splunk"]
    alternative_vendors: Mapped[List[str]] = mapped_column(JSON, default=list)  # e.g. ["SigNoz", "Grafana"] or ["Elastic", "OpenSearch"]
    
    # Firmographic criteria
    geography: Mapped[List[str]] = mapped_column(JSON, default=list)  # e.g. ["US", "India"]
    company_size: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {"min": 200, "max": 5000}
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Pain points & intent
    pain_points: Mapped[List[str]] = mapped_column(JSON, default=list)
    migration_intent: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Execution mode & lifecycle state
    monitoring_mode: Mapped[str] = mapped_column(String(50), default="ON_DEMAND")  # "ON_DEMAND" or "SCHEDULED"
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", index=True)  # "ACTIVE", "PAUSED", "COMPLETED"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_payload: Mapped[dict] = mapped_column(JSON, default=dict)
