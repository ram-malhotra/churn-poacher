"""
FinOps and Architecture Agent API Endpoints.
Provides financial modeling, OpenTelemetry migration blueprint generation,
pricing catalog inspection, and Deposition Dossier persistence.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.session import get_db
from app.models.company import Company
from app.models.signal import Signal
from app.models.dossier import DepositionDossier
from app.models.execution_log import AgentExecutionLog
from app.schemas.dossier import DossierRead
from app.agents.finops_architect.pricing_sources import PricingCatalog
from app.agents.finops_architect.finops_agent import FinOpsAgent
from app.agents.finops_architect.architecture_agent import ArchitectureAgent
from app.agents.finops_architect.financial_models import (
    FinancialDeltaReport,
    PricingEntry,
)
from app.agents.finops_architect.architecture_models import (
    ArchitectureMigrationBlueprint,
)

router = APIRouter(tags=["FinOps & Architecture Agent"])


# 1. Static Routes (Must be declared before parameterized {company_id} routes)
@router.get("/finops/pricing", response_model=List[PricingEntry])
async def get_pricing_catalog():
    """Returns official verified public unit prices, sources, and verification dates."""
    return PricingCatalog.get_all_entries()


@router.get("/finops/metrics")
async def get_finops_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Returns analytics and financial execution statistics across all generated dossiers."""
    dossiers_res = await db.execute(select(DepositionDossier))
    dossiers = dossiers_res.scalars().all()

    total_dossiers = len(dossiers)
    total_savings = 0.0
    avg_payback_months = 0.0
    payback_count = 0

    for d in dossiers:
        delta = d.financial_delta or {}
        savings = float(delta.get("estimated_annual_savings", 0.0))
        payback = float(delta.get("payback_period_months", 0.0))
        total_savings += savings
        if payback > 0:
            avg_payback_months += payback
            payback_count += 1

    return {
        "dossiers_generated": total_dossiers,
        "total_potential_annual_savings_usd": round(total_savings, 2),
        "average_payback_period_months": round(avg_payback_months / payback_count, 1) if payback_count > 0 else 0.0,
        "platforms_supported": [
            "Datadog",
            "SigNoz Cloud",
            "SigNoz Self-Hosted",
            "Grafana Cloud",
            "Grafana OSS",
        ],
    }


# 2. POST /api/v1/finops/run/{company_id}
@router.post("/finops/run/{company_id}", response_model=FinancialDeltaReport)
async def run_finops_analysis(
    company_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generates the Financial Delta Matrix for a verified company."""
    company_res = await db.execute(select(Company).where(Company.id == company_id))
    company = company_res.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    signal_res = await db.execute(select(Signal).where(Signal.id == company.signal_id))
    signal = signal_res.scalar_one_or_none()

    report = await FinOpsAgent.generate_financial_analysis(company, signal)
    return report


# 3. POST /api/v1/architecture/run/{company_id}
@router.post("/architecture/run/{company_id}", response_model=ArchitectureMigrationBlueprint)
async def run_architecture_blueprint(
    company_id: str,
    target_backend: str = Query("SigNoz Cloud", description="SigNoz Cloud or Grafana Cloud"),
    db: AsyncSession = Depends(get_db),
):
    """Generates an OpenTelemetry Collector migration blueprint and rollout plan."""
    company_res = await db.execute(select(Company).where(Company.id == company_id))
    company = company_res.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    blueprint = await ArchitectureAgent.generate_migration_blueprint(company, target_backend)
    return blueprint


# 4. POST /api/v1/finops/dossier/{company_id}
@router.post("/finops/dossier/{company_id}", response_model=DossierRead)
async def generate_and_persist_dossier(
    company_id: str,
    target_backend: str = Query("SigNoz Cloud"),
    db: AsyncSession = Depends(get_db),
):
    """Combines FinOps modeling and Architecture migration blueprints into a DepositionDossier."""
    company_res = await db.execute(select(Company).where(Company.id == company_id))
    company = company_res.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    signal_res = await db.execute(select(Signal).where(Signal.id == company.signal_id))
    signal = signal_res.scalar_one_or_none()

    # Generate Part A: FinOps Analysis
    fin_report = await FinOpsAgent.generate_financial_analysis(company, signal)
    
    # Generate Part B: Architecture Blueprint
    arch_blueprint = await ArchitectureAgent.generate_migration_blueprint(company, target_backend)

    # Base financial savings payload for quick summary
    base_scenario = fin_report.scenarios.get("BASE")
    delta_dict = {
        "datadog_monthly": base_scenario.current_datadog_monthly if base_scenario else 0.0,
        "datadog_annual": base_scenario.current_datadog_annual if base_scenario else 0.0,
        "signoz_monthly": base_scenario.signoz_cloud_monthly if base_scenario else 0.0,
        "signoz_annual": base_scenario.signoz_cloud_annual if base_scenario else 0.0,
        "estimated_annual_savings": base_scenario.signoz_cloud_annual_savings if base_scenario else 0.0,
        "payback_period_months": base_scenario.payback_period_months if base_scenario else 0.0,
        "report": fin_report.model_dump(mode="json"),
    }

    blueprint_dict = arch_blueprint.model_dump(mode="json")

    # Persist or update existing dossier
    existing_dossier = await db.execute(
        select(DepositionDossier).where(DepositionDossier.company_id == company_id)
    )
    dossier = existing_dossier.scalar_one_or_none()

    if dossier:
        dossier.financial_delta = delta_dict
        dossier.migration_blueprint = blueprint_dict
        dossier.status = "DRAFT_PENDING_APPROVAL"
    else:
        dossier = DepositionDossier(
            company_id=company.id,
            signal_id=company.signal_id,
            financial_delta=delta_dict,
            migration_blueprint=blueprint_dict,
            outreach_drafts={},
            status="DRAFT_PENDING_APPROVAL",
            is_synthetic=company.is_synthetic,
        )
        db.add(dossier)

    # Record Execution Log
    log_entry = AgentExecutionLog(
        agent_name="FINOPS_ARCHITECT",
        signal_id=company.signal_id,
        status="SUCCESS",
        execution_time_ms=150,
        input_payload={"company_id": company.id, "target_backend": target_backend},
        output_payload={"dossier_status": "DRAFT_PENDING_APPROVAL", "annual_savings": delta_dict["estimated_annual_savings"]},
    )
    db.add(log_entry)

    await db.commit()
    await db.refresh(dossier)
    return dossier


# 5. Parameterized {company_id} Routes
@router.get("/finops/{company_id}", response_model=FinancialDeltaReport)
async def get_financial_analysis(
    company_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves existing or generates financial analysis for a company."""
    company_res = await db.execute(select(Company).where(Company.id == company_id))
    company = company_res.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # If persisted in dossier, reuse for consistency
    dossier_res = await db.execute(
        select(DepositionDossier).where(DepositionDossier.company_id == company_id)
    )
    dossier = dossier_res.scalar_one_or_none()
    if dossier and dossier.financial_delta and "report" in dossier.financial_delta:
        return FinancialDeltaReport(**dossier.financial_delta["report"])

    signal_res = await db.execute(select(Signal).where(Signal.id == company.signal_id))
    signal = signal_res.scalar_one_or_none()
    return await FinOpsAgent.generate_financial_analysis(company, signal)


@router.get("/architecture/{company_id}", response_model=ArchitectureMigrationBlueprint)
async def get_architecture_blueprint(
    company_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves existing or generates migration blueprint for a company."""
    company_res = await db.execute(select(Company).where(Company.id == company_id))
    company = company_res.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # If persisted in dossier, return the persisted blueprint for consistency
    dossier_res = await db.execute(
        select(DepositionDossier).where(DepositionDossier.company_id == company_id)
    )
    dossier = dossier_res.scalar_one_or_none()
    if dossier and dossier.migration_blueprint:
        return ArchitectureMigrationBlueprint(**dossier.migration_blueprint)

    return await ArchitectureAgent.generate_migration_blueprint(company)
