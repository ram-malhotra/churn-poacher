"""
Crustdata Intelligence Extraction ORM Models.
Provides structured persistence for entities, searches, and granular evidence provenance.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Float, Boolean, JSON, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class IntelligenceEntity(Base, TimestampMixin):
    """
    Master record for an extracted business or person entity.
    Maintains primary identifiers to eliminate redundant enrichment calls.
    """
    __tablename__ = "intelligence_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(20), index=True)  # COMPANY, PERSON
    primary_name: Mapped[str] = mapped_column(String(200), index=True)
    primary_domain: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    profile_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)

    # Full structured profile snapshot
    raw_profile: Mapped[dict] = mapped_column(JSON, default=dict)

    # Telemetry and freshness
    data_freshness: Mapped[str] = mapped_column(String(50), default="CACHED")  # CACHED, REALTIME_CRAWL
    enrichment_level: Mapped[str] = mapped_column(String(50), default="LEVEL_2_STANDARD")
    credits_consumed: Mapped[float] = mapped_column(Float, default=0.0)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    last_enriched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    evidence: Mapped[List["IntelligenceEvidence"]] = relationship(
        "IntelligenceEvidence", back_populates="entity", cascade="all, delete-orphan"
    )
    searches: Mapped[List["IntelligenceSearch"]] = relationship(
        "IntelligenceSearch", back_populates="selected_entity"
    )


class IntelligenceSearch(Base):
    """
    Audit record for every Level 1 Search query and candidate selection.
    """
    __tablename__ = "intelligence_searches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    search_query: Mapped[str] = mapped_column(String(255), index=True)
    entity_type: Mapped[str] = mapped_column(String(20), default="UNKNOWN", index=True)
    search_status: Mapped[str] = mapped_column(
        String(50), default="COMPLETED", index=True
    )  # COMPLETED, AMBIGUOUS, NO_MATCH, FAILED
    
    selected_entity_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("intelligence_entities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    candidates: Mapped[list] = mapped_column(JSON, default=list)
    credits_consumed: Mapped[float] = mapped_column(Float, default=0.0)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    selected_entity: Mapped[Optional["IntelligenceEntity"]] = relationship(
        "IntelligenceEntity", back_populates="searches"
    )


class IntelligenceEvidence(Base):
    """
    Provenance record for every individual claim, technographic item, or fact.
    Strictly follows VERIFIED / INFERRED / UNKNOWN classifications.
    """
    __tablename__ = "intelligence_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("intelligence_entities.id", ondelete="CASCADE"), index=True
    )
    data_category: Mapped[str] = mapped_column(String(50), index=True)  # TECHNOGRAPHICS, FUNDING, etc.
    claim: Mapped[str] = mapped_column(Text)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    retrieval_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    verification_classification: Mapped[str] = mapped_column(
        String(50), default="VERIFIED", index=True
    )  # VERIFIED, INFERRED, UNKNOWN
    original_source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    entity: Mapped["IntelligenceEntity"] = relationship("IntelligenceEntity", back_populates="evidence")


class CrustdataBudgetLedger(Base, TimestampMixin):
    """
    Maintains the application-level Crustdata spending budget and tracked cumulative usage.
    Singleton record with id='global'.
    """
    __tablename__ = "crustdata_budget_ledgers"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default="global")
    total_budget: Mapped[float] = mapped_column(Float, default=1200.0)
    used_credits: Mapped[float] = mapped_column(Float, default=0.0)
    mock_used_credits: Mapped[float] = mapped_column(Float, default=0.0)


class CrustdataBudgetHistory(Base):
    """
    Audit log of all budget increases and credit usage transactions.
    """
    __tablename__ = "crustdata_budget_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action: Mapped[str] = mapped_column(String(50), index=True)  # INITIAL_BUDGET, USAGE, BUDGET_INCREASE
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    budget_before: Mapped[float] = mapped_column(Float, default=1200.0)
    budget_after: Mapped[float] = mapped_column(Float, default=1200.0)
    used_before: Mapped[float] = mapped_column(Float, default=0.0)
    used_after: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(String(500), default="")
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
