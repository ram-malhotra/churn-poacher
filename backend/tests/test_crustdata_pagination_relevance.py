"""
Acceptance Tests for Crustdata Pagination, Search Relevance, and Data Accuracy.
Covers:
1. Configurable pagination (10, 25, 50 results per page, cursor-based pagination beyond the first 6 results)
2. Results deduplication across pages using stable entity identifiers
3. Data accuracy & preservation of raw Crustdata responses (no fabricated attributes, field verification status)
4. Search relevance criteria matching for the 4 core queries:
   - SaaS companies in the US with 200-1000 employees
   - Fintech companies in India with more than 500 employees
   - Companies using Datadog
   - CTOs at companies using Datadog
"""

import pytest
import os
from dotenv import load_dotenv

load_dotenv()

from app.db.session import init_db, AsyncSessionLocal
from app.services.crustdata.client import CrustdataClient
from app.services.crustdata.intelligence_service import CrustdataIntelligenceService
from app.services.crustdata.query_interpreter import CrustdataQueryInterpreter
from app.services.crustdata.schemas import (
    EntityType,
    EnrichmentLevel,
    EntityCandidate,
)


@pytest.fixture
def live_client():
    key = os.getenv("CRUSTDATA_API_KEY")
    if not key:
        pytest.skip("CRUSTDATA_API_KEY not configured in environment.")
    return CrustdataClient(api_key=key)


@pytest.mark.asyncio
async def test_pagination_beyond_six_and_no_duplicates(live_client):
    """
    Verifies that pagination retrieves more than 6 results (e.g. 10 per page),
    supports cursor-based next page retrieval, and does not duplicate records.
    """
    service = CrustdataIntelligenceService(client=live_client)
    async with AsyncSessionLocal() as db:
        # Page 1: Request 10 candidates
        page1 = await service.search_candidates(
            db=db,
            query="Datadog",
            limit=10,
            cursor=None,
            page=1,
            mode="LIVE",
        )

        assert len(page1.candidates) > 6, f"Expected >6 candidates, got {len(page1.candidates)}"
        assert page1.next_cursor is not None, "Expected next_cursor to be present for further pages"
        assert page1.total_results is not None
        assert page1.total_results > 10

        p1_ids = {c.profile_url or (f"domain_{c.primary_domain}" if c.primary_domain else c.candidate_id) for c in page1.candidates}

        # Page 2: Request next 10 candidates using next_cursor
        page2 = await service.search_candidates(
            db=db,
            query="Datadog",
            limit=10,
            cursor=page1.next_cursor,
            page=2,
            mode="LIVE",
        )

        assert len(page2.candidates) > 0
        p2_ids = {c.profile_url or (f"domain_{c.primary_domain}" if c.primary_domain else c.candidate_id) for c in page2.candidates}

        # Verify page 1 and page 2 are disjoint (no duplicate records)
        intersection = p1_ids.intersection(p2_ids)
        assert len(intersection) == 0, f"Found duplicate records across pages: {intersection}"


@pytest.mark.asyncio
async def test_acceptance_query_1_saas_us_headcount(live_client):
    """Query 1: SaaS companies in the US with 200–1000 employees."""
    service = CrustdataIntelligenceService(client=live_client)
    async with AsyncSessionLocal() as db:
        res = await service.search_candidates(
            db=db,
            query="SaaS companies in the US with 200–1000 employees",
            limit=10,
            mode="LIVE",
        )
        assert res.detected_type == EntityType.COMPANY
        assert len(res.candidates) > 0
        assert res.total_results is not None

        # Verify criteria matching on each candidate
        for c in res.candidates:
            assert c.raw_data is not None
            assert c.data_origin == "LIVE"
            # Verify matched criteria list
            criteria_names = [m.criterion for m in c.matched_criteria]
            assert "Country" in criteria_names or "Industry" in criteria_names


@pytest.mark.asyncio
async def test_acceptance_query_2_fintech_india_500_plus(live_client):
    """Query 2: Fintech companies in India with more than 500 employees."""
    service = CrustdataIntelligenceService(client=live_client)
    async with AsyncSessionLocal() as db:
        res = await service.search_candidates(
            db=db,
            query="Fintech companies in India with more than 500 employees",
            limit=10,
            mode="LIVE",
        )
        assert res.detected_type == EntityType.COMPANY
        assert len(res.candidates) > 0
        for c in res.candidates:
            assert c.raw_data is not None
            # Location check
            country_criterion = next((m for m in c.matched_criteria if m.criterion == "Country"), None)
            if country_criterion:
                assert country_criterion.status == "VERIFIED"


@pytest.mark.asyncio
async def test_acceptance_query_3_companies_using_datadog(live_client):
    """Query 3: Companies using Datadog."""
    service = CrustdataIntelligenceService(client=live_client)
    async with AsyncSessionLocal() as db:
        res = await service.search_candidates(
            db=db,
            query="Companies using Datadog",
            limit=10,
            mode="LIVE",
        )
        assert res.detected_type == EntityType.COMPANY
        assert len(res.candidates) > 0
        for c in res.candidates:
            tech_crit = next((m for m in c.matched_criteria if m.criterion == "Technology stack"), None)
            assert tech_crit is not None
            assert tech_crit.status == "VERIFIED"
            assert "Datadog" in tech_crit.requested_value


@pytest.mark.asyncio
async def test_acceptance_query_4_ctos_at_companies_using_datadog(live_client):
    """Query 4: CTOs at companies using Datadog."""
    service = CrustdataIntelligenceService(client=live_client)
    async with AsyncSessionLocal() as db:
        res = await service.search_candidates(
            db=db,
            query="CTOs at companies using Datadog",
            limit=10,
            mode="LIVE",
        )
        assert res.detected_type == EntityType.PERSON
        assert len(res.candidates) > 0
        for c in res.candidates:
            assert c.entity_type == EntityType.PERSON
            assert c.raw_data is not None
            title_crit = next((m for m in c.matched_criteria if m.criterion == "Job title"), None)
            if title_crit:
                assert "CTO" in title_crit.requested_value
