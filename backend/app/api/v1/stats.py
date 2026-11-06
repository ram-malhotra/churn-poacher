"""
API Endpoints for Dashboard Overview Statistics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.session import get_db
from app.models.signal import Signal
from app.models.company import Company
from app.models.dossier import DepositionDossier
from app.models.workflow import WorkflowExecution
from app.schemas.stats import DashboardStats

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/overview", response_model=DashboardStats)
async def get_overview_stats(db: AsyncSession = Depends(get_db)):
    # 1. Total Signals
    signals_count_res = await db.execute(select(func.count(Signal.id)))
    signals_count = signals_count_res.scalar() or 0

    # 2. Total Companies
    companies_count_res = await db.execute(select(func.count(Company.id)))
    companies_count = companies_count_res.scalar() or 0

    # 3. Qualified Prospects (ICP Score >= 0.7)
    qualified_count_res = await db.execute(
        select(func.count(Company.id)).where(Company.icp_score >= 0.7)
    )
    qualified_count = qualified_count_res.scalar() or 0

    # 4. Total Dossiers
    dossiers_count_res = await db.execute(select(func.count(DepositionDossier.id)))
    dossiers_count = dossiers_count_res.scalar() or 0

    # 5. Total Potential Annual Savings across dossiers
    dossiers_res = await db.execute(select(DepositionDossier.financial_delta))
    dossier_deltas = dossiers_res.scalars().all()
    
    total_savings = 0.0
    for delta in dossier_deltas:
        if isinstance(delta, dict):
            total_savings += float(delta.get("estimated_annual_savings", 0.0))

    # 6. Dynamically resolve agent statuses
    active_wf_res = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.status.in_([
                "PENDING",
                "LISTENER_RUNNING",
                "PROFILER_RUNNING",
                "QUALIFICATION_REVIEW",
                "FINOPS_RUNNING",
                "ARCHITECT_RUNNING",
                "COPYWRITER_RUNNING",
            ])
        ).order_by(desc(WorkflowExecution.created_at)).limit(1)
    )
    active_wf = active_wf_res.scalar_one_or_none()

    agent_status = {
        "listener": "ready",
        "profiler": "ready",
        "finops_architect": "ready",
        "copywriter": "ready",
        "orchestrator": "ready",
    }

    if active_wf:
        step = (active_wf.current_step or "").upper()
        agent_status["orchestrator"] = "running"
        if "LISTENER" in step:
            agent_status["listener"] = "running"
        elif "PROFILER" in step or "QUALIFICATION" in step:
            agent_status["profiler"] = "running"
        elif "FINOPS" in step or "ARCHITECT" in step:
            agent_status["finops_architect"] = "running"
        elif "COPYWRITER" in step:
            agent_status["copywriter"] = "running"

    return DashboardStats(
        signals_detected=signals_count,
        companies_identified=companies_count,
        qualified_prospects=qualified_count,
        dossiers_count=dossiers_count,
        total_potential_annual_savings=total_savings,
        agent_status=agent_status,
    )
