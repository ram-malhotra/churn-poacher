"""
Personalization Engine for the Copywriter Agent.
Adapts messaging context, pain points, and technical depth based on target persona,
signal distress category, company scale, and chosen competitor alternative.
"""

from typing import Dict, Any


class PersonalizationEngine:
    """Adapts tone, hooks, and technical depth to the prospect's context."""

    @classmethod
    def get_context(
        cls,
        company_data: Dict[str, Any],
        signal_data: Dict[str, Any],
        target_challenger: str = "SigNoz Cloud",
        target_vendor: str = "Datadog",
    ) -> Dict[str, Any]:
        """Derives dynamic contextual hooks and phrasing guidelines."""
        complaint_cat = (signal_data.get("complaint_category") or "GENERAL_DISCUSSION").upper()
        estimated_size = company_data.get("estimated_size") or "50-250 employees"
        industry = company_data.get("industry") or "Technology"
        company_name = company_data.get("name") or "Your Team"
        vendor = target_vendor or "Datadog"

        # Determine distress hook
        if "PRICING" in complaint_cat or "BILLING" in complaint_cat:
            hook_headline = f"Eliminating the {vendor} License Tax & Predictable Unit Economics"
            primary_pain = f"unpredictable monthly overages and the compounding {vendor} licensing tax"
            strategic_solution = "an ingestion-only pricing model with zero vendor penalties and no custom metric tax"
            distress_tag = "BILLING_SHOCK"
        elif "OUTAGE" in complaint_cat or "RELIABILITY" in complaint_cat:
            hook_headline = f"Architectural Resilience & Zero-Blackout Observability Beyond {vendor}"
            primary_pain = f"recent {vendor} outages creating blind spots during critical production workloads"
            strategic_solution = "an OpenTelemetry-native architecture with multi-region ingestion and full data ownership"
            distress_tag = "OUTAGE"
        elif "MIGRATION" in complaint_cat or "DEPRECATION" in complaint_cat:
            hook_headline = f"Seamless Migration from {vendor} to Vendor-Neutral OpenTelemetry"
            primary_pain = f"engineering friction and high switching costs when migrating off {vendor}"
            strategic_solution = f"zero-code collector compatibility and a validated dual-shipping rollout from {vendor}"
            distress_tag = "MIGRATION_INTENT"
        else:
            hook_headline = f"Modernizing from {vendor} to Vendor-Neutral OpenTelemetry Standards"
            primary_pain = f"proprietary {vendor} lock-in and high total cost of ownership on legacy monitoring"
            strategic_solution = "CNCF OpenTelemetry standard with direct compatibility"
            distress_tag = "GENERAL_DISCUSSION"

        # Challenger advantages
        is_grafana = "grafana" in target_challenger.lower()
        if is_grafana:
            challenger_tech = "Grafana Cloud (Mimir, Loki, Tempo)"
            backend_benefit = "battle-tested Prometheus/PromQL and Loki pipelines with unified Grafana dashboards"
        else:
            challenger_tech = "SigNoz Cloud (OpenTelemetry native)"
            backend_benefit = "single-pane traces, metrics, and logs powered by a high-performance ClickHouse columnar backend"

        return {
            "company_name": company_name,
            "industry": industry,
            "estimated_size": estimated_size,
            "distress_tag": distress_tag,
            "hook_headline": hook_headline,
            "primary_pain": primary_pain,
            "strategic_solution": strategic_solution,
            "target_challenger": target_challenger,
            "challenger_tech": challenger_tech,
            "backend_benefit": backend_benefit,
            "target_vendor": vendor,
        }
