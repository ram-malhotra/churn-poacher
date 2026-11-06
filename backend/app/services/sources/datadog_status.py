"""
Datadog Public Status Page API Adapter.
Fetches public incidents and component degradations from status.datadoghq.com.
Supports both the official Statuspage API JSON and the incident history RSS feed.
"""

from typing import List, Dict, Any, Optional, Tuple
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.agents.listener.schemas import NormalizedSignal
from app.agents.listener.normalizer import SignalNormalizer, strip_html
from app.agents.listener.classifier import SignalClassifier


class DatadogStatusAdapter:
    NAME = "DATADOG_STATUS"

    def __init__(
        self,
        endpoint_url: str = settings.DATADOG_STATUS_PAGE_URL,
        rss_url: str = "https://status.datadoghq.com/history.rss",
    ):
        self.endpoint_url = endpoint_url
        self.rss_url = rss_url

    async def is_available(self) -> bool:
        return bool(self.endpoint_url or self.rss_url)

    async def fetch_signals(self) -> List[NormalizedSignal]:
        """Fetches active and recent incidents from Datadog's official status feed."""
        meta = await self.fetch_signals_with_meta()
        return meta["signals"]

    async def fetch_signals_with_meta(self) -> Dict[str, Any]:
        """Fetches incidents with metadata for telemetry reporting."""
        signals, count, errors = await self._fetch_json()
        if signals:
            return {"signals": signals, "records_retrieved": count, "errors": errors}

        # Fallback to official incident history RSS feed
        logger.info("Falling back to Datadog Status history RSS feed...")
        rss_signals, rss_count, rss_errors = await self._fetch_rss()
        return {
            "signals": rss_signals,
            "records_retrieved": rss_count,
            "errors": errors + rss_errors,
        }

    async def _fetch_json(self) -> Tuple[List[NormalizedSignal], int, List[str]]:
        signals: List[NormalizedSignal] = []
        errors: List[str] = []
        records_count = 0
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChurnPoacher/1.0",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                response = await client.get(self.endpoint_url)
                if response.status_code == 200:
                    data = response.json()
                    incidents = data.get("incidents", [])
                    records_count = len(incidents)
                    for incident in incidents:
                        normalized = SignalNormalizer.normalize_datadog_incident(incident)
                        classified = SignalClassifier.classify(normalized)
                        signals.append(classified)
                else:
                    errors.append(f"Statuspage API returned HTTP {response.status_code}")
        except Exception as e:
            msg = f"Datadog JSON API check failed: {e}"
            logger.debug(msg)
            errors.append(msg)
        return signals, records_count, errors

    async def _fetch_rss(self) -> Tuple[List[NormalizedSignal], int, List[str]]:
        signals: List[NormalizedSignal] = []
        errors: List[str] = []
        records_count = 0
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.rss_url)
                if response.status_code != 200:
                    msg = f"Datadog RSS feed returned HTTP {response.status_code}"
                    logger.warning(msg)
                    errors.append(msg)
                    return [], 0, errors

                root = ET.fromstring(response.text)
                items = root.findall(".//item")
                records_count = len(items)
                for item in items:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    pub_elem = item.find("pubDate")
                    desc_elem = item.find("description")
                    guid_elem = item.find("guid")

                    title = strip_html(title_elem.text) if title_elem is not None and title_elem.text else "Datadog Incident"
                    link = link_elem.text.strip() if link_elem is not None and link_elem.text else "https://status.datadoghq.com"
                    guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else link.split("/")[-1]
                    description = strip_html(desc_elem.text) if desc_elem is not None and desc_elem.text else title

                    published_at = datetime.now(timezone.utc)
                    if pub_elem is not None and pub_elem.text:
                        try:
                            published_at = parsedate_to_datetime(pub_elem.text)
                            if published_at.tzinfo is None:
                                published_at = published_at.replace(tzinfo=timezone.utc)
                            else:
                                published_at = published_at.astimezone(timezone.utc)
                        except Exception:
                            pass

                    normalized = NormalizedSignal(
                        source="DATADOG_STATUS",
                        source_id=f"dd-status-{guid}",
                        source_url=link,
                        vendor="Datadog",
                        title=title,
                        content=f"{title}: {description}",
                        author="Datadog SRE",
                        published_at=published_at,
                        signal_type="VENDOR_INCIDENT",
                        complaint_category="OUTAGE",
                        sentiment="NEGATIVE",
                        urgency_score=0.9,
                        confidence_score=1.0,
                        relevance_score=0.95,
                        extracted_evidence={
                            "incident_title": title,
                            "url": link,
                            "guid": guid,
                        },
                        is_synthetic=False,
                    )
                    signals.append(SignalClassifier.classify(normalized))
        except Exception as e:
            msg = f"Datadog RSS fetch error: {e}"
            logger.error(msg)
            errors.append(msg)

        return signals, records_count, errors
