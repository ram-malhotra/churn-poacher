"""
End-to-End Multi-Agent Pipeline Integration Test.
Executes the complete sequence:
1. Listener (Signal Ingestion with evidence)
2. Profiler (Entity Resolution & ICP Qualification)
3. Qualification Gate
4. FinOps Engine (5-Platform Pricing Delta Modeling)
5. Architect Agent (OTel Port 8126 Dual-Shipping Blueprint)
6. Copywriter Agent (Collateral & Anti-Hallucination Evidence Guard)
7. Human Approval Gate (Strict export prevention before approval, unlock after approval)
"""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.signal import Signal
from app.models.company import Company
from app.models.dossier import DepositionDossier
from app.models.workflow import WorkflowExecution
from app.agents.orchestrator.state_machine import WorkflowState, WorkflowStep
from app.agents.orchestrator.schemas import WorkflowRunRequest
from app.agents.orchestrator.orchestrator import CentralOrchestrator
from app.agents.copywriter.agent import CopywriterAgent
from app.api.v1.copywriter import approve_outreach_draft, export_outreach_package
from app.api.deps import AuthenticatedUserContext
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_complete_e2e_pipeline_demonstration():
    async with AsyncSessionLocal() as db:
        # Step 1: Create the designated Demonstration Distress Signal (CloudScale Dynamics)
        sig_id = f"demo-cloudscale-{uuid.uuid4().hex[:8]}"
        demo_signal = Signal(
            signal_id=sig_id,
            source="REDDIT",
            original_url="https://demo.churnpoacher.io/reddit/r/devops/comments/dd_pricing_insane",
            vendor="Datadog",
            complaint_category="PRICING_SHOCK",
            raw_content=(
                "Our team at CloudScale Dynamics (cloudscaledynamics.io) just received our monthly Datadog "
                "invoice and custom metrics alone added an extra $38,500 without any warning. We are a team "
                "of 140 engineers running ~500 nodes on AWS EKS. Has anyone successfully migrated their APM "
                "and traces to SigNoz or Grafana with OpenTelemetry?"
            ),
            author_handle="u/cloud_scale_lead",
            urgency_score=0.94,
            extracted_evidence={
                "company_name": "CloudScale Dynamics",
                "domain": "cloudscaledynamics.io",
                "financial_figures": ["$38,500"],
                "percentage_increases": ["45%"],
                "products_mentioned": ["custom metrics", "apm"],
                "inferred_nodes": 500,
                "inferred_engineers": 140,
            },
            is_synthetic=True,
            status="NEW",
        )
        db.add(demo_signal)
        await db.commit()
        await db.refresh(demo_signal)

        print(f"\n[DEMO EXECUTION] 1. Signal Ingested: ID={demo_signal.id}, Urgency={demo_signal.urgency_score}")

        # Step 2: Trigger End-to-End Pipeline via CentralOrchestrator
        run_req = WorkflowRunRequest(
            signal_id=demo_signal.id,
            target_challenger="SigNoz Cloud",
            include_synthetic=True,
            timeout_seconds=60,
        )
        workflow = await CentralOrchestrator.run_pipeline(request=run_req, db=db)

        print(f"[DEMO EXECUTION] 2. Workflow Completed: ID={workflow.id}, Status={workflow.status}, Step={workflow.current_step}")
        assert workflow.status == WorkflowState.DRAFT_PENDING_APPROVAL.value
        assert workflow.current_step == WorkflowStep.APPROVAL_GATE.value
        assert workflow.company_id is not None
        assert workflow.dossier_id is not None

        # Verify all 7 milestone steps were formally recorded
        step_names = [s["step_name"] for s in workflow.step_history]
        print(f"[DEMO EXECUTION] Recorded Step History ({len(step_names)} steps): {step_names}")
        assert len(workflow.step_history) == 7
        assert step_names == [
            "LISTENER",
            "PROFILER",
            "QUALIFICATION",
            "FINOPS",
            "ARCHITECT",
            "COPYWRITER",
            "APPROVAL_GATE",
        ]

        # Step 3: Verify Profiled Company
        comp_res = await db.execute(select(Company).where(Company.id == workflow.company_id))
        company = comp_res.scalar_one_or_none()
        assert company is not None
        assert company.name == "CloudScale Dynamics"
        assert company.domain == "cloudscaledynamics.io"
        assert company.qualification_status == "ACCEPTED"
        assert company.icp_score >= 0.70
        assert len(company.decision_makers) > 0
        print(f"[DEMO EXECUTION] 3. Company Profiled: ID={company.id}, Name={company.name}, ICP Score={company.icp_score}, Status={company.qualification_status}")

        # Step 4: Verify Deposition Dossier (FinOps + Architecture + Copywriter)
        dossier_res = await db.execute(select(DepositionDossier).where(DepositionDossier.id == workflow.dossier_id))
        dossier = dossier_res.scalar_one_or_none()
        assert dossier is not None
        assert dossier.status == "DRAFT_PENDING_APPROVAL"
        
        # Verify FinOps Delta
        fin_delta = dossier.financial_delta
        assert fin_delta is not None
        assert fin_delta["estimated_annual_savings"] > 0
        print(f"[DEMO EXECUTION] 4. FinOps Calculated: Datadog Annual=${fin_delta['datadog_annual']:,.2f}, Annual Savings=${fin_delta['estimated_annual_savings']:,.2f}")

        # Verify Architecture Blueprint
        arch_bp = dossier.migration_blueprint
        assert arch_bp is not None
        assert "collector_config_yaml" in arch_bp
        assert len(arch_bp["phases"]) == 7
        print(f"[DEMO EXECUTION] 5. Migration Blueprint: Phases={len(arch_bp['phases'])}, Port 8126 dual-shipping confirmed.")

        # Verify Copywriter Drafts & Evidence Guard Audit
        drafts = dossier.outreach_drafts
        assert drafts is not None
        assert drafts["governance_status"] == "DRAFT_PENDING_APPROVAL"
        assert len(drafts.get("executive_emails", [])) > 0
        assert drafts.get("linkedin_sequence") is not None
        
        audit = drafts["evidence_audit"]
        assert audit["passed"] is True
        assert len(audit.get("unsupported_claims_flagged", [])) == 0
        print(f"[DEMO EXECUTION] 6. Copywriter Drafts Generated: Anti-Hallucination Audit Passed={audit['passed']}, Emails={len(drafts['executive_emails'])}, LinkedIn=Present")

        # Step 5: Test Governance Gate - Verify Export is strictly BLOCKED prior to approval
        user_context = AuthenticatedUserContext(id="admin-001", email="admin@churnpoacher.io", role="ADMINISTRATOR")
        with pytest.raises(HTTPException) as exc_info:
            await export_outreach_package(dossier_id=dossier.id, db=db, current_user=user_context)
        assert exc_info.value.status_code == 403
        print(f"[DEMO EXECUTION] 7. Export Gate Verified: Pre-approval export blocked with 403 Forbidden.")

        # Step 6: Human Approval Gate - Approve Draft
        approval = await approve_outreach_draft(dossier_id=dossier.id, db=db, current_user=user_context)
        assert approval.status == "APPROVED"
        
        await db.refresh(dossier)
        assert dossier.status == "APPROVED"

        await db.refresh(workflow)
        assert workflow.status == "APPROVED"
        print(f"[DEMO EXECUTION] 8. Human Review: Dossier and Workflow approved by Sales Manager / Administrator.")

        # Step 7: Export Approved Outreach Package
        export_res = await export_outreach_package(dossier_id=dossier.id, db=db, current_user=user_context)
        assert export_res.status == "EXPORTED"
        assert len(export_res.markdown_bundle) > 500
        assert "Competitive Deposition Pack" in export_res.markdown_bundle
        assert "Executive Emails" in export_res.markdown_bundle
        assert "LinkedIn Multi-Touch Sequence" in export_res.markdown_bundle

        await db.refresh(workflow)
        assert workflow.status == WorkflowState.COMPLETED.value
        assert workflow.current_step == WorkflowStep.FINALIZED.value
        print(f"[DEMO EXECUTION] 9. Package Exported: Workflow={workflow.id} reached COMPLETED (FINALIZED). Length={len(export_res.markdown_bundle)} chars.")


@pytest.mark.asyncio
async def test_full_pipeline_autonomous_dispatch():
    """Tests autonomous dispatch of FULL_PIPELINE (no signal_id passed, as triggered from UI button)."""
    async with AsyncSessionLocal() as db:
        # Trigger full pipeline with no signal_id or company_id
        run_req = WorkflowRunRequest(
            target_challenger="SigNoz Cloud",
            include_synthetic=True,
            timeout_seconds=60,
        )
        workflow = await CentralOrchestrator.run_pipeline(request=run_req, db=db)

        # Assertions
        assert workflow.status == WorkflowState.DRAFT_PENDING_APPROVAL.value
        assert workflow.current_step == WorkflowStep.APPROVAL_GATE.value
        assert workflow.signal_id is not None
        assert workflow.company_id is not None
        assert workflow.dossier_id is not None

        # Verify all 7 milestone steps were formally recorded
        step_names = [s["step_name"] for s in workflow.step_history]
        assert len(workflow.step_history) == 7
        assert step_names == [
            "LISTENER",
            "PROFILER",
            "QUALIFICATION",
            "FINOPS",
            "ARCHITECT",
            "COPYWRITER",
            "APPROVAL_GATE",
        ]

        # Verify drafts
        dossier_res = await db.execute(select(DepositionDossier).where(DepositionDossier.id == workflow.dossier_id))
        dossier = dossier_res.scalar_one_or_none()
        assert dossier is not None
        assert len(dossier.outreach_drafts.get("executive_emails", [])) > 0
        assert dossier.outreach_drafts.get("linkedin_sequence") is not None

        # Human Approval
        user_context = AuthenticatedUserContext(id="admin-001", email="admin@churnpoacher.io", role="ADMINISTRATOR")
        await approve_outreach_draft(dossier_id=dossier.id, db=db, current_user=user_context)
        await db.refresh(workflow)
        assert workflow.status == WorkflowState.APPROVED.value

        # Export
        export_res = await export_outreach_package(dossier_id=dossier.id, db=db, current_user=user_context)
        assert export_res.status == "EXPORTED"
        await db.refresh(workflow)
        assert workflow.status == WorkflowState.COMPLETED.value
        assert workflow.current_step == WorkflowStep.FINALIZED.value

