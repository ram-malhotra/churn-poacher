"""
Listener Service Layer.
Coordinates listener agent runs and aggregates quantitative metrics from the database.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.signal import Signal
from app.models.execution_log import AgentExecutionLog
from app.agents.listener.agent import ListenerAgent
from app.agents.listener.schemas import (
    IngestionSummary,
    ListenerStatusReport,
    ListenerMetricsReport,
)


class ListenerService:
    def __init__(self):
        self.agent = ListenerAgent()

    async def run_cycle(
        self,
        db: AsyncSession,
        include_synthetic: Optional[bool] = None,
        max_items_per_source: int = 10,
        queries: Optional[List[str]] = None,
        objective_criteria: Optional[Dict[str, Any]] = None,
    ) -> IngestionSummary:
        """Triggers a single ingestion cycle."""
        return await self.agent.run_ingestion_cycle(
            db=db,
            include_synthetic=include_synthetic,
            max_items_per_source=max_items_per_source,
            queries=queries,
            objective_criteria=objective_criteria,
        )

    async def get_status(self, db: AsyncSession) -> ListenerStatusReport:
        """Returns the readiness and adapter status report."""
        return await self.agent.get_status_report(db)

    async def get_metrics(self, db: AsyncSession) -> ListenerMetricsReport:
        """Computes comprehensive listener operational metrics."""
        # Total signals
        total_res = await db.execute(select(func.count(Signal.id)))
        total_count = total_res.scalar() or 0

        # Real vs. Synthetic
        real_res = await db.execute(select(func.count(Signal.id)).where(Signal.is_synthetic == False))
        real_count = real_res.scalar() or 0

        synth_res = await db.execute(select(func.count(Signal.id)).where(Signal.is_synthetic == True))
        synth_count = synth_res.scalar() or 0

        # High urgency signals
        urgency_res = await db.execute(select(func.count(Signal.id)).where(Signal.urgency_score >= 0.75))
        urgency_count = urgency_res.scalar() or 0

        # Signals by source
        source_res = await db.execute(
            select(Signal.source, func.count(Signal.id)).group_by(Signal.source)
        )
        sources_dict = dict(source_res.all())

        # Signals by category
        cat_res = await db.execute(
            select(Signal.complaint_category, func.count(Signal.id)).group_by(Signal.complaint_category)
        )
        cats_dict = dict(cat_res.all())

        return ListenerMetricsReport(
            total_signals_collected=total_count,
            real_signals_count=real_count,
            synthetic_signals_count=synth_count,
            signals_by_source=sources_dict,
            signals_by_category=cats_dict,
            duplicates_rejected=0,
            high_urgency_signals=urgency_count,
        )


listener_service = ListenerService()
