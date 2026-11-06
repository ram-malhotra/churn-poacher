"""
Central Orchestrator Service.
Coordinates workflow lifecycle, concurrency checks, duplicate prevention, retries,
and pipeline observability.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from app.core.logging import logger
from app.models.workflow import WorkflowExecution
from app.models.company import Company
from app.models.signal import Signal
from app.agents.orchestrator.state_machine import WorkflowState, ACTIVE_RUNNING_STATES
from app.agents.orchestrator.schemas import (
    WorkflowRunRequest,
    WorkflowResponse,
    WorkflowMetricsResponse,
)
from app.agents.orchestrator.pipeline import PipelineRunner
from app.agents.orchestrator.config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TARGET_CHALLENGER,
)


class CentralOrchestrator:
    """Manages multi-agent execution workflows with concurrency and retry governance."""

    @classmethod
    async def run_pipeline(
        cls,
        request: WorkflowRunRequest,
        db: AsyncSession,
    ) -> WorkflowExecution:
        """
        Initiates an orchestrated workflow run.
        Prevents concurrent duplicate workflows on the same target company or signal.
        """
        # 1. Duplicate execution check: prevent starting a new workflow if one is already running
        if request.company_id or request.signal_id:
            active_conditions = [
                WorkflowExecution.status.in_([s.value for s in ACTIVE_RUNNING_STATES])
            ]
            target_conditions = []
            if request.company_id:
                target_conditions.append(WorkflowExecution.company_id == request.company_id)
            if request.signal_id:
                target_conditions.append(WorkflowExecution.signal_id == request.signal_id)

            check_query = select(WorkflowExecution).where(
                and_(*active_conditions, or_(*target_conditions))
            )
            active_existing = await db.execute(check_query)
            existing_wf = active_existing.scalar_one_or_none()

            if existing_wf:
                logger.warning(f"Active workflow {existing_wf.id} already running for target. Preventing duplicate run.")
                raise ValueError(
                    f"A workflow is already in progress for this target (Workflow ID: {existing_wf.id}, "
                    f"Status: {existing_wf.status}). Duplicate concurrent executions are prevented."
                )

        # 2. Determine workflow type and synthetic flag
        workflow_type = "FULL_PIPELINE"
        is_synthetic = request.include_synthetic
        if request.company_id:
            workflow_type = "SINGLE_COMPANY"
            comp_res = await db.execute(select(Company).where(Company.id == request.company_id))
            comp = comp_res.scalar_one_or_none()
            if comp:
                is_synthetic = comp.is_synthetic
        elif request.signal_id:
            workflow_type = "SINGLE_SIGNAL"
            sig_res = await db.execute(select(Signal).where(Signal.id == request.signal_id))
            sig = sig_res.scalar_one_or_none()
            if sig:
                is_synthetic = sig.is_synthetic

        # 2b. Campaign creation or resolution
        campaign = None
        if request.objective:
            from app.services.campaign_service import CampaignService
            campaign = await CampaignService.create_or_update_from_objective(
                db=db,
                objective=request.objective,
                monitoring_mode=getattr(request, "monitoring_mode", "ON_DEMAND") or "ON_DEMAND",
            )
        else:
            from app.services.campaign_service import CampaignService
            campaign = await CampaignService.get_active_campaign(db)
            if campaign:
                campaign.last_executed_at = datetime.now(timezone.utc)
                await db.commit()

        target_challenger = request.target_challenger
        if campaign and campaign.alternative_vendors and (not request.target_challenger or request.target_challenger in ("SigNoz Cloud", "SigNoz")):
            target_challenger = campaign.alternative_vendors[0]

        input_payload = request.model_dump()
        if campaign:
            input_payload["campaign_id"] = campaign.id
            input_payload["target_vendors"] = campaign.target_vendors
            input_payload["alternative_vendors"] = campaign.alternative_vendors
            if not input_payload.get("objective") and campaign.original_objective:
                input_payload["objective"] = campaign.original_objective

        # 3. Create initial WorkflowExecution entry
        workflow = WorkflowExecution(
            workflow_type=workflow_type,
            status=WorkflowState.PENDING.value,
            current_step="INIT",
            signal_id=request.signal_id,
            company_id=request.company_id,
            target_challenger=target_challenger,
            max_retries=request.max_retries,
            step_history=[],
            input_payload=input_payload,
            output_payload={},
            is_synthetic=is_synthetic,
        )
        db.add(workflow)
        await db.commit()
        await db.refresh(workflow)

        # 4. Check if persistent background execution is requested
        if getattr(request, "async_worker", False):
            from app.worker.queue import WorkflowTaskQueue
            enqueued = await WorkflowTaskQueue.enqueue(
                workflow_id=workflow.id,
                timeout_seconds=request.timeout_seconds,
            )
            if enqueued:
                workflow.status = "QUEUED"
                await db.commit()
                await db.refresh(workflow)
                return workflow

        # 5. Direct async execution (default for synchronous API calls and automated tests)
        return await PipelineRunner.execute_workflow(
            workflow=workflow,
            db=db,
            timeout_seconds=request.timeout_seconds,
        )

    @classmethod
    async def retry_workflow(
        cls,
        workflow_id: str,
        db: AsyncSession,
        max_retries_override: Optional[int] = None,
    ) -> WorkflowExecution:
        """
        Retries a failed or rejected workflow from its last incomplete step.
        Reuses completed upstream steps to avoid unnecessary re-computation.
        """
        res = await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == workflow_id))
        workflow = res.scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found.")

        if workflow.status in [s.value for s in ACTIVE_RUNNING_STATES]:
            raise ValueError(f"Workflow {workflow_id} is currently running. Cannot trigger retry.")

        max_allowed = max_retries_override if max_retries_override is not None else workflow.max_retries
        if workflow.retry_count >= max_allowed:
            raise ValueError(
                f"Workflow {workflow_id} has exhausted its retry limit ({workflow.retry_count}/{max_allowed})."
            )

        # Reset state for resumption
        workflow.status = WorkflowState.PENDING.value
        workflow.error_details = None
        if max_retries_override is not None:
            workflow.max_retries = max_retries_override

        await db.commit()
        logger.info(f"Retrying workflow {workflow_id} (Attempt {workflow.retry_count + 1}/{workflow.max_retries})...")

        timeout_sec = workflow.input_payload.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
        return await PipelineRunner.execute_workflow(
            workflow=workflow,
            db=db,
            timeout_seconds=timeout_sec,
        )

    @classmethod
    async def get_workflow(cls, workflow_id: str, db: AsyncSession) -> Optional[WorkflowExecution]:
        """Retrieves a single workflow execution by ID."""
        res = await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == workflow_id))
        return res.scalar_one_or_none()

    @classmethod
    async def list_workflows(
        cls,
        db: AsyncSession,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[WorkflowExecution], int]:
        """Lists workflows with optional status filtering and pagination."""
        query = select(WorkflowExecution)
        count_query = select(func.count(WorkflowExecution.id))

        if status:
            query = query.where(WorkflowExecution.status == status)
            count_query = count_query.where(WorkflowExecution.status == status)

        query = query.order_by(desc(WorkflowExecution.created_at)).offset(offset).limit(limit)

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        workflows_res = await db.execute(query)
        workflows = workflows_res.scalars().all()

        return workflows, total

    @classmethod
    async def get_metrics(cls, db: AsyncSession) -> WorkflowMetricsResponse:
        """Aggregates metrics and state distribution across all workflow runs."""
        all_wf_res = await db.execute(select(WorkflowExecution))
        workflows = all_wf_res.scalars().all()

        total = len(workflows)
        by_status: Dict[str, int] = {}
        total_duration = 0
        completed_count = 0
        failed_count = 0
        disqualified_count = 0
        pending_approval_count = 0
        approved_count = 0
        active_running = 0

        for w in workflows:
            st = w.status
            by_status[st] = by_status.get(st, 0) + 1
            total_duration += w.execution_duration_ms

            if st in [s.value for s in ACTIVE_RUNNING_STATES]:
                active_running += 1
            if st == WorkflowState.COMPLETED.value:
                completed_count += 1
            elif st == WorkflowState.FAILED.value:
                failed_count += 1
            elif st == WorkflowState.REJECTED.value:
                disqualified_count += 1
            elif st == WorkflowState.DRAFT_PENDING_APPROVAL.value:
                pending_approval_count += 1
            elif st == WorkflowState.APPROVED.value:
                approved_count += 1

        avg_dur = (total_duration / total) if total > 0 else 0.0

        return WorkflowMetricsResponse(
            total_workflows=total,
            by_status=by_status,
            completed_count=completed_count,
            failed_count=failed_count,
            disqualified_count=disqualified_count,
            pending_approval_count=pending_approval_count,
            approved_count=approved_count,
            average_duration_ms=round(avg_dur, 1),
            active_running_workflows=active_running,
        )
