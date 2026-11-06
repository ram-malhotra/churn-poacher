"""
Architecture and Migration Data Models for the Architecture Migration Agent.
Captures audited telemetry components, granular 12-component migration effort estimates,
dual-shipping operational risk analysis, and validated OpenTelemetry Collector configurations.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ArchitectureComponent(BaseModel):
    name: str
    category: str  # Ingestion, Agent, Processor, Storage, UI
    classification: str = "INFERRED"  # VERIFIED, INFERRED, UNKNOWN
    details: str
    component_maturity: str = "Stable"  # Stable, Beta, Alpha


class CurrentArchitectureAssessment(BaseModel):
    """Structured assessment of the enterprise's current telemetry setup."""
    application_services: List[ArchitectureComponent] = Field(default_factory=list)
    kubernetes_environments: List[str] = Field(default_factory=list)
    datadog_agents_detected: bool = False
    evidence_provenance: str = "INFERRED"  # VERIFIED, INFERRED, UNKNOWN
    apm_instrumentation: str = "Datadog dd-trace library (Beta OTel collector receiver)"
    log_collection_method: str = "DaemonSet / filelog tailing"
    metrics_collection_method: str = "dogstatsd UDP :8125 + Prometheus"
    trace_collection_method: str = "Datadog APM Agent (:8126 HTTP)"


class MigrationPhase(BaseModel):
    """Detailed tasks and milestones for one phase of the migration."""
    phase_number: int
    name: str
    duration_days: int
    tasks: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    potential_risks: List[str] = Field(default_factory=list)
    rollback_triggers: List[str] = Field(default_factory=list)


class MigrationEffortItem(BaseModel):
    """Granular effort breakdown for a single migration category."""
    category: str
    description: str
    low_hours: int
    base_hours: int
    high_hours: int
    assumptions: str


class MigrationEffortEstimate(BaseModel):
    """12-component migration effort model with Low, Base, and High scenarios."""
    items: List[MigrationEffortItem] = Field(default_factory=list)
    total_low_hours: int = 120
    total_base_hours: int = 240
    total_high_hours: int = 480
    hourly_rate_usd: float = 125.0
    is_preliminary: bool = True
    estimate_status: str = "PRELIMINARY ESTIMATE — PENDING ARCHITECTURE DISCOVERY"
    methodology_note: str = (
        "Effort estimates represent engineering time across infrastructure, SRE, and application teams. "
        "Scenarios reflect codebase modularity, custom DogStatsD metric complexity, and dashboard density."
    )


class DualShippingRiskAnalysis(BaseModel):
    """Comprehensive technical risk and operational trade-off evaluation for dual shipping."""
    temporary_ingestion_cost_summary: str
    duplicate_telemetry_overhead: str
    sampling_and_retention_differences: str
    cardinality_and_schema_differences: str
    collector_resource_consumption: str
    network_egress_impact: str
    failure_isolation_design: str
    rollback_limitations: str


class RollbackPlan(BaseModel):
    """Concrete operational rollback procedures to mitigate data loss or service degradation."""
    revert_steps: List[str] = Field(default_factory=list)
    data_preservation_strategy: str
    monitoring_and_parity_checks: List[str] = Field(default_factory=list)
    irreversible_actions_warning: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class ArchitectureMigrationBlueprint(BaseModel):
    """Complete migration architecture specification produced by the Architecture Agent."""
    company_id: str
    company_name: str
    target_backend: str = "SigNoz Cloud (OpenTelemetry native)"
    is_generic_blueprint: bool = False
    
    current_architecture: CurrentArchitectureAssessment
    proposed_target_architecture: str
    opentelemetry_strategy: str
    collector_config_yaml: str
    yaml_validation_passed: bool = True
    yaml_validation_errors: List[str] = Field(default_factory=list)
    
    dual_shipping_strategy: str
    dual_shipping_risks: DualShippingRiskAnalysis
    effort_estimate: MigrationEffortEstimate
    
    data_compatibility_matrix: Dict[str, str] = Field(default_factory=dict)
    phases: List[MigrationPhase] = Field(default_factory=list)
    rollback_plan: RollbackPlan
    downtime_mitigation_and_risks: List[Dict[str, str]] = Field(default_factory=list)
    evidence_and_sources: List[str] = Field(default_factory=list)
