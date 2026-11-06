"""
Copywriter Agent API Endpoints.
Provides outreach collateral generation, human-in-the-loop approval/rejection workflows,
and strictly gated export operations.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.company import Company
from app.models.signal import Signal
from app.models.dossier import DepositionDossier
from app.models.execution_log import AgentExecutionLog
from app.agents.copywriter.agent import CopywriterAgent
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
        raise HTTPException(status_code=500, detail=f"Copywriter generation failed: {str(e)}")


# 3. GET /api/v1/copywriter/{company_id}
@router.get("/copywriter/{company_id}")
async def get_copywriter_drafts(
    company_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves generated outreach drafts for a given company."""
    dossier_res = await db.execute(
        select(DepositionDossier).where(DepositionDossier.company_id == company_id)
    )
    dossier = dossier_res.scalar_one_or_none()
    if not dossier or not dossier.outreach_drafts:
        comp_res = await db.execute(select(Company).where(Company.id == company_id))
        company = comp_res.scalar_one_or_none()
        if not company:
            raise HTTPException(
                status_code=404, 
                detail="Company not found."
            )
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


# 4. PATCH /api/v1/copywriter/{dossier_id}/approve
@router.patch("/copywriter/{dossier_id}/approve", response_model=ApprovalResponse)
async def approve_outreach_draft(
    dossier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUserContext = Depends(require_roles(["ADMINISTRATOR", "SALES_MANAGER"])),
):
    """Human-in-the-loop approval endpoint. Promotes draft from DRAFT_PENDING_APPROVAL to APPROVED."""
    dossier_res = await db.execute(
        select(DepositionDossier).where(DepositionDossier.id == dossier_id)
    )
    dossier = dossier_res.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")

    dossier.status = "APPROVED"
    
    # Also update embedded package status if present
    if dossier.outreach_drafts and isinstance(dossier.outreach_drafts, dict):
        dossier.outreach_drafts["governance_status"] = "APPROVED"

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
        message="Outreach draft successfully approved. It is now unlocked for export.",
    )


# 5. PATCH /api/v1/copywriter/{dossier_id}/reject
@router.patch("/copywriter/{dossier_id}/reject", response_model=ApprovalResponse)
async def reject_outreach_draft(
    dossier_id: str,
    body: Optional[RejectionRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Rejection endpoint. Marks draft as REJECTED with feedback notes."""
    dossier_res = await db.execute(
        select(DepositionDossier).where(DepositionDossier.id == dossier_id)
    )
    dossier = dossier_res.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")

    reason = body.reason if body else "Content requires revision"
    dossier.status = "REJECTED"
    
    if dossier.outreach_drafts and isinstance(dossier.outreach_drafts, dict):
        dossier.outreach_drafts["governance_status"] = "REJECTED"
        dossier.outreach_drafts["rejection_reason"] = reason

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
    
    # Build complete Markdown bundle for SDR / AE clipboard / sales engagement tooling
    md_sections = [
        f"# Competitive Deposition Pack: {company_name}",
        f"**Target Alternative**: {package.get('target_challenger')} | **Distress Category**: {package.get('distress_category')}",
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
        md_sections.append(f"**Talking Points**:")
        for pt in obj.get("talking_points", []):
            md_sections.append(f"- {pt}")
        md_sections.append(f"**Recommended Response**: {obj.get('recommended_response')}\n")

    bundle_text = "\n\n".join(md_sections)

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
    )
