"""
Architecture Migration Agent.
Orchestrates current architecture auditing, OpenTelemetry Collector configuration generation,
YAML structural validation, phased rollout planning, dual-shipping risk analysis,
and rollback risk governance.
"""

from app.models.company import Company
from app.agents.finops_architect.architecture_models import ArchitectureMigrationBlueprint
from app.agents.finops_architect.architecture_analyzer import ArchitectureAnalyzer
from app.agents.finops_architect.otel_generator import OTelCollectorGenerator
from app.agents.finops_architect.migration_planner import MigrationPlanner
from app.agents.finops_architect.rollback_planner import RollbackPlanner


class ArchitectureAgent:
    @classmethod
    async def generate_migration_blueprint(
        cls,
        company: Company,
        target_backend: str = "SigNoz Cloud",
    ) -> ArchitectureMigrationBlueprint:
        """Produces a comprehensive technical architecture migration blueprint with validation."""
        current_arch = ArchitectureAnalyzer.analyze_current_setup(company)
        is_generic = (company.id == "unknown" or company.qualification_status == "REJECTED" or current_arch.evidence_provenance == "UNKNOWN")

        collector_yaml = OTelCollectorGenerator.generate_collector_yaml(
            company_name=company.name,
            target_backend=target_backend,
            enable_dual_shipping=True,
        )
        
        # Run automated YAML validation against OpenTelemetry Collector specification
        yaml_valid, yaml_errors = OTelCollectorGenerator.validate_collector_yaml(collector_yaml)

        # Effort estimates with Low, Base, High scenarios
        is_verified = current_arch.evidence_provenance == "VERIFIED"
        effort = MigrationPlanner.generate_effort_estimate(company.name, is_verified_stack=is_verified)
        dual_risks = MigrationPlanner.generate_dual_shipping_risk_analysis()
        phases = MigrationPlanner.generate_phased_plan(company.name, target_backend)
        rollback = RollbackPlanner.generate_rollback_strategy(company.name, target_backend)

        return ArchitectureMigrationBlueprint(
            company_id=company.id,
            company_name=company.name,
            target_backend=target_backend,
            is_generic_blueprint=is_generic,
            current_architecture=current_arch,
            proposed_target_architecture=(
                f"Dual-shipping OpenTelemetry Collector deployment forwarding telemetry to {target_backend} "
                f"while maintaining parallel feeds to Datadog during the validation window. Signals are segregated "
                f"into distinct trace (:8126 HTTP), metric (:8125 UDP), and log pipelines."
            ),
            opentelemetry_strategy=(
                "Deploy OpenTelemetry Collector Contrib as a Kubernetes DaemonSet or sidecar. Use the Datadog receiver "
                "(:8126 HTTP) for trace translation and the StatsD receiver (:8125 UDP) for DogStatsD metrics, "
                "supplemented by standard OTLP (:4317/:4318) for new application services. Avoid claims of universal zero-code "
                "applicability without evaluating asynchronous tracing or custom metric aggregation requirements."
            ),
            collector_config_yaml=collector_yaml,
            yaml_validation_passed=yaml_valid,
            yaml_validation_errors=yaml_errors,
            dual_shipping_strategy="Multiplexed pipeline routing with isolated sending_queue buffers per remote exporter.",
            dual_shipping_risks=dual_risks,
            effort_estimate=effort,
            data_compatibility_matrix={
                "APM Tracing (HTTP :8126)": "Beta datadog receiver in otelcol-contrib translates dd-trace spans into OTLP.",
                "Custom Metrics (UDP :8125)": "Beta statsd receiver maps DogStatsD gauges, counters, and timers into OTel gauge/sum data points.",
                "Container Logs (/var/log/pods)": "Beta filelog receiver tails and parses container log files from host nodes.",
                "Native OTLP (:4317/:4318)": "Stable standard OpenTelemetry gRPC and HTTP protocol supported natively by SigNoz.",
            },
            phases=phases,
            rollback_plan=rollback,
            downtime_mitigation_and_risks=[
                {
                    "risk": "Telemetry ingestion lag during initial collector spin-up",
                    "mitigation": "Parallel deployment ensures legacy Datadog DaemonSet continues running uninterrupted.",
                },
                {
                    "risk": "Collector memory limits under sudden traffic bursts",
                    "mitigation": "memory_limiter processor configured at 75% hard limit with 20% spike threshold to prevent pod eviction.",
                },
                {
                    "risk": "Doubled data egress bandwidth during dual shipping",
                    "mitigation": "Schedule intensive canary verification during standard business hours and monitor cloud NAT gateway egress.",
                },
                {
                    "risk": "Remote target backend latency or transient rate-limiting",
                    "mitigation": "Isolated sending_queue (5000 items) and retry_on_failure prevents backpressure from impacting Datadog ingestion.",
                },
            ],
            evidence_and_sources=[
                "https://opentelemetry.io/docs/collector/",
                "https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/datadogreceiver",
                "https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/statsdreceiver",
                "https://signoz.io/docs/userguide/opentelemetry-collector/",
            ],
        )
