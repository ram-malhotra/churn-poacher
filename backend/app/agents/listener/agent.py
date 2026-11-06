"""
Central Listener Agent Implementation.
Fetches, normalizes, classifies, deduplicates, and persists competitor signals into the database.
"""

import time
from datetime import datetime, timezone
from typing import List, Optional, Set, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.signal import Signal
from app.models.execution_log import AgentExecutionLog
from app.agents.listener.schemas import (
    NormalizedSignal,
    IngestionSummary,
    AdapterStatus,
    ListenerStatusReport,
    SourceExecutionSummary,
)
from app.agents.listener.deduplicator import SignalDeduplicator
from app.services.sources.datadog_status import DatadogStatusAdapter
from app.services.sources.hackernews import HackerNewsAdapter
from app.services.sources.reddit import RedditAdapter
from app.services.sources.g2_reviews import G2ReviewsAdapter
from app.services.sources.synthetic_generator import SyntheticSignalGenerator


class ListenerAgent:
    """The Listener Agent continuously ingests public signals indicating Datadog dissatisfaction."""

    def __init__(self):
        self.datadog_status = DatadogStatusAdapter()
        self.hackernews = HackerNewsAdapter()
        self.reddit = RedditAdapter()
        self.g2_reviews = G2ReviewsAdapter()
        self.last_run_at: Optional[datetime] = None
        self.is_running: bool = False

    async def get_status_report(self, db: AsyncSession) -> ListenerStatusReport:
        """Returns the readiness and configuration status of each ingestion source."""
        adapters = [
            AdapterStatus(
                name="DATADOG_STATUS",
                enabled=True,
                status="AVAILABLE" if await self.datadog_status.is_available() else "UNAVAILABLE",
                details="Polls official public Datadog Statuspage incidents and components",
            ),
            AdapterStatus(
                name="HACKER_NEWS",
                enabled=True,
                status="AVAILABLE" if await self.hackernews.is_available() else "UNAVAILABLE",
                details="Queries official Algolia HN Search API for competitor discussions",
            ),
            AdapterStatus(
                name="REDDIT",
                enabled=self.reddit.is_configured(),
                status="AVAILABLE" if self.reddit.is_configured() else "DISABLED_NO_CREDS",
                details="Reddit OAuth Script App for r/devops, r/sysadmin, r/aws, r/kubernetes",
            ),
            AdapterStatus(
                name="G2_REVIEWS",
                enabled=self.g2_reviews.is_configured(),
                status="AVAILABLE" if self.g2_reviews.is_configured() else "DISABLED_NO_CREDS",
                details="G2 Enterprise Reviews API for verified competitor customer vents",
            ),
            AdapterStatus(
                name="SYNTHETIC_GENERATOR",
                enabled=settings.DEMO_MODE,
                status="AVAILABLE",
                details="Generates high-conviction realistic synthetic signals (is_synthetic=True)",
            ),
        ]

        # Snapshot of operational source execution states
        sources = [
            SourceExecutionSummary(
                source_name="Hacker News",
                connection_status="CONNECTED",
                monitoring_status="IDLE" if not self.is_running else "SCANNING",
                last_successful_scan=self.last_run_at,
                records_retrieved=0,
                relevant_signals=0,
                errors=[],
                notes="Public Algolia HN Search API active",
            ),
            SourceExecutionSummary(
                source_name="Datadog Status",
                connection_status="CONNECTED",
                monitoring_status="IDLE" if not self.is_running else "SCANNING",
                last_successful_scan=self.last_run_at,
                records_retrieved=0,
                relevant_signals=0,
                errors=[],
                notes="Public Statuspage JSON + RSS feed active",
            ),
            SourceExecutionSummary(
                source_name="Reddit",
                connection_status="CONNECTED" if self.reddit.is_configured() else "UNCONFIGURED",
                monitoring_status="IDLE" if self.reddit.is_configured() else "SKIPPED",
                last_successful_scan=self.last_run_at if self.reddit.is_configured() else None,
                records_retrieved=0,
                relevant_signals=0,
                errors=[] if self.reddit.is_configured() else ["Reddit OAuth credentials not configured in environment"],
                notes="Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET",
            ),
            SourceExecutionSummary(
                source_name="G2 Reviews",
                connection_status="CONNECTED" if self.g2_reviews.is_configured() else "UNCONFIGURED",
                monitoring_status="IDLE" if self.g2_reviews.is_configured() else "SKIPPED",
                last_successful_scan=self.last_run_at if self.g2_reviews.is_configured() else None,
                records_retrieved=0,
                relevant_signals=0,
                errors=[] if self.g2_reviews.is_configured() else ["G2 API key not configured in environment"],
                notes="Requires G2_API_KEY",
            ),
        ]

        from sqlalchemy import select, func
        count_res = await db.execute(select(func.count(Signal.id)))
        total_signals = count_res.scalar() or 0

        return ListenerStatusReport(
            is_running=self.is_running,
            monitoring_mode="ON_DEMAND",
            demo_mode=settings.DEMO_MODE,
            adapters=adapters,
            sources=sources,
            last_run_at=self.last_run_at,
            total_signals_stored=total_signals,
        )

    async def run_ingestion_cycle(
        self,
        db: AsyncSession,
        include_synthetic: Optional[bool] = None,
        max_items_per_source: int = 10,
        queries: Optional[List[str]] = None,
        objective_criteria: Optional[Dict[str, Any]] = None,
    ) -> IngestionSummary:
        """
        Runs a complete signal detection, normalization, classification, and persistence cycle
        across all configured sources, using search queries tailored from user objective.
        """
        start_time = time.time()
        self.is_running = True
        self.last_run_at = datetime.now(timezone.utc)
        
        include_synth = include_synthetic if include_synthetic is not None else settings.DEMO_MODE
        summary = IngestionSummary()
        collected_signals: List[NormalizedSignal] = []

        # Determine queries from objective criteria or explicit list
        search_queries = queries
        if not search_queries and objective_criteria:
            search_queries = objective_criteria.get("search_queries")

        logger.info(
            f"Starting Listener Agent ingestion cycle (demo_mode={include_synth}, "
            f"queries={search_queries})..."
        )

        # -------------------------------------------------------------
        # 1. Datadog Status Page
        # -------------------------------------------------------------
        status_src_summary = SourceExecutionSummary(
            source_name="Datadog Status",
            connection_status="CONNECTED",
            monitoring_status="SCANNING",
            last_successful_scan=None,
            records_retrieved=0,
            relevant_signals=0,
            errors=[],
            notes="Polls official public Datadog Statuspage incidents & RSS",
        )
        try:
            dd_meta = await self.datadog_status.fetch_signals_with_meta()
            status_signals = dd_meta.get("signals", [])
            status_src_summary.records_retrieved = dd_meta.get("records_retrieved", len(status_signals))
            status_src_summary.relevant_signals = len(status_signals[:max_items_per_source])
            status_src_summary.errors = dd_meta.get("errors", [])
            status_src_summary.monitoring_status = "COMPLETED"
            status_src_summary.last_successful_scan = datetime.now(timezone.utc)
            collected_signals.extend(status_signals[:max_items_per_source])
            logger.info(f"Fetched {len(status_signals)} signals from Datadog Status")
        except Exception as e:
            msg = f"Datadog Status fetch error: {str(e)}"
            logger.error(msg)
            status_src_summary.connection_status = "ERROR"
            status_src_summary.monitoring_status = "FAILED"
            status_src_summary.errors.append(msg)
            summary.errors.append(msg)
        summary.sources.append(status_src_summary)

        # -------------------------------------------------------------
        # 2. Hacker News Algolia Search API
        # -------------------------------------------------------------
        hn_src_summary = SourceExecutionSummary(
            source_name="Hacker News",
            connection_status="CONNECTED",
            monitoring_status="SCANNING",
            last_successful_scan=None,
            records_retrieved=0,
            relevant_signals=0,
            errors=[],
            notes="Queries Algolia HN Search for competitive mentions",
        )
        try:
            hn_meta = await self.hackernews.fetch_signals_with_meta(queries=search_queries)
            hn_signals = hn_meta.get("signals", [])
            hn_src_summary.records_retrieved = hn_meta.get("records_retrieved", len(hn_signals))
            hn_src_summary.relevant_signals = len(hn_signals[:max_items_per_source])
            hn_src_summary.errors = hn_meta.get("errors", [])
            hn_src_summary.monitoring_status = "COMPLETED"
            hn_src_summary.last_successful_scan = datetime.now(timezone.utc)
            collected_signals.extend(hn_signals[:max_items_per_source])
            logger.info(f"Fetched {len(hn_signals)} signals from Hacker News")
        except Exception as e:
            msg = f"Hacker News fetch error: {str(e)}"
            logger.error(msg)
            hn_src_summary.connection_status = "ERROR"
            hn_src_summary.monitoring_status = "FAILED"
            hn_src_summary.errors.append(msg)
            summary.errors.append(msg)
        summary.sources.append(hn_src_summary)

        # -------------------------------------------------------------
        # 3. Reddit API
        # -------------------------------------------------------------
        reddit_src_summary = SourceExecutionSummary(
            source_name="Reddit",
            connection_status="CONNECTED" if self.reddit.is_configured() else "UNCONFIGURED",
            monitoring_status="SCANNING" if self.reddit.is_configured() else "SKIPPED",
            last_successful_scan=None,
            records_retrieved=0,
            relevant_signals=0,
            errors=[],
            notes="Reddit OAuth Script App for devops/sysadmin communities",
        )
        if self.reddit.is_configured():
            try:
                reddit_meta = await self.reddit.fetch_signals_with_meta()
                reddit_signals = reddit_meta.get("signals", [])
                reddit_src_summary.records_retrieved = reddit_meta.get("records_retrieved", len(reddit_signals))
                reddit_src_summary.relevant_signals = len(reddit_signals[:max_items_per_source])
                reddit_src_summary.errors = reddit_meta.get("errors", [])
                reddit_src_summary.monitoring_status = "COMPLETED"
                reddit_src_summary.last_successful_scan = datetime.now(timezone.utc)
                collected_signals.extend(reddit_signals[:max_items_per_source])
                logger.info(f"Fetched {len(reddit_signals)} signals from Reddit")
            except Exception as e:
                msg = f"Reddit fetch error: {str(e)}"
                logger.error(msg)
                reddit_src_summary.connection_status = "ERROR"
                reddit_src_summary.monitoring_status = "FAILED"
                reddit_src_summary.errors.append(msg)
                summary.errors.append(msg)
        else:
            reddit_src_summary.errors.append("Reddit API credentials not configured (REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET missing)")
            logger.debug("Skipping Reddit (credentials not configured in environment).")
        summary.sources.append(reddit_src_summary)

        # -------------------------------------------------------------
        # 4. G2 Reviews API
        # -------------------------------------------------------------
        g2_src_summary = SourceExecutionSummary(
            source_name="G2 Reviews",
            connection_status="CONNECTED" if self.g2_reviews.is_configured() else "UNCONFIGURED",
            monitoring_status="SCANNING" if self.g2_reviews.is_configured() else "SKIPPED",
            last_successful_scan=None,
            records_retrieved=0,
            relevant_signals=0,
            errors=[],
            notes="G2 Reviews API integration",
        )
        if self.g2_reviews.is_configured():
            try:
                g2_meta = await self.g2_reviews.fetch_signals_with_meta(queries=search_queries)
                g2_signals = g2_meta.get("signals", [])
                g2_src_summary.records_retrieved = g2_meta.get("records_retrieved", len(g2_signals))
                g2_src_summary.relevant_signals = len(g2_signals[:max_items_per_source])
                g2_src_summary.errors = g2_meta.get("errors", [])
                g2_src_summary.monitoring_status = "COMPLETED"
                g2_src_summary.last_successful_scan = datetime.now(timezone.utc)
                collected_signals.extend(g2_signals[:max_items_per_source])
                logger.info(f"Fetched {len(g2_signals)} signals from G2 Reviews")
            except Exception as e:
                msg = f"G2 Reviews fetch error: {str(e)}"
                logger.error(msg)
                g2_src_summary.connection_status = "ERROR"
                g2_src_summary.monitoring_status = "FAILED"
                g2_src_summary.errors.append(msg)
                summary.errors.append(msg)
        else:
            g2_src_summary.errors.append("G2 API key not configured in environment (G2_API_KEY missing)")
            logger.debug("Skipping G2 Reviews (credentials not configured in environment).")
        summary.sources.append(g2_src_summary)

        # -------------------------------------------------------------
        # 5. Synthetic Signals (EXCLUSIVELY for DEMO mode)
        # -------------------------------------------------------------
        if include_synth:
            try:
                synth_signals = SyntheticSignalGenerator.generate_signals(count=4)
                collected_signals.extend(synth_signals)
                logger.info(f"Generated {len(synth_signals)} synthetic signals")
            except Exception as e:
                msg = f"Synthetic generator error: {str(e)}"
                logger.error(msg)
                summary.errors.append(msg)

        summary.total_fetched = len(collected_signals)

        # -------------------------------------------------------------
        # 6. Deduplicate and Persist
        # -------------------------------------------------------------
        seen_in_batch: Set[str] = set()
        saved_count = 0
        duplicates_count = 0

        for sig in collected_signals:
            summary.signals_by_source[sig.source] = summary.signals_by_source.get(sig.source, 0) + 1
            summary.signals_by_category[sig.complaint_category] = summary.signals_by_category.get(sig.complaint_category, 0) + 1

            if sig.urgency_score >= 0.75:
                summary.high_urgency_count += 1

            is_dup = await SignalDeduplicator.is_duplicate(sig, db, seen_in_batch=seen_in_batch)
            if is_dup:
                duplicates_count += 1
                continue

            # Map NormalizedSignal into existing SQLAlchemy Signal model
            db_signal = Signal(
                signal_id=sig.source_id,
                source=sig.source,
                original_url=sig.source_url,
                author_handle=sig.author,
                vendor=sig.vendor,
                complaint_category=sig.complaint_category,
                raw_content=sig.content,
                sentiment=sig.sentiment,
                urgency_score=sig.urgency_score,
                extracted_evidence=sig.extracted_evidence,
                is_synthetic=sig.is_synthetic,
                status="NEW",
            )
            db.add(db_signal)
            saved_count += 1

        summary.new_signals_saved = saved_count
        summary.duplicates_skipped = duplicates_count

        # Commit newly saved signals
        await db.commit()

        # -------------------------------------------------------------
        # 7. Record Agent Execution Log
        # -------------------------------------------------------------
        duration_ms = int((time.time() - start_time) * 1000)
        summary.execution_time_ms = duration_ms
        self.is_running = False

        log_entry = AgentExecutionLog(
            agent_name="LISTENER",
            signal_id=None,
            status="SUCCESS" if not summary.errors else "PARTIAL_SUCCESS",
            execution_time_ms=duration_ms,
            input_payload={
                "include_synthetic": include_synth,
                "max_items_per_source": max_items_per_source,
                "queries": search_queries,
                "objective_criteria": objective_criteria,
            },
            output_payload=summary.model_dump(mode="json"),
            error_message="; ".join(summary.errors) if summary.errors else None,
        )
        db.add(log_entry)
        await db.commit()

        logger.info(
            f"Listener ingestion cycle complete: {saved_count} saved, {duplicates_count} duplicates skipped "
            f"in {duration_ms}ms"
        )
        return summary
