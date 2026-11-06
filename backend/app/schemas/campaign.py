"""
Pydantic Schemas for Multi-Vendor Campaigns.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CampaignResponse(BaseModel):
    id: str
    name: str
    original_objective: str
    target_vendors: List[str] = Field(default_factory=list)
    alternative_vendors: List[str] = Field(default_factory=list)
    geography: List[str] = Field(default_factory=list)
    company_size: Optional[Dict[str, Optional[int]]] = None
    industry: Optional[str] = None
    pain_points: List[str] = Field(default_factory=list)
    migration_intent: bool = False
    monitoring_mode: str = "ON_DEMAND"
    status: str = "ACTIVE"
    is_active: bool = True
    last_executed_at: Optional[str] = None
    created_at: str
    updated_at: str


class CampaignCreate(BaseModel):
    objective: str = Field(..., description="Natural language search objective")
    name: Optional[str] = Field(None, description="Optional custom campaign name")
    monitoring_mode: str = Field("ON_DEMAND", description="ON_DEMAND or SCHEDULED")


class CampaignListResponse(BaseModel):
    total: int
    campaigns: List[CampaignResponse]
