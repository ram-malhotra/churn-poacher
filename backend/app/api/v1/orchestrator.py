"""
Central Orchestrator API Endpoints.
Provides pipeline execution, workflow status inspection, listing, metrics, and retry controls.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.workflow import WorkflowExecution
from app.agents.orchestrator.orchestrator import CentralOrchestrator
from app.agents.orchestrator.schemas import (
    WorkflowRunRequest,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowMetricsResponse,
    WorkflowRetryRequest,
)
from app.services.objective.objective_interpreter import ObjectiveInterpreter, ObjectiveCriteria

router = APIRouter(tags=["Central Orchestrator"])


class InterpretObjectiveRequest(BaseModel):
    objective: str


def _to_response(w: WorkflowExecution) -> WorkflowResponse:
    """Helper to serialize WorkflowExecution model into WorkflowResponse schema."""
    return WorkflowResponse(
        workflow_id=w.id,
        workflow_type=w.workflow_type,
        status=w.status,
        current_step=w.current_step,
        signal_id=w.signal_id,
        company_id=w.company_id,
        dossier_id=w.dossier_id,
        target_challenger=w.target_challenger,
        retry_count=w.retry_count,
        max_retries=w.max_retries,
        execution_duration_ms=w.execution_duration_ms,
        step_history=w.step_history or [],
        input_payload=w.input_payload or {},
        output_payload=w.output_payload or {},
        error_details=w.error_details,
        is_synthetic=w.is_synthetic,
        created_at=w.created_at.isoformat() if w.created_at else "",
        completed_at=w.completed_at.isoformat() if w.completed_at else None,
    )


# 1. Static Routes (Must be declared before parameterized routes)
@router.post("/orchestrator/interpret-objective", response_model=ObjectiveCriteria)
async def interpret_objective(payload: InterpretObjectiveRequest):
    """
    Translates an unstructured natural-language target opportunity into structured search criteria
    and tailored public source search queries.
    """
    return ObjectiveInterpreter.interpret(payload.objective)


@router.get("/orchestrator/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    status: Optional[str] = Query(None, description="Filter by workflow state (e.g. DRAFT_PENDING_APPROVAL, FAILED)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves paginated list of workflow executions."""
    workflows, total = await CentralOrchestrator.list_workflows(db=db, status=status, limit=limit, offset=offset)
    return WorkflowListResponse(
        total=total,
        workflows=[_to_response(w) for w in workflows],
    )


@router.get("/orchestrator/metrics", response_model=WorkflowMetricsResponse)
async def get_orchestrator_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Returns analytics across all workflow executions."""
    return await CentralOrchestrator.get_metrics(db=db)


# 2. POST /api/v1/orchestrator/run
@router.post("/orchestrator/run", response_model=WorkflowResponse)
async def run_orchestration_pipeline(
    payload: WorkflowRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers an end-to-end multi-agent pipeline execution.
    Prevents concurrent duplicate executions for the same target company or signal.
    """
    try:
        workflow = await CentralOrchestrator.run_pipeline(request=payload, db=db)
        return _to_response(workflow)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Orchestration execution failed: {str(e)}",
        )


# 3. GET /api/v1/orchestrator/status/{workflow_id}
@router.get("/orchestrator/status/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_status(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves execution details, step history, and status for a specific workflow."""
    workflow = await CentralOrchestrator.get_workflow(workflow_id=workflow_id, db=db)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID '{workflow_id}' not found",
        )
    return _to_response(workflow)


# 4. POST /api/v1/orchestrator/retry/{workflow_id}
@router.post("/orchestrator/retry/{workflow_id}", response_model=WorkflowResponse)
async def retry_failed_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retries a FAILED workflow execution from its last failed step."""
    try:
        workflow = await CentralOrchestrator.retry_workflow(workflow_id=workflow_id, db=db)
        return _to_response(workflow)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry workflow: {str(e)}",
        )
