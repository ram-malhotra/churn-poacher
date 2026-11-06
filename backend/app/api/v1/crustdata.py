"""
Crustdata Intelligence Extraction API Endpoints.
Provides REST routes for Level 1 Search, Level 2 Standard Enrichment, Level 3 Deep Enrichment,
Credit Inspection, Application Budget Management, Search History, and Intelligence Report Exports.
"""

from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.logging import logger
from app.db.session import get_db
from app.models.intelligence import (
    IntelligenceEntity,
    IntelligenceSearch,
    IntelligenceEvidence,
    CrustdataBudgetHistory,
)
from app.services.crustdata.intelligence_service import CrustdataIntelligenceService
from app.services.crustdata.query_interpreter import CrustdataQueryInterpreter
from app.services.crustdata.credit_guard import CreditGuard
from app.services.crustdata.exceptions import (
    CrustdataError,
    CrustdataCreditDepletedError,
    CrustdataBudgetExhaustedError,
    CrustdataAuthError,
    CrustdataRateLimitError,
)
from app.services.crustdata.schemas import (
    EntityType,
    EnrichmentLevel,
    EntitySearchRequest,
    EntitySearchResponse,
    CrustdataCreditsInfo,
    CrustdataBudgetStatus,
    BudgetIncreaseRequest,
    BudgetHistoryItem,
    CompanyIntelligenceProfile,
    PersonIntelligenceProfile,
    DeepEnrichmentCostEstimate,
)


router = APIRouter(prefix="/crustdata", tags=["Crustdata Intelligence"])
intelligence_service = CrustdataIntelligenceService()


class EntityEnrichmentRequest(BaseModel):
    identifier: str = Field(..., description="Company domain/name or Person profile URL/name")
    entity_type: EntityType = Field(..., description="COMPANY or PERSON")
    level: EnrichmentLevel = Field(default=EnrichmentLevel.LEVEL_2_STANDARD)
    force_refresh: bool = Field(default=False, description="Bypass local 7-day cache")
    confirmation_confirmed: bool = Field(default=False, description="User confirmation for Level 3 Deep Enrichment")
    mode: str = Field(default="LIVE", description="LIVE (Crustdata API v2) or DEMO (Isolated mock)")


class InterpretQueryRequest(BaseModel):
    query: str


class ExportIntelligenceRequest(BaseModel):
    entity_id: str
    export_format: str = Field(default="markdown", pattern="^(markdown|json)$")


@router.get("/credits", response_model=CrustdataCreditsInfo)
async def get_credits():
    """
    Returns active Crustdata account credit balances, renewal schedule, and enabled endpoints.
    Free endpoint (consumes 0 credits).
    """
    try:
        return await intelligence_service.client.get_account_credits()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Crustdata credit status: {str(e)}",
        )


@router.get("/budget", response_model=CrustdataBudgetStatus)
async def get_budget_status(db: AsyncSession = Depends(get_db)):
    """
    Returns application-level Crustdata spending budget, tracked cumulative usage,
    remaining budget, usage percentage, and status (Active / Near Limit / Exhausted).
    """
    account_credits = None
    try:
        account_credits = await intelligence_service.client.get_account_credits()
    except Exception as e:
        logger.warning(f"Could not refresh live account credits for budget status: {e}")

    return await CreditGuard.get_budget_status_async(db=db, credits_info=account_credits)


@router.post("/budget/increase", response_model=CrustdataBudgetStatus)
async def increase_budget(
    request: BudgetIncreaseRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Increases the application-level Crustdata spending budget upon explicit user approval.
    Records the budget increase event in the audit history.
    """
    if request.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Budget increase amount must be strictly positive.",
        )

    try:
        return await CreditGuard.increase_budget_async(
            amount=request.amount,
            reason=request.reason or "User-approved budget increase",
            approved_by=request.approved_by or "User",
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to increase budget: {str(e)}",
        )


@router.get("/budget/history", response_model=List[BudgetHistoryItem])
async def get_budget_history(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the audit trail of all budget increases and credit usage transactions.
    """
    stmt = (
        select(CrustdataBudgetHistory)
        .order_by(desc(CrustdataBudgetHistory.created_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()
    return [
        BudgetHistoryItem(
            id=r.id,
            action=r.action,
            amount=r.amount,
            budget_before=r.budget_before,
            budget_after=r.budget_after,
            used_before=r.used_before,
            used_after=r.used_after,
            notes=r.notes,
            is_mock=r.is_mock,
            approved_by=r.approved_by,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.post("/interpret-query")
async def interpret_query(request: InterpretQueryRequest):
    """
    Interprets natural language discovery query into target entity, filters, and intent explanation.
    """
    return CrustdataQueryInterpreter.interpret(request.query)


@router.post("/search", response_model=EntitySearchResponse)
async def search_entities(
    request: EntitySearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    LEVEL 1 — SEARCH
    Identifies candidate matches for companies or people without high credit consumption.
    Detects ambiguity and never automatically enriches multiple matches.
    """
    try:
        return await intelligence_service.search_candidates(
            db=db,
            query=request.query,
            entity_type=request.entity_type,
            limit=request.limit,
            mode=request.mode,
        )
    except CrustdataBudgetExhaustedError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error_type": "BUDGET_EXHAUSTED",
                "message": str(e),
                "budget": e.budget,
                "used": e.used,
                "remaining": e.remaining,
                "required_credits": e.required_credits,
            },
        )
    except CrustdataCreditDepletedError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))
    except CrustdataRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/enrich",
    response_model=Union[CompanyIntelligenceProfile, PersonIntelligenceProfile, DeepEnrichmentCostEstimate],
)
async def enrich_entity(
    request: EntityEnrichmentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    LEVEL 2 — STANDARD ENRICHMENT & LEVEL 3 — DEEP ENRICHMENT
    Retrieves full structured profile.
    If Level 3 is requested without confirmation_confirmed=True, returns DeepEnrichmentCostEstimate.
    """
    try:
        return await intelligence_service.enrich_entity(
            db=db,
            identifier=request.identifier,
            entity_type=request.entity_type,
            level=request.level,
            force_refresh=request.force_refresh,
            confirmation_confirmed=request.confirmation_confirmed,
            mode=request.mode,
        )
    except CrustdataBudgetExhaustedError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error_type": "BUDGET_EXHAUSTED",
                "message": str(e),
                "budget": e.budget,
                "used": e.used,
                "remaining": e.remaining,
                "required_credits": e.required_credits,
            },
        )
    except CrustdataCreditDepletedError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))
    except CrustdataRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/entities/{entity_id}")
async def get_entity_profile(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns stored intelligence profile snapshot and granular evidence provenance.
    """
    stmt = select(IntelligenceEntity).where(IntelligenceEntity.id == entity_id)
    res = await db.execute(stmt)
    entity = res.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Entity {entity_id} not found.")

    ev_stmt = select(IntelligenceEvidence).where(IntelligenceEvidence.entity_id == entity_id)
    ev_res = await db.execute(ev_stmt)
    evidence_items = ev_res.scalars().all()

    return {
        "entity_id": entity.id,
        "entity_type": entity.entity_type,
        "primary_name": entity.primary_name,
        "primary_domain": entity.primary_domain,
        "profile_url": entity.profile_url,
        "raw_profile": entity.raw_profile,
        "data_freshness": entity.data_freshness,
        "enrichment_level": entity.enrichment_level,
        "credits_consumed": entity.credits_consumed,
        "last_enriched_at": entity.last_enriched_at.isoformat() if entity.last_enriched_at else None,
        "is_mock": entity.is_mock,
        "evidence": [
            {
                "data_category": ev.data_category,
                "claim": ev.claim,
                "source_url": ev.source_url,
                "retrieval_timestamp": ev.retrieval_timestamp.isoformat() if ev.retrieval_timestamp else None,
                "confidence": ev.confidence,
                "verification_classification": ev.verification_classification,
                "metadata": ev.original_source_metadata,
            }
            for ev in evidence_items
        ],
    }


@router.get("/searches/history")
async def get_search_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns search history audit records.
    """
    stmt = select(IntelligenceSearch).order_by(desc(IntelligenceSearch.created_at)).limit(limit)
    res = await db.execute(stmt)
    searches = res.scalars().all()
    return [
        {
            "id": s.id,
            "search_query": s.search_query,
            "entity_type": s.entity_type,
            "search_status": s.search_status,
            "selected_entity_id": s.selected_entity_id,
            "candidates_count": len(s.candidates) if s.candidates else 0,
            "credits_consumed": s.credits_consumed,
            "is_mock": s.is_mock,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in searches
    ]


@router.post("/export")
async def export_intelligence_report(
    request: ExportIntelligenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a structured intelligence report in Markdown or JSON format.
    """
    stmt = select(IntelligenceEntity).where(IntelligenceEntity.id == request.entity_id)
    res = await db.execute(stmt)
    entity = res.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Entity {request.entity_id} not found.")

    ev_stmt = select(IntelligenceEvidence).where(IntelligenceEvidence.entity_id == entity.id)
    ev_res = await db.execute(ev_stmt)
    evidence_items = ev_res.scalars().all()

    profile = entity.raw_profile or {}

    if request.export_format == "json":
        return {
            "entity_id": entity.id,
            "entity_type": entity.entity_type,
            "primary_name": entity.primary_name,
            "profile": profile,
            "evidence": [
                {
                    "category": e.data_category,
                    "claim": e.claim,
                    "classification": e.verification_classification,
                    "confidence": e.confidence,
                    "source_url": e.source_url,
                }
                for e in evidence_items
            ],
            "exported_at": entity.last_enriched_at.isoformat() if entity.last_enriched_at else None,
        }

    # Format Markdown
    title = entity.primary_name
    lines = [
        f"# Crustdata Intelligence Report: {title}",
        f"**Entity Type:** {entity.entity_type} | **Freshness:** {entity.data_freshness} | **Enrichment Level:** {entity.enrichment_level}",
        f"**Primary Domain / Handle:** {entity.primary_domain or entity.profile_url or 'N/A'}",
        f"**Report Generated:** {entity.last_enriched_at}",
        "",
        "## Executive Summary",
        f"{profile.get('description') or profile.get('headline') or profile.get('summary_bio') or 'No summary available.'}",
        "",
    ]

    if entity.entity_type == "COMPANY":
        lines.extend([
            "## Firmographics",
            f"- **Headquarters:** {profile.get('headquarters', 'N/A')}",
            f"- **Headcount:** {profile.get('headcount', 'N/A')}",
            f"- **Industry:** {profile.get('industry', 'N/A')}",
            f"- **Revenue Band:** {profile.get('annual_revenue_range', 'N/A')}",
            "",
            "## Technographics",
        ])
        technos = profile.get("technographics", [])
        if technos:
            for t in technos:
                lines.append(f"- **{t.get('name')}** ({t.get('category')}): `{t.get('classification', 'VERIFIED')}`")
        else:
            lines.append("- *No verified technographics on record.*")

        lines.extend(["", "## Funding & Investors"])
        funds = profile.get("funding_rounds", [])
        if funds:
            for f in funds:
                lines.append(f"- **{f.get('round_name')}**: ${f.get('amount_usd', 0):,.2f} ({f.get('round_date', 'N/A')}) — Investors: {', '.join(f.get('investors', []))}")
        else:
            lines.append("- *No public funding rounds recorded.*")

    else:
        lines.extend([
            "## Professional Overview",
            f"- **Current Role:** {profile.get('current_title', 'N/A')} at {profile.get('current_company', 'N/A')}",
            f"- **Location:** {profile.get('location', 'N/A')}",
            f"- **Decision Maker Score:** {profile.get('decision_maker_score', 'N/A')}",
            "",
            "## Employment History",
        ])
        history = profile.get("work_history", [])
        for h in history:
            lines.append(f"- **{h.get('title')}** at {h.get('company_name')} ({h.get('start_date', 'N/A')} - {h.get('end_date') or 'Present'})")

    lines.extend([
        "",
        "## Evidence & Provenance Audit",
        "| Category | Claim | Classification | Confidence | Source |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])
    for e in evidence_items:
        lines.append(f"| {e.data_category} | {e.claim} | `{e.verification_classification}` | {e.confidence:.2f} | {e.source_url or 'Crustdata API'} |")

    return {
        "entity_id": entity.id,
        "format": "markdown",
        "content": "\n".join(lines),
    }
