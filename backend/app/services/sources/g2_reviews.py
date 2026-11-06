"""
G2 Reviews API Adapter.
Safely integrates with G2 API if credentials are provided,
or disables itself gracefully when credentials are absent.
"""

from typing import List, Optional, Dict, Any
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.agents.listener.schemas import NormalizedSignal
from app.agents.listener.normalizer import SignalNormalizer
from app.agents.listener.classifier import SignalClassifier
from app.agents.listener.config import listener_config


class G2ReviewsAdapter:
    NAME = "G2_REVIEWS"

    def __init__(
        self,
        api_key: Optional[str] = settings.G2_API_KEY,
        api_base: str = "https://data.g2.com/api/v1",
    ):
        self.api_key = api_key
        self.api_base = api_base

    def is_configured(self) -> bool:
        """Checks if valid credentials exist for G2 API."""
        return bool(self.api_key and self.api_key.strip())

    async def is_available(self) -> bool:
        return self.is_configured()

    async def fetch_signals(self, queries: Optional[List[str]] = None) -> List[NormalizedSignal]:
        """
        Fetches Datadog reviews from G2 if API key is provided.
        Returns empty list when unconfigured.
        """
        meta = await self.fetch_signals_with_meta(queries)
        return meta["signals"]

    async def fetch_signals_with_meta(self, queries: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetches signals with metadata for telemetry reporting."""
        if not self.is_configured():
            logger.info("G2 Reviews adapter is disabled (G2 API key not configured in environment).")
            return {
                "signals": [],
                "records_retrieved": 0,
                "errors": ["G2 API key not configured in environment (G2_API_KEY missing)"],
            }

        signals: List[NormalizedSignal] = []
        errors: List[str] = []
        total_records_retrieved = 0

        try:
            async with httpx.AsyncClient(timeout=listener_config.REQUEST_TIMEOUT_SECONDS) as client:
                headers = {
                    "Authorization": f"Token token={self.api_key}",
                    "Content-Type": "application/vnd.api+json",
                }
                url = f"{self.api_base}/products/datadog/reviews"
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    review_items = data.get("data", [])
                    total_records_retrieved = len(review_items)
                    for item in review_items:
                        attrs = item.get("attributes", {})
                        body = attrs.get("body", "")
                        if "pricing" in body.lower() or "cost" in body.lower() or "outage" in body.lower():
                            normalized = NormalizedSignal(
                                source="G2_REVIEWS",
                                source_id=f"g2-{item.get('id')}",
                                source_url=attrs.get("url") or "https://www.g2.com/products/datadog/reviews",
                                vendor="Datadog",
                                title=attrs.get("title") or "G2 Review - Datadog",
                                content=body,
                                author=attrs.get("author_name") or "Anonymous Reviewer",
                                signal_type="COMPLAINT",
                                complaint_category="PRICING_SHOCK" if "pricing" in body.lower() else "GENERAL_DISCUSSION",
                                sentiment="NEGATIVE",
                                urgency_score=0.7,
                                confidence_score=0.9,
                                relevance_score=0.85,
                                extracted_evidence={"source": "G2", "review_id": item.get("id")},
                                is_synthetic=False,
                            )
                            signals.append(SignalClassifier.classify(normalized))
                else:
                    msg = f"G2 API returned status {response.status_code}"
                    logger.warning(msg)
                    errors.append(msg)
        except Exception as e:
            msg = f"Error querying G2 Reviews API: {e}"
            logger.error(msg)
            errors.append(msg)

        return {
            "signals": signals,
            "records_retrieved": total_records_retrieved,
            "errors": errors,
        }
