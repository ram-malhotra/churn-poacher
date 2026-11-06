"""
Listener Agent API Endpoints.
Provides manual execution triggers, status monitoring, and ingestion metrics.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.listener_service import listener_service
from app.agents.listener.schemas import (
    IngestionSummary,
    ListenerStatusReport,
    ListenerMetricsReport,
    SourceExecutionSummary,
)

router = APIRouter(prefix="/listener", tags=["Listener Agent"])


class RunListenerRequest(BaseModel):
    include_synthetic: Optional[bool] = None
    max_items_per_source: int = 10
    queries: Optional[List[str]] = None


@router.post("/run", response_model=IngestionSummary)
async def trigger_listener_run(
    request: Optional[RunListenerRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Triggers a single ingestion cycle across all active adapters."""
    include_synth = request.include_synthetic if request else None
    max_items = request.max_items_per_source if request else 10
    queries = request.queries if request else None
    
    summary = await listener_service.run_cycle(
        db=db,
        include_synthetic=include_synth,
        max_items_per_source=max_items,
        queries=queries,
    )
    return summary


@router.get("/status", response_model=ListenerStatusReport)
async def get_listener_status(
    db: AsyncSession = Depends(get_db),
):
    """Returns the adapter readiness and execution state of the Listener Agent."""
    return await listener_service.get_status(db)


@router.get("/sources", response_model=List[SourceExecutionSummary])
async def get_listener_sources(
    db: AsyncSession = Depends(get_db),
):
    """Returns the operational status of all public listener sources."""
    status_report = await listener_service.get_status(db)
    return status_report.sources


@router.get("/metrics", response_model=ListenerMetricsReport)
async def get_listener_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Returns quantitative ingestion metrics (real vs. synthetic, categories, duplicates)."""
    return await listener_service.get_metrics(db)
