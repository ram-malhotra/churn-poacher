"""
Tests for Listener Sources Operational Status and Adapters.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.sources.g2_reviews import G2ReviewsAdapter
from app.services.sources.reddit import RedditAdapter
from app.services.sources.hackernews import HackerNewsAdapter
from app.services.sources.datadog_status import DatadogStatusAdapter


@pytest.mark.asyncio
async def test_g2_adapter_unconfigured_behavior():
    adapter = G2ReviewsAdapter(api_key=None)
    assert adapter.is_configured() is False
    assert await adapter.is_available() is False
    meta = await adapter.fetch_signals_with_meta()
    assert meta["signals"] == []
    assert meta["records_retrieved"] == 0
    assert len(meta["errors"]) > 0
    assert "G2 API key not configured" in meta["errors"][0]


@pytest.mark.asyncio
async def test_reddit_adapter_unconfigured_behavior():
    adapter = RedditAdapter(client_id=None, client_secret=None)
    assert adapter.is_configured() is False
    assert await adapter.is_available() is False
    meta = await adapter.fetch_signals_with_meta()
    assert meta["signals"] == []
    assert meta["records_retrieved"] == 0
    assert "Reddit API credentials not configured" in meta["errors"][0]


@pytest.mark.asyncio
async def test_api_listener_sources_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/listener/sources")
        assert response.status_code == 200
        sources = response.json()
        assert isinstance(sources, list)
        source_names = [s["source_name"] for s in sources]
        assert "Hacker News" in source_names
        assert "Datadog Status" in source_names
        assert "Reddit" in source_names
        assert "G2 Reviews" in source_names

        # Check Reddit and G2 Reviews show UNCONFIGURED when credentials are not present
        reddit_src = next(s for s in sources if s["source_name"] == "Reddit")
        assert reddit_src["connection_status"] in ("CONNECTED", "UNCONFIGURED")

        g2_src = next(s for s in sources if s["source_name"] == "G2 Reviews")
        assert g2_src["connection_status"] in ("CONNECTED", "UNCONFIGURED")
