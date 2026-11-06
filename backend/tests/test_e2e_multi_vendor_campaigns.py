"""
End-to-End Acceptance Tests for Multi-Vendor Dynamic Campaigns and Pipeline Orchestration.
Demonstrates:
- Campaign A: Datadog -> SigNoz / Grafana
- Campaign B: Splunk -> Elastic / OpenSearch
- Active campaign switching and persistence
- Downstream agent vendor context propagation
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.db.session import AsyncSessionLocal
from app.models.campaign import Campaign
from app.models.workflow import WorkflowExecution
from app.services.campaign_service import CampaignService
from app.agents.orchestrator.orchestrator import CentralOrchestrator
from app.agents.orchestrator.schemas import WorkflowRunRequest


@pytest.mark.asyncio
async def test_e2e_multi_vendor_campaign_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # =====================================================================
        # Step 1: Initial Empty State
        # =====================================================================
        resp_empty = await client.get("/api/v1/campaigns/active")
        assert resp_empty.status_code == 200
        assert resp_empty.json() is None

        # =====================================================================
        # Step 2: Run Pipeline with Campaign A (Datadog -> SigNoz / Grafana)
        # =====================================================================
        obj_datadog = (
            "Find companies in the US and India experiencing high Datadog observability costs, "
            "unexpected billing increases, performance issues, or outages. Prioritize companies "
            "discussing migration to OpenTelemetry, Grafana, or SigNoz. Focus on companies with 200–5000 employees."
        )

        async with AsyncSessionLocal() as session:
            wf_a = await CentralOrchestrator.run_pipeline(
                request=WorkflowRunRequest(
                    objective=obj_datadog,
                    monitoring_mode="ON_DEMAND",
                    include_synthetic=True,
                ),
                db=session,
            )
            wf_a_id = wf_a.id

        # Check Active Campaign after Campaign A run
        resp_act_a = await client.get("/api/v1/campaigns/active")
        assert resp_act_a.status_code == 200
        camp_a_data = resp_act_a.json()
        assert camp_a_data is not None
        assert "Datadog" in camp_a_data["target_vendors"]
        assert camp_a_data["is_active"] is True
        camp_a_id = camp_a_data["id"]

        # Verify workflow A linked campaign A
        async with AsyncSessionLocal() as session:
            wf_res = await session.execute(select(WorkflowExecution).where(WorkflowExecution.id == wf_a_id))
            loaded_wf_a = wf_res.scalar_one()
            assert loaded_wf_a.input_payload.get("campaign_id") == camp_a_id
            assert loaded_wf_a.input_payload.get("target_vendors") == ["Datadog"]

        # =====================================================================
        # Step 3: Run Pipeline with Campaign B (Splunk -> Elastic / OpenSearch)
        # =====================================================================
        obj_splunk = (
            "Find enterprise companies suffering from massive Splunk license cost overruns and indexing fees. "
            "Prioritize teams evaluating migrations to Elastic or OpenSearch."
        )

        async with AsyncSessionLocal() as session:
            wf_b = await CentralOrchestrator.run_pipeline(
                request=WorkflowRunRequest(
                    objective=obj_splunk,
                    monitoring_mode="SCHEDULED",
                    include_synthetic=True,
                ),
                db=session,
            )
            wf_b_id = wf_b.id

        # Check Active Campaign after Campaign B run
        resp_act_b = await client.get("/api/v1/campaigns/active")
        assert resp_act_b.status_code == 200
        camp_b_data = resp_act_b.json()
        assert camp_b_data is not None
        assert "Splunk" in camp_b_data["target_vendors"]
        assert "Elastic" in camp_b_data["alternative_vendors"]
        assert camp_b_data["monitoring_mode"] == "SCHEDULED"
        assert camp_b_data["is_active"] is True
        camp_b_id = camp_b_data["id"]
        assert camp_b_id != camp_a_id

        # Verify Campaign A is now deactivated in DB
        async with AsyncSessionLocal() as session:
            camp_a_db = (await session.execute(select(Campaign).where(Campaign.id == camp_a_id))).scalar_one()
            assert camp_a_db.is_active is False

            # Verify workflow B details
            wf_b_res = await session.execute(select(WorkflowExecution).where(WorkflowExecution.id == wf_b_id))
            loaded_wf_b = wf_b_res.scalar_one()
            assert loaded_wf_b.input_payload.get("campaign_id") == camp_b_id
            assert loaded_wf_b.input_payload.get("target_vendors") == ["Splunk"]
            assert loaded_wf_b.target_challenger in ["Elastic", "OpenSearch"]

            # Verify Datadog status adapter was skipped in Workflow B listener step
            src_results = loaded_wf_b.output_payload.get("source_execution_results", [])
            dd_status_records = [s for s in src_results if s.get("source_name") == "Datadog Status"]
            if dd_status_records:
                assert dd_status_records[0].get("monitoring_status") == "SKIPPED"

        # =====================================================================
        # Step 4: Re-activate Campaign A via API and Verify State Transition
        # =====================================================================
        resp_switch = await client.post(f"/api/v1/campaigns/{camp_a_id}/activate")
        assert resp_switch.status_code == 200
        switched_data = resp_switch.json()
        assert switched_data["id"] == camp_a_id
        assert switched_data["is_active"] is True

        # Now active campaign endpoint should return Campaign A
        resp_act_after = await client.get("/api/v1/campaigns/active")
        assert resp_act_after.status_code == 200
        assert resp_act_after.json()["id"] == camp_a_id
        assert "Datadog" in resp_act_after.json()["target_vendors"]

        # List should show both campaigns
        resp_all = await client.get("/api/v1/campaigns")
        assert resp_all.status_code == 200
        assert resp_all.json()["total"] >= 2
