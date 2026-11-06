"""
Data Schemas for Central Orchestrator.
Includes workflow run requests, step transition records, metrics, and retry requests.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class WorkflowRunRequest(BaseModel):
    """Payload to trigger an orchestrated pipeline run."""
    objective: Optional[str] = Field(None, description="Natural language target opportunity description")
    monitoring_mode: str = Field("ON_DEMAND", description="Execution mode: ON_DEMAND or SCHEDULED")
    signal_id: Optional[str] = Field(None, description="Optional target signal ID to process")
    company_id: Optional[str] = Field(None, description="Optional target company ID to process downstream")
    target_challenger: str = Field("SigNoz Cloud", description="Target alternative: SigNoz Cloud or Grafana Cloud")
    include_synthetic: bool = Field(True, description="Whether to include synthetic demo signals if listener runs")
    max_retries: int = Field(3, ge=1, le=5, description="Maximum retry attempts on transient step failure")
    timeout_seconds: int = Field(60, ge=5, le=300, description="Per-workflow timeout limit in seconds")
    async_worker: bool = Field(False, description="Enqueue workflow task to persistent Redis background worker queue")


class WorkflowStepRecord(BaseModel):
    """Execution details for an individual workflow step."""
    step_name: str
    status: str  # STARTED, SUCCESS, FAILED, SKIPPED, DISQUALIFIED
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: int = 0
    details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class WorkflowResponse(BaseModel):
    """Full workflow execution record representation."""
    workflow_id: str
    workflow_type: str
    status: str
    current_step: str
    signal_id: Optional[str] = None
    company_id: Optional[str] = None
    dossier_id: Optional[str] = None
    target_challenger: str
    retry_count: int
    max_retries: int
    execution_duration_ms: int
    step_history: List[Dict[str, Any]] = Field(default_factory=list)
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    output_payload: Dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[str] = None
    is_synthetic: bool
    created_at: str
    completed_at: Optional[str] = None


class WorkflowListResponse(BaseModel):
    """Paginated list of workflow executions."""
    total: int
    workflows: List[WorkflowResponse]


class WorkflowMetricsResponse(BaseModel):
    """High-level execution statistics across all orchestrated workflows."""
    total_workflows: int
    by_status: Dict[str, int]
    completed_count: int
    failed_count: int
    disqualified_count: int
    pending_approval_count: int
    approved_count: int
    average_duration_ms: float
    active_running_workflows: int


class WorkflowRetryRequest(BaseModel):
    """Payload to retry a failed workflow from its point of failure."""
    max_retries_override: Optional[int] = Field(None, ge=1, le=5)
