"""
Copywriter Agent API Endpoints.
Provides outreach collateral generation, human-in-the-loop approval/rejection workflows,
and strictly validated, gated export operations.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.session import get_db
from app.models.company import Company
from app.models.signal import Signal
from app.models.dossier import DepositionDossier
from app.models.workflow import WorkflowExecution
from app.models.execution_log import AgentExecutionLog
from app.agents.copywriter.agent import CopywriterAgent
from app.agents.copywriter.report_validator import ReportValidator
from app.agents.orchestrator.pipeline import PipelineRunner
from app.agents.orchestrator.state_machine import WorkflowState, WorkflowStep
from app.api.deps import require_roles, AuthenticatedUserContext
from app.agents.copywriter.schemas import OutreachPackage

router = APIRouter(tags=["Copywriter Agent"])


class RejectionRequest(BaseModel):
    reason: Optional[str] = Field(default="Content requires revision", description="Reason for rejecting draft")


class ApprovalResponse(BaseModel):
    dossier_id: str
    status: str
    message: str


class ExportResponse(BaseModel):
    dossier_id: str
    company_name: str
    status: str
    exported_at: str
    outreach_package: Dict[str, Any]
    markdown_bundle: str
    validation_report: Optional[Dict[str, Any]] = None


# 1. Static Routes (Declared before parameterized routes to avoid path collision)
@router.get("/copywriter/metrics")
async def get_copywriter_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Returns analytics across all generated outreach collateral and human governance status."""
    dossiers_res = await db.execute(select(DepositionDossier))
    dossiers = dossiers_res.scalars().all()

    total_with_drafts = 0
    pending_approval = 0
    approved = 0
    rejected = 0

    for d in dossiers:
        if d.outreach_drafts:
            total_with_drafts += 1
            if d.status == "APPROVED":
                approved += 1
            elif d.status == "REJECTED":
                rejected += 1
            else:
                pending_approval += 1

    return {
        "total_dossiers_with_drafts": total_with_drafts,
        "pending_human_approval": pending_approval,
        "approved": approved,
        "rejected": rejected,
        "governance_rule": "Outreach collateral remains in DRAFT_PENDING_APPROVAL until explicitly approved by human reviewer.",
    }


# 2. POST /api/v1/copywriter/run/{company_id}
@router.post("/copywriter/run/{company_id}")
async def run_copywriter(
    company_id: str,
    target_challenger: str = Query("SigNoz Cloud", description="SigNoz Cloud or Grafana Cloud"),
    db: AsyncSession = Depends(get_db),
):
    """Generates personalized sales collateral, runs evidence guard audit, and updates dossier."""
    company_res = await db.execute(select(Company).where(Company.id == company_id))
    company = company_res.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        result = await CopywriterAgent.run_and_persist(
            company_id=company_id,
            target_challenger=target_challenger,
            db=db,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate outreach collateral: {str(e)}")


# 3a. GET /api/v1/copywriter/{company_id} (Convenience lookup by company)
@router.get("/copywriter/{company_id}")
async def get_copywriter_drafts_by_company(
    company_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves generated outreach drafts for a given company, auto-generating if needed."""
    dossier_res = await db.execute(
        select(DepositionDossier).where(DepositionDossier.company_id == company_id)
    )
    dossier = dossier_res.scalar_one_or_none()
    if not dossier or not dossier.outreach_drafts:
        comp_res = await db.execute(select(Company).where(Company.id == company_id))
        company = comp_res.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found.")
        try:
            await CopywriterAgent.run_and_persist(
                company_id=company_id,
                target_challenger="SigNoz Cloud",
                db=db,
            )
            dossier_res = await db.execute(
                select(DepositionDossier).where(DepositionDossier.company_id == company_id)
            )
            dossier = dossier_res.scalar_one_or_none()
        except Exception as e:
            raise HTTPException(
                status_code=404, 
                detail=f"No outreach drafts found for this company and auto-generation failed: {str(e)}"
            )

    if not dossier or not dossier.outreach_drafts:
        raise HTTPException(
            status_code=404, 
            detail="No outreach drafts found for this company. Run /copywriter/run first."
        )

    return {
        "dossier_id": dossier.id,
        "company_id": dossier.company_id,
        "status": dossier.status,
        "outreach_package": dossier.outreach_drafts,
    }


# 3b. GET /api/v1/copywriter/{dossier_id}/drafts
@router.get("/copywriter/{dossier_id}/drafts", response_model=Dict[str, Any])
async def get_outreach_drafts(
    dossier_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves generated outreach package for human review."""
    dossier_res = await db.execute(
        select(DepositionDossier).where(DepositionDossier.id == dossier_id)
    )
    dossier = dossier_res.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")

    if not dossier.outreach_drafts:
        raise HTTPException(status_code=404, detail="No outreach drafts found for this dossier.")

    return {
        "dossier_id": dossier.id,
        "status": dossier.status,
        "company_id": dossier.company_id,
        "outreach_package": dossier.outreach_drafts,
    }


# 4. POST /api/v1/copywriter/{dossier_id}/approve
@router.patch("/copywriter/{dossier_id}/approve", response_model=ApprovalResponse)
@router.post("/copywriter/{dossier_id}/approve", response_model=ApprovalResponse)
async def approve_outreach_drafts(
    dossier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUserContext = Depends(require_roles(["ADMINISTRATOR", "SALES_MANAGER"])),
):
    """
    Approves outreach drafts, advancing the dossier to APPROVED state.
    Unblocks export operations.
    """
    dossier_res = await db.execute(
        select(DepositionDossier).where(DepositionDossier.id == dossier_id)
    )
    dossier = dossier_res.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")

    if not dossier.outreach_drafts:
        raise HTTPException(status_code=400, detail="Cannot approve: dossier has no outreach drafts.")

    dossier.status = "APPROVED"
    if isinstance(dossier.outreach_drafts, dict):
        dossier.outreach_drafts["governance_status"] = "APPROVED"
        dossier.outreach_drafts["approved_by"] = "HUMAN_REVIEWER"

    # Synchronize associated WorkflowExecution if present
    wf_res = await db.execute(
        select(WorkflowExecution).where(
            or_(
                WorkflowExecution.dossier_id == dossier.id,
                WorkflowExecution.company_id == dossier.company_id,
            )
        )
    )
    wf = wf_res.scalars().first()
    if wf:
        wf.status = WorkflowState.APPROVED.value
        wf.current_step = WorkflowStep.APPROVAL_GATE.value
        PipelineRunner._record_step(
            workflow=wf,
            step_name=WorkflowStep.APPROVAL_GATE.value,
            status="SUCCESS",
            duration_ms=0,
            details={"approved_by": "HUMAN_REVIEWER", "action": "APPROVAL_GRANTED"},
        )

    log_entry = AgentExecutionLog(
        agent_name="COPYWRITER",
        signal_id=dossier.signal_id,
        status="SUCCESS",
        execution_time_ms=50,
        input_payload={"dossier_id": dossier.id, "company_id": dossier.company_id},
        output_payload={"action": "APPROVE_OUTREACH_DRAFT", "new_status": "APPROVED"},
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(dossier)

    return ApprovalResponse(
        dossier_id=dossier.id,
        status="APPROVED",
        message="Outreach collateral approved. Export unlocked.",
    )


approve_outreach_draft = approve_outreach_drafts


# 5. POST /api/v1/copywriter/{dossier_id}/reject
@router.patch("/copywriter/{dossier_id}/reject", response_model=ApprovalResponse)
@router.post("/copywriter/{dossier_id}/reject", response_model=ApprovalResponse)
async def reject_outreach_drafts(
    dossier_id: str,
    payload: Optional[RejectionRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUserContext = Depends(require_roles(["ADMINISTRATOR", "SALES_MANAGER"])),
):
    """
    Rejects outreach drafts, locking export and logging rejection reason.
    """
    reason = payload.reason if payload else "Content requires revision"
    dossier_res = await db.execute(
        select(DepositionDossier).where(DepositionDossier.id == dossier_id)
    )
    dossier = dossier_res.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")

    dossier.status = "REJECTED"
    
    if dossier.outreach_drafts and isinstance(dossier.outreach_drafts, dict):
        dossier.outreach_drafts["governance_status"] = "REJECTED"
        dossier.outreach_drafts["rejection_reason"] = reason

    # Synchronize associated WorkflowExecution if present
    wf_res = await db.execute(
        select(WorkflowExecution).where(
            or_(
                WorkflowExecution.dossier_id == dossier.id,
                WorkflowExecution.company_id == dossier.company_id,
            )
        )
    )
    wf = wf_res.scalars().first()
    if wf:
        wf.status = WorkflowState.REJECTED.value
        wf.current_step = WorkflowStep.APPROVAL_GATE.value
        wf.error_details = f"Outreach draft rejected by human reviewer: {reason}"
        PipelineRunner._record_step(
            workflow=wf,
            step_name=WorkflowStep.APPROVAL_GATE.value,
            status="REJECTED",
            duration_ms=0,
            details={"rejected_by": "HUMAN_REVIEWER", "reason": reason},
            error_message=reason,
        )

    log_entry = AgentExecutionLog(
        agent_name="COPYWRITER",
        signal_id=dossier.signal_id,
        status="SUCCESS",
        execution_time_ms=50,
        input_payload={"dossier_id": dossier.id, "company_id": dossier.company_id, "reason": reason},
        output_payload={"action": "REJECT_OUTREACH_DRAFT", "new_status": "REJECTED"},
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(dossier)

    return ApprovalResponse(
        dossier_id=dossier.id,
        status="REJECTED",
        message=f"Outreach draft rejected: {reason}",
    )


# 6. POST /api/v1/copywriter/{dossier_id}/export
@router.post("/copywriter/{dossier_id}/export", response_model=ExportResponse)
async def export_outreach_package(
    dossier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUserContext = Depends(require_roles(["ADMINISTRATOR", "SALES_MANAGER"])),
):
    """
    Exports approved collateral package.
    GOVERNANCE ENFORCEMENT: Export is strictly prohibited if dossier status is NOT 'APPROVED'.
    VALIDATION ENFORCEMENT: Automated report validation engine must pass all technical and financial checks.
    """
    dossier_res = await db.execute(
        select(DepositionDossier).where(DepositionDossier.id == dossier_id)
    )
    dossier = dossier_res.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")

    if not dossier.outreach_drafts:
        raise HTTPException(status_code=400, detail="Dossier has no outreach collateral to export.")

    # Strict Human-in-the-Loop Governance Gate
    if dossier.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Export blocked: Dossier status is '{dossier.status}'. "
                "Human approval is strictly required before exporting or sending outreach collateral."
            ),
        )

    package = dossier.outreach_drafts
    company_name = package.get("company_name", "Unknown Company")
    finops_data = dossier.financial_delta or {}
    arch_data = dossier.migration_blueprint or {}
    is_synth = bool(dossier.is_synthetic)

    # Determine Header and Provenance Banner
    is_generic = (
        arch_data.get("is_generic_blueprint", False)
        or company_name in ["Unknown Company", "Generic Organization"]
        or is_synth
    )

    if is_generic and is_synth:
        doc_header = f"# Competitive Deposition Pack & Telemetry Sizing Model: {company_name}"
        provenance_banner = (
            "> **DATA PROVENANCE NOTICE**: `SYNTHETIC DEMO / ILLUSTRATIVE MODEL — NOT VERIFIED CUSTOMER SPEND`\n"
            "> All telemetry volumes, custom metric counts, and spend figures represent mathematical models "
            "derived from public list pricing. No actual customer billing or proprietary infrastructure has been verified."
        )
    elif is_generic:
        doc_header = f"# Generic OpenTelemetry Migration Blueprint & Sizing Model"
        provenance_banner = (
            "> **REFERENCE ARCHITECTURE**: `GENERIC TECHNICAL BLUEPRINT — UNVERIFIED PROSPECT`\n"
            "> Infrastructure complexity and telemetry volume are modeled on industry heuristics."
        )
    else:
        doc_header = f"# Competitive Deposition Pack: {company_name}"
        provenance_banner = (
            "> **DATA PROVENANCE**: `ILLUSTRATIVE MODEL — NOT VERIFIED CUSTOMER SPEND`\n"
            "> Projections reflect public list pricing benchmarks. Actual enterprise spend requires signed NDA invoice audit."
        )

    # Build comprehensive, audited Markdown bundle
    md_sections = [
        doc_header,
        provenance_banner,
        f"\n**Target Alternative**: {package.get('target_challenger')} | **Distress Category**: {package.get('distress_category')}",
        "\n---\n## 1. Executive Emails",
    ]

    for idx, email in enumerate(package.get("executive_emails", []), start=1):
        md_sections.append(f"### Variant {idx}: {email.get('target_role')}")
        md_sections.append("**Subject Options**:")
        for subj in email.get("subject_lines", []):
            md_sections.append(f"- {subj}")
        md_sections.append(f"**Preheader**: {email.get('preheader')}")
        md_sections.append(f"\n{email.get('body_markdown')}\n")

    md_sections.append("\n---\n## 2. LinkedIn Multi-Touch Sequence")
    li = package.get("linkedin_sequence", {})
    md_sections.append(f"**Touch 1 (Connection Request < 300 chars)**:\n{li.get('step_1_connection_request')}\n")
    md_sections.append(f"**Touch 2 (Value Add)**:\n{li.get('step_2_value_add')}\n")
    md_sections.append(f"**Touch 3 (Technical Follow-Up)**:\n{li.get('step_3_technical_commercial')}\n")

    md_sections.append("\n---\n## 3. Technical Migration Brief")
    tp = package.get("technical_pitch", {})
    md_sections.append(tp.get("full_pitch_markdown", ""))

    md_sections.append("\n---\n## 4. Value Proposition & Business Case")
    vp = package.get("value_proposition", {})
    md_sections.append(vp.get("full_value_prop_markdown", ""))

    md_sections.append("\n---\n## 5. Enterprise Objection Matrix")
    for obj in package.get("objection_matrix", {}).get("items", []):
        md_sections.append(f"### Objection: {obj.get('objection')}")
        md_sections.append("**Talking Points**:")
        for pt in obj.get("talking_points", []):
            md_sections.append(f"- {pt}")
        md_sections.append(f"**Recommended Response**: {obj.get('recommended_response')}\n")

    # Section 6: Validated OpenTelemetry Collector Configuration YAML
    collector_yaml = arch_data.get("collector_config_yaml", "")
    if collector_yaml:
        md_sections.append("\n---\n## 6. Validated OpenTelemetry Collector Configuration (YAML)")
        md_sections.append(
            "```yaml\n"
            f"{collector_yaml.strip()}\n"
            "```\n"
        )

    # Section 7: 12-Component Scoped Labor Breakdown
    effort_est = arch_data.get("effort_estimate", {})
    effort_items = effort_est.get("items", [])
    if effort_items:
        md_sections.append("\n---\n## 7. Granular 12-Component Migration Effort Breakdown")
        md_sections.append(f"*{effort_est.get('estimate_status', 'PRELIMINARY ESTIMATE')}*")
        md_sections.append(f"{effort_est.get('methodology_note', '')}\n")
        md_sections.append("| Component | Low (Hours) | Base (Hours) | High (Hours) | Key Assumptions |")
        md_sections.append("|---|---|---|---|---|")
        for it in effort_items:
            md_sections.append(f"| {it.get('category')} | {it.get('low_hours')}h | {it.get('base_hours')}h | {it.get('high_hours')}h | {it.get('assumptions')} |")
        md_sections.append(
            f"| **TOTAL SCOPED HOURS** | **{effort_est.get('total_low_hours', 120)}h** | "
            f"**{effort_est.get('total_base_hours', 240)}h** | **{effort_est.get('total_high_hours', 480)}h** | "
            f"Blended rate: ${effort_est.get('hourly_rate_usd', 125.0):.0f}/hr |\n"
        )

    # Section 8: Dual-Shipping Operational Risk & Parity Analysis
    ds_risks = arch_data.get("dual_shipping_risks", {})
    if ds_risks:
        md_sections.append("\n---\n## 8. Dual-Shipping Operational Risk & Parity Governance")
        md_sections.append(f"- **Temporary Ingestion Overlap**: {ds_risks.get('temporary_ingestion_cost_summary', '')}")
        md_sections.append(f"- **Duplicate Telemetry Overhead**: {ds_risks.get('duplicate_telemetry_overhead', '')}")
        md_sections.append(f"- **Sampling & Retention Differences**: {ds_risks.get('sampling_and_retention_differences', '')}")
        md_sections.append(f"- **Cardinality & Schema Differences**: {ds_risks.get('cardinality_and_schema_differences', '')}")
        md_sections.append(f"- **Collector Resource Consumption**: {ds_risks.get('collector_resource_consumption', '')}")
        md_sections.append(f"- **Network Egress Impact**: {ds_risks.get('network_egress_impact', '')}")
        md_sections.append(f"- **Failure Isolation Architecture**: {ds_risks.get('failure_isolation_design', '')}")
        md_sections.append(f"- **Rollback Limitations**: {ds_risks.get('rollback_limitations', '')}\n")

    bundle_text = "\n\n".join(md_sections)

    # Automated Pre-Export Report Validation Gate
    validation = ReportValidator.validate_report(
        bundle_markdown=bundle_text,
        package=package,
        finops_data=finops_data,
        arch_data=arch_data,
        is_synthetic=is_synth,
    )

    if not validation.passed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Report export blocked: Automated pre-export validation failed.",
                "critical_errors": validation.critical_errors,
                "warnings": validation.warnings,
            },
        )

    # Synchronize associated WorkflowExecution to COMPLETED upon authorized export
    wf_res = await db.execute(
        select(WorkflowExecution).where(
            or_(
                WorkflowExecution.dossier_id == dossier.id,
                WorkflowExecution.company_id == dossier.company_id,
            )
        )
    )
    wf = wf_res.scalars().first()
    if wf:
        wf.status = WorkflowState.COMPLETED.value
        wf.current_step = WorkflowStep.FINALIZED.value
        PipelineRunner._record_step(
            workflow=wf,
            step_name=WorkflowStep.FINALIZED.value,
            status="COMPLETED",
            duration_ms=0,
            details={"action": "EXPORT_OUTREACH_PACKAGE", "bundle_size_chars": len(bundle_text)},
        )

    log_entry = AgentExecutionLog(
        agent_name="COPYWRITER",
        signal_id=dossier.signal_id,
        status="SUCCESS",
        execution_time_ms=60,
        input_payload={"dossier_id": dossier.id, "company_name": company_name},
        output_payload={"action": "EXPORT_OUTREACH_PACKAGE", "status": "EXPORTED"},
    )
    db.add(log_entry)
    await db.commit()

    from datetime import datetime, timezone
    return ExportResponse(
        dossier_id=dossier.id,
        company_name=company_name,
        status="EXPORTED",
        exported_at=datetime.now(timezone.utc).isoformat(),
        outreach_package=package,
        markdown_bundle=bundle_text,
        validation_report=validation.model_dump(),
    )
