"""
Phased Migration Planner and Effort Estimator.
Generates an audited 7-phase migration roadmap and a granular 12-component
engineering effort model with Low, Base, and High scenarios.
"""

from typing import List, Tuple
from app.agents.finops_architect.architecture_models import (
    MigrationPhase,
    MigrationEffortItem,
    MigrationEffortEstimate,
    DualShippingRiskAnalysis,
)


class MigrationPlanner:
    """Plans migration phases, analyzes dual-shipping operational risks, and estimates labor hours."""

    @classmethod
    def generate_effort_estimate(
        cls,
        company_name: str,
        is_verified_stack: bool = False,
    ) -> MigrationEffortEstimate:
        """
        Builds the 12-component migration effort model across Low, Base, and High scenarios.
        """
        items = [
            MigrationEffortItem(
                category="Architecture Discovery",
                description="Audit existing agent DaemonSets, host tags, custom metric namespaces, and service topology.",
                low_hours=8,
                base_hours=16,
                high_hours=32,
                assumptions="Low: Centralized Terraform/GitOps repo; High: Fragmented legacy multi-account deployments.",
            ),
            MigrationEffortItem(
                category="Collector Deployment",
                description="Deploy OpenTelemetry Collector DaemonSet and Gateway cluster with memory limiters and healthchecks.",
                low_hours=12,
                base_hours=20,
                high_hours=40,
                assumptions="Low: Standard EKS/GKE cluster with Helm; High: Hybrid bare-metal and cross-cloud VPC peering.",
            ),
            MigrationEffortItem(
                category="Instrumentation Changes",
                description="Evaluate dd-trace compatibility, configure container env vars (DD_TRACE_AGENT_URL), and stage native OTel SDKs.",
                low_hours=10,
                base_hours=24,
                high_hours=60,
                assumptions="Low: Pure container env redirection without code changes; High: Deep proprietary Datadog custom span tagging.",
            ),
            MigrationEffortItem(
                category="Trace Migration",
                description="Route APM traces to OTel port 8126, validate span hierarchy, trace context propagation, and error rates.",
                low_hours=12,
                base_hours=24,
                high_hours=48,
                assumptions="Low: Uniform HTTP services using W3C/Datadog headers; High: Asynchronous queues (Kafka/RabbitMQ) requiring manual context injection.",
            ),
            MigrationEffortItem(
                category="Metrics Migration",
                description="Configure DogStatsD UDP port 8125 listener, reconcile metric aggregation types, and verify series cardinality.",
                low_hours=16,
                base_hours=32,
                high_hours=64,
                assumptions="Low: Standard system & container metrics; High: Hundreds of custom DogStatsD gauges with high tag cardinality.",
            ),
            MigrationEffortItem(
                category="Log Migration",
                description="Configure filelog receiver or syslog stream, replicate multiline log parsing, JSON extraction, and severity mapping.",
                low_hours=12,
                base_hours=24,
                high_hours=48,
                assumptions="Low: Standard structured JSON stdout logging; High: Unstructured multi-line Java stack traces and legacy syslog sources.",
            ),
            MigrationEffortItem(
                category="Dashboard Migration",
                description="Extract Datadog dashboard definitions and convert widgets/timeseries queries into Grafana / SigNoz schemas.",
                low_hours=16,
                base_hours=36,
                high_hours=72,
                assumptions="Low: 5-10 core operational dashboards; High: 40+ complex dashboards with proprietary math and composite queries.",
            ),
            MigrationEffortItem(
                category="Alert and Monitor Migration",
                description="Translate Datadog monitors (threshold, composite, anomaly) into PromQL / SigNoz alert rules and PagerDuty routes.",
                low_hours=14,
                base_hours=28,
                high_hours=56,
                assumptions="Low: Simple static threshold monitors; High: Complex composite alerts, anomaly monitors, and custom downtime schedules.",
            ),
            MigrationEffortItem(
                category="Historical Data Considerations",
                description="Establish cold storage retention (S3/GCS) for archived compliance logs and document query transition windows.",
                low_hours=4,
                base_hours=10,
                high_hours=20,
                assumptions="Low: Forward-looking telemetry only; High: Strict audit requirement to retain and index 12 months of historical logs.",
            ),
            MigrationEffortItem(
                category="Validation & Parity Auditing",
                description="Execute automated trace span count and metric value parity comparisons between legacy and target platforms.",
                low_hours=10,
                base_hours=20,
                high_hours=40,
                assumptions="Low: Synthetic canary traffic validation; High: High-throughput financial transaction auditing under production peak load.",
            ),
            MigrationEffortItem(
                category="Rollback Testing",
                description="Perform simulated failure chaos drill, verify DNS failback, and validate exporter queue isolation.",
                low_hours=4,
                base_hours=10,
                high_hours=20,
                assumptions="Low: Single-command config rollback in staging; High: Multi-cluster disaster recovery drill across live production tiers.",
            ),
            MigrationEffortItem(
                category="Agent Decommissioning",
                description="Safely scale down and remove legacy Datadog DaemonSets, unmount host volumes, and cancel cloud subscription licenses.",
                low_hours=6,
                base_hours=12,
                high_hours=24,
                assumptions="Low: Automated Helm uninstall; High: Multi-region legacy VM inventory requiring manual agent uninstalls.",
            ),
        ]

        total_low = sum(item.low_hours for item in items)
        total_base = sum(item.base_hours for item in items)
        total_high = sum(item.high_hours for item in items)

        is_preliminary = not is_verified_stack
        status = (
            "AUDITED ESTIMATE — BASED ON REPOSITORY EVIDENCE"
            if is_verified_stack
            else "PRELIMINARY ESTIMATE — PENDING ARCHITECTURE DISCOVERY"
        )

        return MigrationEffortEstimate(
            items=items,
            total_low_hours=total_low,
            total_base_hours=total_base,
            total_high_hours=total_high,
            hourly_rate_usd=125.0,
            is_preliminary=is_preliminary,
            estimate_status=status,
            methodology_note=(
                "Effort estimates represent engineering time across infrastructure, SRE, and application teams. "
                "Assumes a blended engineering rate of $125/hr. If the target enterprise infrastructure complexity "
                "or custom metric volume has not been empirically verified, the estimate is labeled PRELIMINARY."
            ),
        )

    @classmethod
    def generate_dual_shipping_risk_analysis(cls) -> DualShippingRiskAnalysis:
        """
        Produces an evidence-backed operational risk and trade-off analysis for dual shipping.
        Never promises zero downtime, zero data loss, or zero operational risk.
        """
        return DualShippingRiskAnalysis(
            temporary_ingestion_cost_summary=(
                "Dual-shipping incurs simultaneous billing on both the incumbent and target platforms during the 14-30 day "
                "validation window. Running both platforms in parallel adds an estimated 1 month of target-platform ingestion "
                "cost on top of regular operating expenditures."
            ),
            duplicate_telemetry_overhead=(
                "Every application container and node serializes and transmits duplicate spans, metrics, and logs. "
                "In high-throughput environments, this can double node network interface load and require tuning of "
                "Linux socket buffers (net.core.wmem_max) and collector batch sizes."
            ),
            sampling_and_retention_differences=(
                "Datadog uses proprietary client-side and server-side head/adaptive sampling; OpenTelemetry utilizes explicit "
                "head-based or tail-based sampling processors. Absolute trace counts may diverge slightly between platforms, "
                "requiring statistical parity evaluation rather than exact 1-to-1 span matching."
            ),
            cardinality_and_schema_differences=(
                "Datadog organizes tags as unindexed key-value pairs; SigNoz and ClickHouse utilize columnar schema conventions "
                "(OTel Semantic Conventions). High-cardinality tags that cause pricing surges in Datadog must be mapped or "
                "normalized using OTel transform processors before landing in columnar storage."
            ),
            collector_resource_consumption=(
                "Running parallel exporter pipelines doubles collector memory consumption. The memory_limiter processor "
                "must be configured at 75% hard limit with a 20% spike threshold. In high-volume clusters, collector nodes "
                "must be allocated at least 2 cores and 4GB RAM to prevent Out-Of-Memory (OOM) evictions."
            ),
            network_egress_impact=(
                "Forwarding telemetry to two distinct remote endpoints doubles internet egress bandwidth. For cloud environments "
                "(AWS/GCP/Azure), cross-region or internet gateway data egress charges will increase proportionately during the "
                "dual-shipping window."
            ),
            failure_isolation_design=(
                "Each exporter in the OpenTelemetry Collector must be isolated with dedicated sending_queue and retry_on_failure "
                "blocks. If the target backend encounters an outage or rate limit, backpressure must NOT block or drop telemetry "
                "destined for the incumbent platform."
            ),
            rollback_limitations=(
                "Rolling back consists of removing the target exporter from the collector pipeline. However, telemetry "
                "ingested into the target platform during the trial cannot be backfilled or reverse-synchronized into "
                "Datadog. Rollback restores the operational status quo but leaves a split historical record."
            ),
        )

    @classmethod
    def generate_phased_plan(
        cls,
        company_name: str,
        target_backend: str = "SigNoz Cloud",
    ) -> List[MigrationPhase]:
        """Produces a 7-stage phased migration plan with explicit risk governance."""
        return [
            MigrationPhase(
                phase_number=1,
                name="Architecture & Telemetry Discovery",
                duration_days=5,
                tasks=[
                    "Audit existing agent DaemonSets, host tags, and high-cardinality custom metric series.",
                    "Catalog active APM services instrumented with dd-trace and review trace context propagation headers.",
                    "Review Prometheus, DogStatsD UDP, and log tailing configurations.",
                ],
                dependencies=["Read-only access to staging infrastructure and CI/CD pipelines"],
                success_criteria=[
                    "Audited inventory of monitored services, DogStatsD namespaces, and container log paths.",
                ],
                potential_risks=["Undocumented proprietary custom metric sidecars or legacy hardcoded agent endpoints"],
                rollback_triggers=["Discovery reveals proprietary integrations without OpenTelemetry translation support"],
            ),
            MigrationPhase(
                phase_number=2,
                name="Parallel OpenTelemetry Collector Deployment",
                duration_days=5,
                tasks=[
                    "Deploy OTel Collector Contrib DaemonSet/Deployment with separate trace (:8126), metric (:8125), and log pipelines.",
                    "Configure memory_limiter (75% limit, 20% spike) and isolated sending_queue per exporter.",
                    "Deploy health_check extension (:13133) and verify pod readiness probes in staging.",
                ],
                dependencies=["Phase 1 completion"],
                success_criteria=[
                    "Collector pods running healthy across all worker nodes without resource throttling.",
                ],
                potential_risks=["Node memory pressure if worker nodes are undersized"],
                rollback_triggers=["Collector pods experience OOM kills or CPU utilization exceeds 25% on nodes"],
            ),
            MigrationPhase(
                phase_number=3,
                name="Canary Dual-Shipping & Ingestion Verification",
                duration_days=7,
                tasks=[
                    "Configure dual-shipping exporters in collector: routing canary microservice traffic to both platforms.",
                    "Point canary service DD_TRACE_AGENT_URL to local collector port 8126.",
                    "Monitor collector egress bandwidth and verify network socket buffer health under peak hours.",
                ],
                dependencies=["Phase 2 collector deployment verified in staging"],
                success_criteria=[
                    "Canary traces, metrics, and logs visible in both platforms with zero dropped telemetry.",
                ],
                potential_risks=["Temporary dual-ingestion cost and doubled egress network bandwidth on canary nodes"],
                rollback_triggers=["Canary trace drop rate exceeds 0.5% or application response latency degrades > 5ms"],
            ),
            MigrationPhase(
                phase_number=4,
                name="Signal Parity & Dashboard/Alert Recreation",
                duration_days=10,
                tasks=[
                    "Replicate P1/P2 production alerting monitors into PromQL / SigNoz alert rules.",
                    "Convert mission-critical Datadog infrastructure and APM dashboards to Grafana/SigNoz schemas.",
                    "Perform statistical comparison of metric aggregates (P50/P95/P99 latency, error counts) across platforms.",
                ],
                dependencies=["Phase 3 canary stability verified for 7 consecutive days"],
                success_criteria=[
                    "Metric aggregate divergence under 1.0%; P1 alert trigger parity confirmed in dry-run mode.",
                ],
                potential_risks=["Complex composite Datadog monitor formulas requiringPromQL query refactoring"],
                rollback_triggers=["Critical SLA alert cannot be replicated with equivalent sensitivity and trigger latency"],
            ),
            MigrationPhase(
                phase_number=5,
                name="Phased Production Traffic Cutover",
                duration_days=10,
                tasks=[
                    "Stagger production workloads to OTel collector in waves (25% -> 50% -> 100%).",
                    "Maintain incumbent exporter as warm standby safety net during all production cutover waves.",
                    "Verify ClickHouse / target backend ingestion throughput under full production load.",
                ],
                dependencies=["Phase 4 alert parity sign-off by SRE and Engineering Leads"],
                success_criteria=[
                    "100% of production telemetry flowing through OTel collector with zero unhandled drop alerts.",
                ],
                potential_risks=["Sudden volume burst during peak hours causing exporter queue backlog"],
                rollback_triggers=["Target backend exporter queue reaches 80% capacity with retry backoff failures"],
            ),
            MigrationPhase(
                phase_number=6,
                name="Cutover Validation & Incumbent De-commissioning",
                duration_days=5,
                tasks=[
                    "Remove incumbent exporter from collector pipelines, terminating dual ingestion and ending overlap billing.",
                    "Export and archive final historical audit logs to cloud cold storage (S3/GCS bucket).",
                    "Decommission legacy agent DaemonSets and confirm clean node resource recovery.",
                ],
                dependencies=["Phase 5 running stably for 14 days without operational incidents"],
                success_criteria=[
                    "Incumbent billing ceased; zero legacy agent processes remaining on cluster nodes.",
                ],
                potential_risks=["Late discovery of unmigrated peripheral cron jobs or utility scripts"],
                rollback_triggers=["Discovery of unmigrated mission-critical service telemetry"],
            ),
            MigrationPhase(
                phase_number=7,
                name="Post-Migration Telemetry Optimization",
                duration_days=5,
                tasks=[
                    "Optimize OTel batch processor parameters and ClickHouse column compression.",
                    "Audit high-cardinality tags and establish automated telemetry hygiene alerts.",
                    "Finalize engineering team runbooks and train oncall engineers on the new platform.",
                ],
                dependencies=["Phase 6 completion"],
                success_criteria=[
                    "Steady-state target platform run-rate matches financial model within 5% tolerance.",
                ],
                potential_risks=["Engineering team unfamiliarity with PromQL or ClickHouse syntax"],
                rollback_triggers=["None (Migration finalized)"],
            ),
        ]
