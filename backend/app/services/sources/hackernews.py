"""
Hacker News Algolia Search API Adapter.
Fetches public discussions and outage threads mentioning Datadog.
"""

from typing import List, Dict, Any, Optional, Tuple
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.agents.listener.schemas import NormalizedSignal
from app.agents.listener.normalizer import SignalNormalizer
from app.agents.listener.classifier import SignalClassifier
from app.agents.listener.config import listener_config


class HackerNewsAdapter:
    NAME = "HACKER_NEWS"

    def __init__(self, api_base: str = settings.HACKER_NEWS_API_BASE):
        self.api_base = api_base

    async def is_available(self) -> bool:
        return bool(self.api_base)

    async def fetch_signals(self, queries: Optional[List[str]] = None) -> List[NormalizedSignal]:
        """Queries the public Algolia Hacker News search endpoint."""
        meta = await self.fetch_signals_with_meta(queries)
        return meta["signals"]

    async def fetch_signals_with_meta(self, queries: Optional[List[str]] = None) -> Dict[str, Any]:
        """Queries Algolia HN search endpoint and returns signals, total hits inspected, and errors."""
        signals: List[NormalizedSignal] = []
        errors: List[str] = []
        total_records_retrieved = 0
        queries = queries or listener_config.SEARCH_QUERIES[:3]

        async with httpx.AsyncClient(timeout=listener_config.REQUEST_TIMEOUT_SECONDS) as client:
            for query in queries:
                try:
                    url = f"{self.api_base}/search"
                    params = {
                        "query": query,
                        "tags": "story",
                        "hitsPerPage": 8,
                    }
                    response = await client.get(url, params=params)
                    if response.status_code != 200:
                        msg = f"HN API returned status {response.status_code} for query '{query}'"
                        logger.warning(msg)
                        errors.append(msg)
                        continue

                    data = response.json()
                    hits = data.get("hits", [])
                    total_records_retrieved += len(hits)
                    for hit in hits:
                        # Ignore items that do not mention Datadog in title or text
                        full_text = f"{hit.get('title', '')} {hit.get('story_text', '')}".lower()
                        if "datadog" not in full_text:
                            continue

                        normalized = SignalNormalizer.normalize_hackernews_item(hit)
                        classified = SignalClassifier.classify(normalized)
                        signals.append(classified)

                except Exception as e:
                    msg = f"Error querying Hacker News API for '{query}': {e}"
                    logger.error(msg)
                    errors.append(msg)
                    continue

        return {
            "signals": signals,
            "records_retrieved": total_records_retrieved,
            "errors": errors,
        }
