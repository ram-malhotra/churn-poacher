"""
Pydantic Schemas for the Listener Agent and Signal Ingestion.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class NormalizedSignal(BaseModel):
    """Common normalized signal format across all external and synthetic sources."""
    source: str = Field(..., description="Source name: DATADOG_STATUS, HACKER_NEWS, REDDIT, G2_REVIEWS, TWITTER, SYNTHETIC")
    source_id: str = Field(..., description="Unique external ID or fingerprint")
    source_url: str = Field(..., description="Canonical source URL")
    vendor: str = Field(default="Datadog", description="Monitored competitor vendor")
    title: str = Field(default="", description="Post/incident title or headline")
    content: str = Field(..., description="Full text, comment, or incident description")
    author: Optional[str] = Field(default=None, description="Username or author handle if public")
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Time posted/published (UTC)")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Time ingested by Listener (UTC)")
    
    signal_type: str = Field(default="COMPLAINT", description="COMPLAINT, VENDOR_INCIDENT, DISCUSSION")
    complaint_category: str = Field(default="GENERAL_DISCUSSION", description="PRICING_SHOCK, OUTAGE, DEPRECATION, RELIABILITY, MIGRATION_INTENT, GENERAL_DISCUSSION, VENDOR_INCIDENT")
    sentiment: str = Field(default="NEUTRAL", description="POSITIVE, NEUTRAL, NEGATIVE, EXTREMELY_NEGATIVE")
    
    urgency_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Urgency rating (0.0 = low, 1.0 = emergency)")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Classification confidence")
    relevance_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Relevance to competitive takeout")
    
    extracted_evidence: Dict[str, Any] = Field(default_factory=dict, description="Key extracted metrics, numbers, quotes")
    is_synthetic: bool = Field(default=False, description="Flag indicating synthetic demo data vs real data")


class SourceExecutionSummary(BaseModel):
    """Operational summary of a specific signal ingestion source."""
    source_name: str
    connection_status: str  # "CONNECTED", "UNCONFIGURED", "UNAVAILABLE", "ERROR"
    monitoring_status: str  # "IDLE", "SCANNING", "COMPLETED", "SKIPPED"
    last_successful_scan: Optional[datetime] = None
    records_retrieved: int = 0
    relevant_signals: int = 0
    errors: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class IngestionSummary(BaseModel):
    """Structured report returned at the end of an ingestion cycle."""
    total_fetched: int = 0
    new_signals_saved: int = 0
    duplicates_skipped: int = 0
    signals_by_source: Dict[str, int] = Field(default_factory=dict)
    signals_by_category: Dict[str, int] = Field(default_factory=dict)
    high_urgency_count: int = 0
    errors: List[str] = Field(default_factory=list)
    execution_time_ms: int = 0
    sources: List[SourceExecutionSummary] = Field(default_factory=list)


class AdapterStatus(BaseModel):
    """Operational status of a signal ingestion adapter."""
    name: str
    enabled: bool
    status: str  # "AVAILABLE", "DISABLED_NO_CREDS", "DEGRADED"
    details: str
    last_poll_at: Optional[datetime] = None
    signals_last_run: int = 0


class ListenerStatusReport(BaseModel):
    """Full operational health and adapter readiness report."""
    is_running: bool = False
    monitoring_mode: str = "ON_DEMAND"  # "ON_DEMAND" or "SCHEDULED"
    demo_mode: bool = True
    adapters: List[AdapterStatus] = Field(default_factory=list)
    sources: List[SourceExecutionSummary] = Field(default_factory=list)
    last_run_at: Optional[datetime] = None
    total_signals_stored: int = 0


class ListenerMetricsReport(BaseModel):
    """Quantitative performance metrics for the Listener Agent."""
    total_signals_collected: int = 0
    real_signals_count: int = 0
    synthetic_signals_count: int = 0
    signals_by_source: Dict[str, int] = Field(default_factory=dict)
    signals_by_category: Dict[str, int] = Field(default_factory=dict)
    duplicates_rejected: int = 0
    high_urgency_signals: int = 0
