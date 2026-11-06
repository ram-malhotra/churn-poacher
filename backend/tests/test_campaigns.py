"""
Tests for Multi-Vendor Dynamic Campaigns, Campaign Persistence, and API Endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.main import app
from app.db.session import AsyncSessionLocal
from app.models.campaign import Campaign
from app.services.campaign_service import CampaignService
from app.services.objective.objective_interpreter import ObjectiveInterpreter
from app.agents.listener.agent import ListenerAgent
from app.agents.copywriter.agent import CopywriterAgent
from app.agents.copywriter.personalization import PersonalizationEngine
from app.models.company import Company
from app.models.signal import Signal


# ---------------------------------------------------------------------------
# 1. Multi-Vendor Objective Interpretation & Campaign Extraction
# ---------------------------------------------------------------------------

def test_campaign_extraction_datadog():
    objective = (
        "Find companies in the US and India experiencing high Datadog observability costs, "
        "unexpected billing increases, performance issues, or outages. Prioritize companies "
        "discussing migration to OpenTelemetry, Grafana, or SigNoz. Focus on companies with 200–5000 employees."
    )
    criteria = ObjectiveInterpreter.interpret(objective)
    assert criteria.target_vendors == ["Datadog"]
    assert "OpenTelemetry" in criteria.alternative_technologies
    assert "Grafana" in criteria.alternative_technologies
    assert "SigNoz" in criteria.alternative_technologies
    assert "Datadog" in criteria.campaign_name
    assert "OpenTelemetry" in criteria.campaign_name


def test_campaign_extraction_splunk():
    objective = (
        "Find enterprise companies suffering from massive Splunk license cost overruns and indexing fees. "
        "Prioritize teams evaluating migrations to Elastic or OpenSearch."
    )
    criteria = ObjectiveInterpreter.interpret(objective)
    assert "Splunk" in criteria.target_vendors
    assert "Elastic" in criteria.alternative_technologies
    assert "OpenSearch" in criteria.alternative_technologies
    assert "Splunk" in criteria.campaign_name


def test_campaign_extraction_new_relic():
    objective = (
        "Find engineering teams frustrated with New Relic full-platform user billing "
        "and considering migrations to Grafana Cloud and OpenTelemetry."
    )
    criteria = ObjectiveInterpreter.interpret(objective)
    assert "New Relic" in criteria.target_vendors
    assert "Grafana" in criteria.alternative_technologies
    assert "OpenTelemetry" in criteria.alternative_technologies
    assert "New Relic" in criteria.campaign_name


def test_campaign_extraction_dynatrace():
    objective = (
        "Find enterprise organizations looking to replace Dynatrace host-unit pricing "
        "with OpenTelemetry-native monitoring."
    )
    criteria = ObjectiveInterpreter.interpret(objective)
    assert "Dynatrace" in criteria.target_vendors
    assert "OpenTelemetry" in criteria.alternative_technologies
    assert "Dynatrace" in criteria.campaign_name


# ---------------------------------------------------------------------------
# 2. Campaign Service Layer & Persistence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_campaign_service_create_and_active_switch():
    async with AsyncSessionLocal() as session:
        # Verify initial empty state (clean_database wiped table)
        active_initial = await CampaignService.get_active_campaign(session)
        assert active_initial is None

        # Create Campaign A: Datadog
        camp_a = await CampaignService.create_or_update_from_objective(
            db=session,
            objective="Find companies facing unexpected Datadog billing increases considering SigNoz or Grafana.",
            monitoring_mode="ON_DEMAND",
        )
        assert camp_a.id is not None
        assert camp_a.is_active is True
        assert "Datadog" in camp_a.target_vendors
        assert "SigNoz" in camp_a.alternative_vendors or "Grafana" in camp_a.alternative_vendors

        active_now = await CampaignService.get_active_campaign(session)
        assert active_now is not None
        assert active_now.id == camp_a.id

        # Create Campaign B: Splunk -> Elastic
        camp_b = await CampaignService.create_or_update_from_objective(
            db=session,
            objective="Find companies suffering from Splunk cost overruns migrating to Elastic.",
            monitoring_mode="SCHEDULED",
        )
        assert camp_b.id != camp_a.id
        assert camp_b.is_active is True
        assert "Splunk" in camp_b.target_vendors
        assert "Elastic" in camp_b.alternative_vendors

        # Verify Campaign A is now inactive
        await session.refresh(camp_a)
        assert camp_a.is_active is False

        # Switch back to Campaign A via activate_campaign
        activated = await CampaignService.activate_campaign(session, camp_a.id)
        assert activated.id == camp_a.id
        assert activated.is_active is True

        await session.refresh(camp_b)
        assert camp_b.is_active is False


# ---------------------------------------------------------------------------
# 3. Campaign API Endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_campaign_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Empty state check
        resp_empty = await client.get("/api/v1/campaigns/active")
        assert resp_empty.status_code == 200
        assert resp_empty.json() is None

        # 2. Create Campaign via API
        payload = {
            "name": "Splunk -> Elastic Enterprise",
            "objective": "Find companies struggling with Splunk ingestion costs moving to Elastic.",
            "monitoring_mode": "ON_DEMAND",
        }
        resp_create = await client.post("/api/v1/campaigns", json=payload)
        assert resp_create.status_code == 201
        created_data = resp_create.json()
        assert created_data["name"] == "Splunk -> Elastic Enterprise"
        assert "Splunk" in created_data["target_vendors"]
        assert created_data["is_active"] is True
        camp_id = created_data["id"]

        # 3. GET /campaigns/active
        resp_active = await client.get("/api/v1/campaigns/active")
        assert resp_active.status_code == 200
        active_data = resp_active.json()
        assert active_data["id"] == camp_id
        assert "Splunk" in active_data["target_vendors"]

        # 4. List campaigns
        resp_list = await client.get("/api/v1/campaigns")
        assert resp_list.status_code == 200
        list_data = resp_list.json()
        assert list_data["total"] >= 1
        assert any(c["id"] == camp_id for c in list_data["campaigns"])

        # 5. Activate campaign endpoint
        resp_act = await client.post(f"/api/v1/campaigns/{camp_id}/activate")
        assert resp_act.status_code == 200
        assert resp_act.json()["is_active"] is True


# ---------------------------------------------------------------------------
# 4. Listener Agent Vendor Filtering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_listener_skips_datadog_when_splunk_targeted():
    async with AsyncSessionLocal() as session:
        listener = ListenerAgent()
        summary = await listener.run_ingestion_cycle(
            db=session,
            include_synthetic=False,
            max_items_per_source=2,
            target_vendors=["Splunk"],
            queries=["Splunk cost overruns"],
        )

        # Verify Datadog Status source was SKIPPED
        dd_sources = [s for s in summary.sources if s.source_name == "Datadog Status"]
        assert len(dd_sources) == 1
        assert dd_sources[0].monitoring_status == "SKIPPED"
        assert "Splunk" in (dd_sources[0].notes or "")


# ---------------------------------------------------------------------------
# 5. Copywriter Agent Multi-Vendor Adaptation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_copywriter_multi_vendor_messaging():
    company_data = {
        "name": "Acme Analytics",
        "domain": "acme.io",
        "industry": "Fintech",
        "estimated_size": "200-500 employees",
        "icp_score": 0.88,
        "qualification_status": "ACCEPTED",
    }
    signal_data = {
        "complaint_category": "PRICING_SHOCK",
        "source": "HACKER_NEWS",
        "raw_content": "Our Splunk indexing bill increased by 60% this quarter.",
        "urgency_score": 0.9,
    }

    # Context with Splunk as target vendor
    context_splunk = PersonalizationEngine.get_context(
        company_data=company_data,
        signal_data=signal_data,
        target_challenger="Elastic",
        target_vendor="Splunk",
    )
    assert context_splunk["target_vendor"] == "Splunk"
    assert "Splunk" in context_splunk["hook_headline"]
    assert "Splunk" in context_splunk["primary_pain"]
