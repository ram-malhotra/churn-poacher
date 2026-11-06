"""
Architecture Analyzer.
Audits the current telemetry footprint of an organization, classifies components
into VERIFIED, INFERRED, and UNKNOWN, and maps OpenTelemetry component maturity levels.
"""

from typing import Dict, Any, List
from app.models.company import Company
from app.agents.finops_architect.architecture_models import (
    CurrentArchitectureAssessment,
    ArchitectureComponent,
)


class ArchitectureAnalyzer:
    @classmethod
    def analyze_current_setup(cls, company: Company) -> CurrentArchitectureAssessment:
        """Constructs an audited assessment of the current telemetry infrastructure."""
        tech_stack = company.tech_stack or {}
        infra = company.infrastructure_indicators or {}
        evidence_records = company.evidence_records or []

        # Check whether Datadog usage is verified in public repos or inferred
        has_verified_dd = any(
            rec.get("classification") == "VERIFIED" and "datadog" in rec.get("claim", "").lower()
            for rec in evidence_records
        )
        has_inferred_dd = any(
            rec.get("classification") == "INFERRED" and "datadog" in rec.get("claim", "").lower()
            for rec in evidence_records
        ) or any(
            "datadog" in str(v).lower()
            for v in (tech_stack.get("monitoring", []) + tech_stack.get("devops", []))
        )

        if has_verified_dd:
            dd_classification = "VERIFIED"
            dd_detected = True
        elif has_inferred_dd:
            dd_classification = "INFERRED"
            dd_detected = True
        else:
            dd_classification = "UNKNOWN"
            dd_detected = False

        components: List[ArchitectureComponent] = [
            ArchitectureComponent(
                name="Datadog APM Ingestion (HTTP :8126)",
                category="Traces",
                classification=dd_classification,
                details="dd-trace libraries emit traces via HTTP to port 8126. OpenTelemetry Collector provides datadogreceiver.",
                component_maturity="Beta",
            ),
            ArchitectureComponent(
                name="DogStatsD Metrics (UDP :8125)",
                category="Metrics",
                classification="INFERRED" if dd_detected else "UNKNOWN",
                details="DogStatsD UDP listener ingests custom gauges, counters, and rate metrics from applications.",
                component_maturity="Beta",
            ),
            ArchitectureComponent(
                name="Container Log Tailing (/var/log/pods)",
                category="Logs",
                classification="INFERRED" if dd_detected else "UNKNOWN",
                details="Container log files collected from Kubernetes host nodes via daemonset filelog receiver.",
                component_maturity="Beta",
            ),
            ArchitectureComponent(
                name="OpenTelemetry Native Ingestion (gRPC :4317 / HTTP :4318)",
                category="Target Standard",
                classification="VERIFIED",
                details="CNCF standard OpenTelemetry Protocol (OTLP) supported natively by SigNoz and modern collectors.",
                component_maturity="Stable",
            ),
        ]

        # Detect Kubernetes / Cloud
        k8s_clusters: List[str] = []
        if "Kubernetes" in tech_stack.get("containers", []) or "k8s_nodes" in infra:
            cloud_name = tech_stack.get("cloud", ["Cloud"])[0] if tech_stack.get("cloud") else "AWS"
            k8s_clusters.append(f"{cloud_name} Managed Kubernetes Production Cluster")
        elif not tech_stack.get("containers"):
            k8s_clusters.append("Standard Containerized / Microservice Environment (Assumed)")

        return CurrentArchitectureAssessment(
            application_services=components,
            kubernetes_environments=k8s_clusters,
            datadog_agents_detected=dd_detected,
            evidence_provenance=dd_classification,
            apm_instrumentation=(
                "Datadog dd-trace library / agent daemon"
                if dd_detected
                else "Unverified / Generic Application Instrumentation"
            ),
            log_collection_method=(
                "Container Log Collector DaemonSet"
                if dd_detected
                else "Standard Container Stdout / Filelog"
            ),
            metrics_collection_method=(
                "dogstatsd UDP :8125 + Prometheus"
                if dd_detected
                else "Prometheus / StatsD Metrics"
            ),
            trace_collection_method=(
                "Datadog APM Agent (:8126 HTTP)"
                if dd_detected
                else "Standard OTLP / Distributed Tracing"
            ),
        )
