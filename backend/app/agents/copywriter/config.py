"""
Configuration and Tone Guidelines for the Copywriter Agent.
Enforces engineering-led, peer-to-peer tone, realistic effort scoping, and anti-spam constraints.
"""

from typing import List, Dict, Any

# Forbidden spammy, sensationalist, or unsubstantiated marketing buzzwords
FORBIDDEN_BUZZWORDS: List[str] = [
    "game-changing",
    "game changing",
    "revolutionary",
    "miracle",
    "silver bullet",
    "rockstar",
    "ninja",
    "10x engineer",
    "unbelievable",
    "insane deal",
    "skyrocket",
    "disruptive magic",
    "secret sauce",
    "no-brainer",
    "growth hack",
    "risk-free",
    "risk free",
    "zero risk",
    "zero downtime guaranteed",
]

# Supported executive personas and their primary focus areas
PERSONA_PROFILES: Dict[str, Dict[str, Any]] = {
    "CTO": {
        "title": "Chief Technology Officer",
        "primary_focus": "Strategic TCO, vendor neutrality, OpenTelemetry standard, multi-year lock-in risk",
        "tone": "Strategic, executive, metric-driven",
        "cta": "15-minute executive architectural review",
    },
    "VP_ENGINEERING": {
        "title": "VP of Engineering",
        "primary_focus": "Developer velocity, minimal migration friction, OpenTelemetry Collector compatibility",
        "tone": "Pragmatic, engineering-focused, risk-conscious",
        "cta": "Technical peer review of the migration blueprint",
    },
    "HEAD_OF_INFRA": {
        "title": "Head of Infrastructure / DevOps Director",
        "primary_focus": "DaemonSet rollout, OpenTelemetry Collector signal pipelines, alert/dashboard parity, ClickHouse performance",
        "tone": "Deeply technical, hands-on, architectural",
        "cta": "Review of the OpenTelemetry Collector YAML and rollout plan",
    },
    "FINOPS_LEAD": {
        "title": "FinOps Lead / Director of Cloud Economics",
        "primary_focus": "Elimination of APM host tax, log re-indexing fees, custom metric overages, 3-year TCO",
        "tone": "Financial, analytical, granular unit economics",
        "cta": "Financial delta and unit-cost comparison session",
    },
}

# Standard enterprise objection catalog with realistic talking points
STANDARD_OBJECTIONS: List[Dict[str, Any]] = [
    {
        "id": "BANDWIDTH",
        "objection": "We don't have the engineering bandwidth for a complex monitoring migration right now.",
        "talking_points": [
            "Infrastructure-layer collector deployment decouples platform setup from application development teams.",
            "Migration effort is partitioned into 12 discrete components across a phased 6-week schedule.",
            "Canarying high-cost services first yields immediate ROI without requiring an all-at-once migration.",
        ],
    },
    {
        "id": "DOWNTIME_RISK",
        "objection": "Switching our core observability vendor risks blind spots and production downtime.",
        "talking_points": [
            "Dual-shipping telemetry architecture maintains incumbent coverage continuously during validation.",
            "Exporter queues have independent backpressure isolation; target hiccups cannot block incumbent ingestion.",
            "Incumbent agents are only decommissioned after 14 days of confirmed alert and metric parity.",
        ],
    },
    {
        "id": "CONTRACT_LOCKIN",
        "objection": "We are locked into an annual contract with our incumbent vendor with several months remaining.",
        "talking_points": [
            "Deploying the OpenTelemetry collector now stops unexpected overages and custom metric spikes immediately.",
            "Validating the alternative 60-90 days prior to contract renewal provides concrete procurement leverage.",
            "Avoids rushed renewal negotiations by having a production-ready alternative tested and approved.",
        ],
    },
    {
        "id": "HISTORICAL_DATA",
        "objection": "We cannot afford to lose our historical metrics, monitors, and custom dashboards.",
        "talking_points": [
            "Datadog monitor JSON definitions translate systematically into PromQL and SigNoz alert rules.",
            "Historical compliance logs can be archived to low-cost cloud storage (S3/GCS) without paying re-indexing fees.",
            "Operational dashboards for Kubernetes and APM map to standardized Grafana / SigNoz community templates.",
        ],
    },
    {
        "id": "SELF_HOSTED_BURDEN",
        "objection": "Managing open source ClickHouse or self-hosted observability creates excessive operational burden.",
        "talking_points": [
            "SigNoz Cloud offers a fully managed enterprise SaaS with 99.9% availability SLAs and automated ClickHouse operations.",
            "Managed cloud pricing retains 40-70% lower TCO than Datadog by charging strictly for ingestion volume without host taxes.",
            "Internal platform engineers never have to provision, shard, or maintain ClickHouse clusters.",
        ],
    },
    {
        "id": "STATUS_QUO",
        "objection": "Datadog works fine for us despite the cost, so why change?",
        "talking_points": [
            "Migration is not universally required; if telemetry spend is under $15k/yr, remaining on Datadog is often optimal.",
            "When infrastructure scales dynamically (Kubernetes pod autoscaling), the per-host tax compounds faster than headcount.",
            "Adopting standard OpenTelemetry protects the company from future proprietary pricing restructuring.",
        ],
    },
    {
        "id": "ROLLBACK_SAFETY",
        "objection": "What happens if the migration fails halfway through?",
        "talking_points": [
            "Tested rollback procedure: disabling the target exporter in collector configuration instantly restores exclusive incumbent routing.",
            "Incumbent agents remain active throughout testing phases, preserving normal operational workflows.",
            "Acknowledge limitation: telemetry recorded only in the target platform cannot be reverse-synchronized into Datadog.",
        ],
    },
]
