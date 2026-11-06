"""
Campaigns API Endpoints.
Provides active campaign retrieval, creation, listing, and activation controls.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.campaign_service import CampaignService
from app.schemas.campaign import CampaignResponse, CampaignCreate, CampaignListResponse

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("/active", response_model=Optional[CampaignResponse])
async def get_active_campaign(
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the currently active multi-vendor campaign configuration.
    Returns null if no campaign has been created yet.
    """
    campaign = await CampaignService.get_active_campaign(db)
    if not campaign:
        return None
    return CampaignService.to_response(campaign)


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves paginated list of all competitive campaigns."""
    campaigns, total = await CampaignService.list_campaigns(db, limit=limit, offset=offset)
    return CampaignListResponse(
        total=total,
        campaigns=[CampaignService.to_response(c) for c in campaigns],
    )


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Parses a natural-language search objective, creates a new active campaign,
    and deactivates previous campaigns.
    """
    campaign = await CampaignService.create_or_update_from_objective(
        db=db,
        objective=payload.objective,
        monitoring_mode=payload.monitoring_mode,
        name=payload.name,
    )
    return CampaignService.to_response(campaign)


@router.post("/{campaign_id}/activate", response_model=CampaignResponse)
async def activate_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Switches active status to the designated campaign."""
    try:
        campaign = await CampaignService.activate_campaign(db, campaign_id=campaign_id)
        return CampaignService.to_response(campaign)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
