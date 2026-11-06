"""
Pydantic Schemas for Crustdata Intelligence Extraction.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    COMPANY = "COMPANY"
    PERSON = "PERSON"
    UNKNOWN = "UNKNOWN"


class EnrichmentLevel(str, Enum):
    LEVEL_1_SEARCH = "LEVEL_1_SEARCH"          # Match candidates, 0-1 credit
    LEVEL_2_STANDARD = "LEVEL_2_STANDARD"      # Cached/Database profile, 1-2 credits
    LEVEL_3_DEEP = "LEVEL_3_DEEP"              # Live web/realtime scrape, 10-25 credits


class VerificationClassification(str, Enum):
    VERIFIED = "VERIFIED"    # Explicit confirmation from authentic official source
    INFERRED = "INFERRED"    # Derived from job descriptions, text references, or patterns
    UNKNOWN = "UNKNOWN"      # Data not available or unconfirmed


class CrustdataCreditsInfo(BaseModel):
    """Account credits status."""
    total_credits: float = 0.0
    remaining_credits: float = 0.0
    used_credits: float = 0.0
    renewal_date: Optional[str] = None
    enabled_endpoints: List[str] = Field(default_factory=list)
    is_mock: bool = False
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class EntityCandidate(BaseModel):
    """Candidate entity returned from Level 1 Search."""
    candidate_id: str
    entity_type: EntityType
    name: str
    primary_domain: Optional[str] = None
    profile_url: Optional[str] = None
    current_title: Optional[str] = None
    company_name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    logo_url: Optional[str] = None
    confidence_score: float = 0.0
    is_ambiguous: bool = False
    is_mock: bool = False
    data_origin: str = "LIVE"  # "LIVE", "CACHED", "DEMO"
    source: str = "Crustdata API v2025-11-01"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    verification_status: str = "VERIFIED"  # "VERIFIED", "UNVERIFIED", "UNKNOWN"
    buying_intent_status: str = "INTELLIGENCE_ONLY"  # "INTELLIGENCE_ONLY", "LINKED_TO_DISTRESS_SIGNAL"
    buying_intent_note: Optional[str] = None
    provenance: Dict[str, str] = Field(default_factory=dict)


class EntitySearchRequest(BaseModel):
    """Search request payload."""
    query: str
    entity_type: Optional[EntityType] = None  # If None, auto-detected
    limit: int = Field(default=5, ge=1, le=20)
    mode: str = "LIVE"  # "LIVE" or "DEMO"


class EntitySearchResponse(BaseModel):
    """Search response payload."""
    query: str
    detected_type: EntityType
    candidates: List[EntityCandidate]
    is_ambiguous: bool
    credits_consumed: float
    is_mock: bool = False
    data_origin: str = "LIVE"
    interpretation: Optional[Dict[str, Any]] = None
    buying_intent_distinction: Optional[str] = None


class IntelligenceEvidenceItem(BaseModel):
    """Granular evidence provenance item."""
    data_category: str  # e.g., "TECHNOGRAPHICS", "FUNDING", "JOB_POSTINGS", "FIRMOGRAPHICS"
    claim: str
    source_url: Optional[str] = None
    retrieval_timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = 0.8
    verification_classification: VerificationClassification = VerificationClassification.VERIFIED
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TechnographicItem(BaseModel):
    name: str
    category: str
    classification: VerificationClassification = VerificationClassification.VERIFIED
    source_url: Optional[str] = None
    first_detected_at: Optional[str] = None
    updated_at: Optional[str] = None


class FundingRoundItem(BaseModel):
    round_name: str
    amount_usd: Optional[float] = None
    round_date: Optional[str] = None
    investors: List[str] = Field(default_factory=list)
    lead_investor: Optional[str] = None


class JobListingItem(BaseModel):
    job_id: Optional[str] = None
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    posted_at: Optional[str] = None
    url: Optional[str] = None
    required_technologies: List[str] = Field(default_factory=list)


class WorkHistoryItem(BaseModel):
    company_name: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None


class CompanyIntelligenceProfile(BaseModel):
    """Full company intelligence bundle."""
    entity_id: str
    name: str
    primary_domain: str
    alternate_domains: List[str] = Field(default_factory=list)
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    github_url: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    headcount: Optional[str] = None
    headcount_timeseries: List[Dict[str, Any]] = Field(default_factory=list)
    headcount_by_department: Dict[str, int] = Field(default_factory=dict)
    annual_revenue_range: Optional[str] = None
    headquarters: Optional[str] = None
    founding_year: Optional[int] = None
    technographics: List[TechnographicItem] = Field(default_factory=list)
    funding_rounds: List[FundingRoundItem] = Field(default_factory=list)
    total_funding_usd: Optional[float] = None
    leadership: List[Dict[str, Any]] = Field(default_factory=list)
    active_jobs: List[JobListingItem] = Field(default_factory=list)
    competitors: List[Dict[str, Any]] = Field(default_factory=list)
    social_posts: List[Dict[str, Any]] = Field(default_factory=list)
    news_articles: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[IntelligenceEvidenceItem] = Field(default_factory=list)
    enrichment_level: EnrichmentLevel = EnrichmentLevel.LEVEL_2_STANDARD
    credits_consumed: float = 0.0
    data_freshness: str = "CACHED"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    is_mock: bool = False
    data_origin: str = "LIVE"  # "LIVE", "CACHED", "DEMO"
    source: str = "Crustdata API v2025-11-01"
    verification_status: str = "VERIFIED"
    buying_intent_status: str = "INTELLIGENCE_ONLY"
    provenance: Dict[str, str] = Field(default_factory=dict)


class PersonIntelligenceProfile(BaseModel):
    """Full person intelligence bundle."""
    entity_id: str
    full_name: str
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    github_url: Optional[str] = None
    verified_work_email: Optional[str] = None
    summary_bio: Optional[str] = None
    is_decision_maker: bool = False
    decision_maker_score: float = 0.0
    work_history: List[WorkHistoryItem] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    social_activity: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[IntelligenceEvidenceItem] = Field(default_factory=list)
    enrichment_level: EnrichmentLevel = EnrichmentLevel.LEVEL_2_STANDARD
    credits_consumed: float = 0.0
    data_freshness: str = "CACHED"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    is_mock: bool = False
    data_origin: str = "LIVE"  # "LIVE", "CACHED", "DEMO"
    source: str = "Crustdata API v2025-11-01"
    verification_status: str = "VERIFIED"
    buying_intent_status: str = "INTELLIGENCE_ONLY"
    provenance: Dict[str, str] = Field(default_factory=dict)


class DeepEnrichmentCostEstimate(BaseModel):
    """Estimate returned before executing Level 3 Deep Enrichment."""
    entity_name: str
    entity_type: EntityType
    target_identifier: str
    estimated_credits: float
    account_credits_available: float
    safety_threshold: float
    can_proceed: bool
    warning_message: Optional[str] = None


class CrustdataBudgetStatus(BaseModel):
    """Application-level spending budget status and metrics."""
    total_budget: float = 1450.0
    used_credits: float = 0.0
    remaining_credits: float = 1450.0
    usage_percentage: float = 0.0
    status: str = "Active"  # "Active", "Near Limit", "Exhausted"
    mock_used_credits: float = 0.0
    account_credits: Optional[CrustdataCreditsInfo] = None
    is_exhausted: bool = False


class BudgetIncreaseRequest(BaseModel):
    """User request to increase the application-level Crustdata budget."""
    amount: float = Field(..., gt=0, description="Additional credits to allocate to application budget")
    reason: Optional[str] = Field(default="User-approved budget increase", description="Rationale for budget increase")
    approved_by: Optional[str] = Field(default="User", description="User or role granting approval")


class BudgetHistoryItem(BaseModel):
    """Audit record for budget allocations and increases."""
    id: str
    action: str
    amount: float
    budget_before: float
    budget_after: float
    used_before: float
    used_after: float
    notes: str
    is_mock: bool
    approved_by: Optional[str] = None
    created_at: datetime
