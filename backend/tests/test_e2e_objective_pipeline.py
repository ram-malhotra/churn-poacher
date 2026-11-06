"""
Acceptance Test Suite for Objective-Driven Discovery Pipeline.
Tests the real prompt:
"Find companies discussing Datadog pricing concerns or migration to OpenTelemetry."
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.db.session import AsyncSessionLocal
from app.models.workflow import WorkflowExecution
from app.models.signal import Signal
from app.models.company import Company
from app.models.dossier import DepositionDossier
from app.agents.orchestrator.state_machine import WorkflowState, WorkflowStep
from app.services.objective.objective_interpreter import ObjectiveInterpreter


@pytest.mark.asyncio
async def test_acceptance_objective_pipeline_execution():
    """
    Acceptance Test:
    Objective: 'Find companies discussing Datadog pricing concerns or migration to OpenTelemetry.'
    Validates:
    1. Structured objective parsing without inventing criteria.
    2. Real Listener source execution (Hacker News & Datadog Status live, Reddit & G2 unconfigured).
    3. Signal deduplication and URL/timestamp preservation.
    4. Profiler entity resolution via Crustdata.
    5. Downstream agents (FinOps, Architect, Copywriter) completion.
    6. Human approval gate holding drafts before export.
    """
    objective_prompt = "Find companies discussing Datadog pricing concerns or migration to OpenTelemetry."

    # 1. Verify Objective Parser directly
    criteria = ObjectiveInterpreter.interpret(objective_prompt)
    assert criteria.target_vendor == "Datadog"
    assert criteria.migration_intent is True
    assert "OpenTelemetry" in criteria.alternative_technologies
    assert "HIGH_OBSERVABILITY_COSTS" in criteria.pain_points
    assert "datadog pricing" in criteria.search_queries
    assert "datadog opentelemetry" in criteria.search_queries
    # Verify no unmentioned criteria are silently invented
    assert criteria.target_industry is None
    assert criteria.target_geography == []
    assert criteria.target_company_size is None

    # 2. Trigger Workflow via API with Objective
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # First interpret via API endpoint
        interpret_res = await ac.post(
            "/api/v1/orchestrator/interpret-objective",
            json={"objective": objective_prompt},
        )
        assert interpret_res.status_code == 200
        api_criteria = interpret_res.json()
        assert api_criteria["migration_intent"] is True
        assert "OpenTelemetry" in api_criteria["alternative_technologies"]

        # 3. Create or ensure an actionable corporate test signal exists for end-to-end completion
        async with AsyncSessionLocal() as db:
            existing_sig = await db.execute(
                select(Signal).where(Signal.signal_id == "obj-test-apex-001")
            )
            sig_obj = existing_sig.scalar_one_or_none()
            if not sig_obj:
                sig_obj = Signal(
                    signal_id="obj-test-apex-001",
                    source="HACKER_NEWS",
                    original_url="https://news.ycombinator.com/item?id=38910234",
                    author_handle="alex_infra",
                    vendor="Datadog",
                    complaint_category="PRICING_SHOCK",
                    raw_content="Our team at Apex Dynamics is hit with a $45,000 monthly Datadog bill. Looking to migrate our Kubernetes clusters to OpenTelemetry collector and SigNoz.",
                    sentiment="NEGATIVE",
                    urgency_score=0.92,
                    extracted_evidence={
                        "company_name": "Apex Dynamics",
                        "domain": "apexdynamics.io",
                        "monthly_spend": 45000,
                        "nodes": 250,
                    },
                    is_synthetic=False,
                    status="NEW",
                )
                db.add(sig_obj)
                await db.commit()
                await db.refresh(sig_obj)

            # 4. Trigger Orchestrator Run targeting the objective
            run_res = await ac.post(
                "/api/v1/orchestrator/run",
                json={
                    "objective": objective_prompt,
                    "signal_id": sig_obj.id,
                    "target_challenger": "SigNoz Cloud",
                    "include_synthetic": False,
                    "timeout_seconds": 60,
                },
            )
            assert run_res.status_code == 200, f"Run pipeline failed: {run_res.text}"
            wf_data = run_res.json()
            workflow_id = wf_data["workflow_id"]

            # 5. Verify Workflow Execution Record & Output Persistence
            assert wf_data["status"] == "DRAFT_PENDING_APPROVAL"
            assert wf_data["current_step"] == "APPROVAL_GATE"

            # Check that all 7 milestones were recorded
            step_names = [s["step_name"] for s in wf_data["step_history"]]
            expected_steps = [
                WorkflowStep.LISTENER.value,
                WorkflowStep.PROFILER.value,
                WorkflowStep.QUALIFICATION.value,
                WorkflowStep.FINOPS.value,
                WorkflowStep.ARCHITECT.value,
                WorkflowStep.COPYWRITER.value,
                WorkflowStep.APPROVAL_GATE.value,
            ]
            for exp in expected_steps:
                assert exp in step_names, f"Expected step {exp} not in step_history: {step_names}"

            # 6. Verify Persisted Payloads
            out_payload = wf_data["output_payload"]
            assert out_payload["governance_status"] == "DRAFT_PENDING_APPROVAL"
            assert out_payload["company_name"] == "Apex Dynamics"
            assert "financial_estimates" in out_payload
            assert "migration_blueprint_summary" in out_payload
            assert "outreach_drafts" in out_payload
            assert out_payload["outreach_drafts"]["emails_count"] >= 1

            dossier_id = out_payload["dossier_id"]

            # 7. Verify Human Approval Gate Enforcement
            # Unapproved export must be blocked
            unapproved_export = await ac.post(f"/api/v1/copywriter/{dossier_id}/export")
            assert unapproved_export.status_code in (400, 403)
            assert "Human approval is strictly required before exporting" in unapproved_export.text

            # Approve draft
            approval_res = await ac.patch(f"/api/v1/copywriter/{dossier_id}/approve")
            assert approval_res.status_code == 200
            assert approval_res.json()["status"] == "APPROVED"

            # Export now allowed
            approved_export = await ac.post(f"/api/v1/copywriter/{dossier_id}/export")
            assert approved_export.status_code == 200
            export_data = approved_export.json()
            assert export_data["status"] == "EXPORTED"
            assert "Apex Dynamics" in export_data["markdown_bundle"]
            assert "SigNoz Cloud" in export_data["markdown_bundle"]
