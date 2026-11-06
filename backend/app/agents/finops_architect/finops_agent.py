"""
FinOps Intelligence Agent.
Orchestrates infrastructure cost estimation, competitive pricing calculations,
scenario modeling (LOW, BASE, HIGH), and Financial Delta Matrix synthesis with strict
factual provenance tracking and disclaimer governance.
"""

from typing import Dict, Any, Optional
from app.models.company import Company
from app.models.signal import Signal
from app.agents.finops_architect.financial_models import FinancialDeltaReport
from app.agents.finops_architect.cost_estimator import CostEstimator
from app.agents.finops_architect.pricing_engine import PricingEngine
from app.agents.finops_architect.scenario_analyzer import ScenarioAnalyzer


class FinOpsAgent:
    """Calculates granular, transparent financial comparisons against Datadog."""

    @classmethod
    async def generate_financial_analysis(
        cls,
        company: Company,
        signal: Optional[Signal] = None,
    ) -> FinancialDeltaReport:
        """Produces a complete Financial Delta Report with low/base/high scenarios."""
        # 1. Check whether we have empirically verified Datadog spend
        evidence_records = company.evidence_records or []
        is_verified_spend = any(
            rec.get("classification") == "VERIFIED" and "spend" in rec.get("claim", "").lower()
            for rec in evidence_records
        )

        # 2. Derive Telemetry Inputs
        inputs = CostEstimator.derive_telemetry_inputs(
            estimated_size=company.estimated_size or "50-250 employees",
            infrastructure_indicators=company.infrastructure_indicators or {},
            extracted_evidence=signal.extracted_evidence if signal else {},
        )
        input_map = {item.name: item.value for item in inputs}
        hosts = input_map.get("monitored_hosts", 100.0)
        apm = input_map.get("apm_hosts", 70.0)
        metrics = input_map.get("custom_metrics", 10000.0)
        logs = input_map.get("monthly_log_gb", 2500.0)
        traces = input_map.get("monthly_trace_gb", 1500.0)

        # 3. Base Platform Breakdowns
        dd_base = PricingEngine.calculate_datadog(hosts, apm, metrics, logs, traces)
        signoz_base = PricingEngine.calculate_signoz_cloud(hosts, apm, metrics, logs, traces)
        grafana_base = PricingEngine.calculate_grafana_cloud(hosts, apm, metrics, logs, traces)

        # 4. Scenario & Sensitivity Analysis (LOW, BASE, HIGH with dual-shipping overlap & labor)
        scenarios, sensitivity = ScenarioAnalyzer.analyze_scenarios(
            inputs,
            is_verified_spend=is_verified_spend,
        )

        confidence = 0.90 if is_verified_spend else 0.75

        # 5. Compile Structured Report
        return FinancialDeltaReport(
            company_id=company.id,
            company_name=company.name,
            target_challenger="SigNoz",
            is_verified_spend=is_verified_spend,
            disclaimer=(
                "VERIFIED CUSTOMER EXPENDITURE: Figures reflect confirmed telemetry spend evidence."
                if is_verified_spend
                else "ILLUSTRATIVE MODEL — NOT VERIFIED CUSTOMER SPEND. All figures are mathematical models "
                "derived from public list pricing and inferred infrastructure sizing. Actual enterprise "
                "expenditure may vary based on negotiated volume discounts and custom commitments."
            ),
            inputs_used=inputs,
            base_breakdown_datadog=dd_base,
            base_breakdown_signoz_cloud=signoz_base,
            base_breakdown_grafana_cloud=grafana_base,
            scenarios=scenarios,
            sensitivity_analysis=sensitivity,
            confidence_score=confidence,
            data_sources=[
                "https://www.datadoghq.com/pricing/",
                "https://signoz.io/pricing/",
                "https://grafana.com/pricing/",
            ],
            caveats=[
                "Estimates assume standard public published list pricing; does not reflect undisclosed enterprise volume discounts.",
                "Dual-shipping introduces a temporary 14-30 day overlap cost where both platforms ingest telemetry simultaneously.",
                "Migration labor costs assume a blended engineering rate of $125/hr across SRE and platform teams.",
                "Actual customer network egress, custom retention tiers, and cold storage indexing will influence net figures.",
            ],
        )
