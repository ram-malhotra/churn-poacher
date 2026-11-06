"""
Campaign Service Layer.
Manages multi-vendor campaign creation, activation, persistence, and state transitions.
"""

from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, func

from app.models.campaign import Campaign
from app.schemas.campaign import CampaignResponse
from app.services.objective.objective_interpreter import ObjectiveInterpreter


class CampaignService:
    """Manages active and historical competitor deposition campaigns."""

    @classmethod
    def to_response(cls, campaign: Campaign) -> CampaignResponse:
        """Serializes SQLAlchemy Campaign model into CampaignResponse schema."""
        return CampaignResponse(
            id=campaign.id,
            name=campaign.name,
            original_objective=campaign.original_objective,
            target_vendors=campaign.target_vendors or [],
            alternative_vendors=campaign.alternative_vendors or [],
            geography=campaign.geography or [],
            company_size=campaign.company_size,
            industry=campaign.industry,
            pain_points=campaign.pain_points or [],
            migration_intent=campaign.migration_intent,
            monitoring_mode=campaign.monitoring_mode or "ON_DEMAND",
            status=campaign.status or "ACTIVE",
            is_active=campaign.is_active,
            last_executed_at=campaign.last_executed_at.isoformat() if campaign.last_executed_at else None,
            created_at=campaign.created_at.isoformat() if campaign.created_at else "",
            updated_at=campaign.updated_at.isoformat() if campaign.updated_at else "",
        )

    @classmethod
    async def create_or_update_from_objective(
        cls,
        db: AsyncSession,
        objective: str,
        monitoring_mode: str = "ON_DEMAND",
        name: Optional[str] = None,
    ) -> Campaign:
        """
        Parses objective, deactivates other campaigns, creates a new active campaign, and persists to DB.
        """
        criteria = ObjectiveInterpreter.interpret(objective)
        campaign_name = name or criteria.campaign_name

        # Mark all existing campaigns as inactive
        await db.execute(update(Campaign).values(is_active=False))

        # Build company size dict
        company_size_dict = None
        if criteria.target_company_size:
            company_size_dict = {
                "min": criteria.target_company_size.min,
                "max": criteria.target_company_size.max,
            }

        # Create new active campaign
        campaign = Campaign(
            name=campaign_name,
            original_objective=objective,
            target_vendors=criteria.target_vendors,
            alternative_vendors=criteria.alternative_technologies,
            geography=criteria.target_geography,
            company_size=company_size_dict,
            industry=criteria.target_industry,
            pain_points=criteria.pain_points,
            migration_intent=criteria.migration_intent,
            monitoring_mode=monitoring_mode,
            status="ACTIVE",
            is_active=True,
            last_executed_at=datetime.now(timezone.utc),
            metadata_payload={
                "search_queries": criteria.search_queries,
                "priority_signals": criteria.priority_signals,
                "filter_summary": criteria.filter_summary,
            },
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        return campaign

    @classmethod
    async def get_active_campaign(cls, db: AsyncSession) -> Optional[Campaign]:
        """Returns the currently active campaign, or latest created if none explicitly flagged active."""
        res = await db.execute(
            select(Campaign).where(Campaign.is_active == True).order_by(desc(Campaign.updated_at))
        )
        active = res.scalar_one_or_none()
        if active:
            return active

        # Fallback to latest campaign
        latest_res = await db.execute(
            select(Campaign).order_by(desc(Campaign.created_at)).limit(1)
        )
        return latest_res.scalar_one_or_none()

    @classmethod
    async def list_campaigns(
        cls,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Campaign], int]:
        """Returns paginated list of all campaigns."""
        count_res = await db.execute(select(func.count(Campaign.id)))
        total = count_res.scalar() or 0

        query = select(Campaign).order_by(desc(Campaign.created_at)).offset(offset).limit(limit)
        res = await db.execute(query)
        campaigns = res.scalars().all()
        return list(campaigns), total

    @classmethod
    async def activate_campaign(cls, db: AsyncSession, campaign_id: str) -> Campaign:
        """Sets the specified campaign as active and deactivates others."""
        res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        target_camp = res.scalar_one_or_none()
        if not target_camp:
            raise ValueError(f"Campaign with ID '{campaign_id}' not found.")

        await db.execute(update(Campaign).values(is_active=False))
        target_camp.is_active = True
        target_camp.status = "ACTIVE"
        await db.commit()
        await db.refresh(target_camp)
        return target_camp
