"""
Comprehensive Acceptance and Regression Tests for Crustdata Live Discovery Architecture.
Tests the 8 core acceptance criteria:
1. Company search
2. Person search
3. Domain search
4. Technology-based search
5. Employee-range search
6. Decision-maker discovery
7. Unknown company/person (never fabricate synthetic data)
8. Repeated cached search (zero redundant credit consumption)
"""

import pytest
import os
from dotenv import load_dotenv
from sqlalchemy import select, func

load_dotenv()

from app.db.session import init_db, AsyncSessionLocal
from app.models.intelligence import IntelligenceEntity
from app.services.crustdata.client import CrustdataClient
from app.services.crustdata.intelligence_service import CrustdataIntelligenceService
from app.services.crustdata.query_interpreter import CrustdataQueryInterpreter
from app.services.crustdata.schemas import (
    EntityType,
    EnrichmentLevel,
    CompanyIntelligenceProfile,
    PersonIntelligenceProfile,
)


@pytest.fixture
def live_client():
    """Provides a live client using the configured CRUSTDATA_API_KEY from environment."""
    key = os.getenv("CRUSTDATA_API_KEY")
    if not key:
        pytest.skip("CRUSTDATA_API_KEY not configured in environment; skipping live acceptance test.")
    return CrustdataClient(api_key=key)


@pytest.mark.asyncio
async def test_acceptance_1_company_search(live_client):
    """1. Company search: Queries Crustdata live dataset for Datadog."""
    candidates = await live_client.search_company_candidates("Datadog", limit=3, mode="LIVE")
    assert len(candidates) > 0
    datadog_cand = next((c for c in candidates if "datadog" in c.name.lower()), candidates[0])
    assert datadog_cand.entity_type == EntityType.COMPANY
    assert datadog_cand.data_origin == "LIVE"
    assert datadog_cand.source == "Crustdata API v2025-11-01"
    assert datadog_cand.is_mock is False
    assert datadog_cand.confidence_score >= 0.70


@pytest.mark.asyncio
async def test_acceptance_2_person_search(live_client):
    """2. Person search: Queries Crustdata live dataset for Elon Musk."""
    candidates = await live_client.search_person_candidates("Elon Musk", limit=3, mode="LIVE")
    assert len(candidates) > 0
    elon = candidates[0]
    assert elon.entity_type == EntityType.PERSON
    assert elon.data_origin == "LIVE"
    assert elon.is_mock is False
    assert "Apex Dynamics" not in (elon.company_name or "")
    assert elon.profile_url is not None


@pytest.mark.asyncio
async def test_acceptance_3_domain_search(live_client):
    """3. Domain search: Exact lookup on datadoghq.com."""
    candidates = await live_client.search_company_candidates("datadoghq.com", limit=1, mode="LIVE")
    assert len(candidates) > 0
    cand = candidates[0]
    assert cand.primary_domain == "datadoghq.com"
    assert cand.entity_type == EntityType.COMPANY
    assert cand.data_origin == "LIVE"


@pytest.mark.asyncio
async def test_acceptance_4_technology_based_search(live_client):
    """4. Technology-based search: Natural language query for companies using Datadog."""
    interp = CrustdataQueryInterpreter.interpret("Find companies using Datadog")
    assert interp.target_entity == EntityType.COMPANY
    assert "Datadog" in interp.technologies
    assert interp.filter_tree["conditions"][0]["field"] == "technographics.technologies.name"

    candidates = await live_client.search_company_candidates(
        query="Datadog",
        limit=3,
        filters=interp.filter_tree,
        mode="LIVE",
    )
    assert len(candidates) > 0
    assert all(c.data_origin == "LIVE" for c in candidates)
    assert all(c.is_mock is False for c in candidates)


@pytest.mark.asyncio
async def test_acceptance_5_employee_range_search(live_client):
    """5. Employee-range search: Natural language query for US companies with 200-1000 employees."""
    interp = CrustdataQueryInterpreter.interpret("Find SaaS companies in the US with 200–1000 employees")
    assert interp.country == "USA"
    assert interp.headcount_min == 200
    assert interp.headcount_max == 1000

    candidates = await live_client.search_company_candidates(
        query="SaaS USA 200-1000",
        limit=3,
        filters=interp.filter_tree,
        mode="LIVE",
    )
    assert len(candidates) > 0
    assert all(c.data_origin == "LIVE" for c in candidates)


@pytest.mark.asyncio
async def test_acceptance_6_decision_maker_discovery(live_client):
    """6. Decision-maker discovery: Finds VP Engineering at NVIDIA."""
    interp = CrustdataQueryInterpreter.interpret("Find VP Engineering at NVIDIA")
    assert interp.target_entity == EntityType.PERSON
    assert interp.company_name == "NVIDIA"
    assert interp.job_title == "VP Engineering"

    candidates = await live_client.search_person_candidates(
        query="VP Engineering at NVIDIA",
        limit=3,
        filters=interp.filter_tree,
        mode="LIVE",
    )
    assert len(candidates) > 0
    assert all(c.entity_type == EntityType.PERSON for c in candidates)
    assert any("engineering" in (c.current_title or "").lower() for c in candidates)


@pytest.mark.asyncio
async def test_acceptance_7_unknown_company_or_person(live_client):
    """7. Unknown company/person: Never fabricates synthetic profiles."""
    unknown_domain = "nonexistent-entity-xyz-999999.io"
    candidates = await live_client.search_company_candidates(unknown_domain, limit=3, mode="LIVE")
    # Must return empty candidate list for non-existent entities
    assert len(candidates) == 0

    # If enriched directly, returns unverified status without fake claims (e.g. Apex Dynamics)
    profile = await live_client.enrich_company(unknown_domain, level=EnrichmentLevel.LEVEL_2_STANDARD, mode="LIVE")
    assert profile.verification_status == "UNVERIFIED"
    assert "Apex Dynamics" not in profile.name
    assert len(profile.technographics) == 0


@pytest.mark.asyncio
async def test_acceptance_8_repeated_cached_search(live_client):
    """8. Repeated cached search: Ensures cache HIT and zero duplicate credits consumed."""
    service = CrustdataIntelligenceService(client=live_client)
    target = "datadoghq.com"

    async with AsyncSessionLocal() as db:
        # First call: live enrichment
        p1 = await service.enrich_entity(
            db,
            identifier=target,
            entity_type=EntityType.COMPANY,
            level=EnrichmentLevel.LEVEL_2_STANDARD,
            force_refresh=True,
            mode="LIVE",
        )
        assert isinstance(p1, CompanyIntelligenceProfile)
        assert p1.primary_domain == "datadoghq.com"

        # Second call: Cache HIT
        p2 = await service.enrich_entity(
            db,
            identifier=target,
            entity_type=EntityType.COMPANY,
            level=EnrichmentLevel.LEVEL_2_STANDARD,
            force_refresh=False,
            mode="LIVE",
        )
        assert p2.data_origin == "CACHED"
        assert p2.source == "Crustdata Local Cache"

        # Verify only 1 row exists in intelligence_entities
        count_stmt = select(func.count(IntelligenceEntity.id)).where(IntelligenceEntity.primary_domain == "datadoghq.com")
        total_rows = (await db.execute(count_stmt)).scalar()
        assert total_rows == 1
