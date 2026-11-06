"""
Value Proposition and Financial Case Generator for the Copywriter Agent.
Produces executive-ready 1-page business cases, transparent multi-year TCO modeling,
first-year net savings calculations, and the incumbent pricing tax breakdown.
"""

from typing import Dict, Any
from app.agents.copywriter.schemas import ValuePropositionSummary


class ValuePropositionWriter:
    """Generates a structured financial business case and transparent TCO comparison."""

    @classmethod
    def generate_value_proposition(
        cls,
        context: Dict[str, Any],
        finops_data: Dict[str, Any],
    ) -> ValuePropositionSummary:
        """Generates the 1-page financial business case with explicit formulas and disclaimers."""
        company_name = context.get("company_name", "Your Team")
        target_challenger = context.get("target_challenger", "SigNoz Cloud")
        target_vendor = context.get("target_vendor", "Datadog")

        base_scenario = finops_data.get("scenarios", {}).get("BASE") or finops_data.get("base_scenario") or {}
        is_verified = base_scenario.get("is_verified_spend", False)
        data_label = "VERIFIED CUSTOMER EXPENDITURE" if is_verified else "ILLUSTRATIVE MODEL — NOT VERIFIED CUSTOMER SPEND"

        current_annual = base_scenario.get("current_annual_spend") or base_scenario.get("current_datadog_annual", 120000.0)
        target_annual = base_scenario.get("target_annual_spend") or base_scenario.get("signoz_cloud_annual", 36000.0)
        recurring_savings = base_scenario.get("recurring_annual_savings") or base_scenario.get("signoz_cloud_annual_savings", 84000.0)
        savings_pct = base_scenario.get("recurring_savings_pct") or base_scenario.get("signoz_cloud_savings_pct", 70.0)
        
        labor_cost = base_scenario.get("migration_labor_cost", 30000.0)
        overlap_cost = base_scenario.get("dual_shipping_overlap_cost", 3000.0)
        total_one_time = base_scenario.get("total_one_time_investment", labor_cost + overlap_cost)
        net_first_year = base_scenario.get("net_first_year_savings", recurring_savings - total_one_time)
        first_year_pct = base_scenario.get("first_year_savings_pct", 42.0)
        payback_months = base_scenario.get("payback_period_months", 3.8)

        three_year_incumbent = base_scenario.get("three_year_tco_incumbent") or base_scenario.get("three_year_tco_datadog", current_annual * 3.0)
        three_year_target = base_scenario.get("three_year_tco_target") or base_scenario.get("three_year_tco_signoz_cloud", (target_annual * 3.0) + total_one_time)
        three_year_net_savings = base_scenario.get("three_year_net_savings", three_year_incumbent - three_year_target)

        curr_str = f"${current_annual:,.0f}"
        target_str = f"${target_annual:,.0f}"
        recurring_str = f"${recurring_savings:,.0f}"
        labor_str = f"${labor_cost:,.0f}"
        overlap_str = f"${overlap_cost:,.0f}"
        net_yr1_str = f"${net_first_year:,.0f}"
        tco_inc_str = f"${three_year_incumbent:,.0f}"
        tco_target_str = f"${three_year_target:,.0f}"
        tco_net_str = f"${three_year_net_savings:,.0f}"

        tax_breakdown = {
            "Infrastructure Host Tax": f"{target_vendor} charges per host regardless of node density, penalizing modern auto-scaled Kubernetes workloads.",
            "APM Host Multiplier": f"Levies compounding per-host APM charges even when only a subset of services require distributed tracing.",
            "Custom Metrics Overages": f"Overages billed aggressively ($5/100 metrics) when ephemeral pod tags or dynamic microservice labels spike.",
            "Log Indexing & Retention Multipliers": "Separate ingestion fees plus daily indexing retention surcharges create unpredictable monthly billing volatility.",
        }

        risk_reward = [
            {
                "Dimension": "Annual Steady-State Run-Rate",
                "Status Quo (Incumbent)": f"{curr_str}/year (Compounding with host & pod scaling)",
                "Migration Target": f"{target_str}/year (Purely ingestion volume-based)",
            },
            {
                "Dimension": "First-Year Net Financial Return",
                "Status Quo (Incumbent)": "$0 net savings (Continued overage exposure)",
                "Migration Target": f"{net_yr1_str} net savings (After {labor_str} labor & {overlap_str} overlap cost)",
            },
            {
                "Dimension": "Payback Period",
                "Status Quo (Incumbent)": "N/A",
                "Migration Target": f"~{payback_months:.1f} months to full ROI recovery",
            },
            {
                "Dimension": "Three-Year Total Cost of Ownership",
                "Status Quo (Incumbent)": f"{tco_inc_str} cumulative 3-year expenditure",
                "Migration Target": f"{tco_target_str} cumulative (Net 3-year savings: {tco_net_str})",
            },
        ]

        full_value_prop = f"""# Executive Financial Business Case: {company_name}
**Data Label**: `{data_label}`
*Transparent financial analysis comparing {target_vendor} vs {target_challenger}*

---
### 1. Transparent Financial Summary & First-Year Net Impact
- **Estimated Current Annual Spend ({target_vendor})**: {curr_str}/yr
- **Estimated Alternative Annual Spend ({target_challenger})**: {target_str}/yr
- **Gross Recurring Annual Savings**: **{recurring_str}/yr** ({savings_pct:.0f}% reduction)
- **One-Time Migration Labor Investment**: {labor_str} (Modeled across 12 discrete engineering components)
- **Temporary Dual-Shipping Overlap Cost**: {overlap_str} (~30-day parallel validation window)
- **Net First-Year Savings**: **{net_yr1_str}** ({first_year_pct:.0f}% first-year net reduction)
- **Modeled Payback Period**: **{payback_months:.1f} months**

---
### 2. Three-Year Total Cost of Ownership (TCO)
- **Status Quo Cumulative 3-Year TCO**: {tco_inc_str}
- **Target Platform Cumulative 3-Year TCO**: {tco_target_str} (includes all labor, overlap, and collector compute)
- **Net Three-Year Cumulative Savings**: **{tco_net_str}**

---
### 3. Root Causes of Incumbent Cost Volatility
1. **The Host Tax**: In Kubernetes and microservice environments, node count scales horizontally with ephemeral compute, multiplying host fees artificially.
2. **Custom Metric Penalties**: Automated container deployments create high-cardinality series that trigger expensive tier overages.
3. **Log Ingestion & Index Surcharges**: Proprietary vendors bill separately for log ingestion and indexed retention, causing unpredictable budget shocks during traffic surges.

---
### 4. Strategic Risk vs. Reward Analysis
- **Operational Disruption**: Mitigated via parallel canary dual-shipping with isolated queues and automated parity checks.
- **Commercial Return**: Modeled payback period of {payback_months:.1f} months yielding net first-year savings of {net_yr1_str}.
"""

        return ValuePropositionSummary(
            executive_summary=f"Financial analysis comparing {target_vendor} vs {target_challenger} for {company_name}",
            current_estimated_runrate_annual=current_annual,
            target_alternative_runrate_annual=target_annual,
            annual_savings_usd=recurring_savings,
            savings_percentage=savings_pct,
            datadog_tax_breakdown=tax_breakdown,
            tco_payback_period_months=payback_months,
            three_year_net_savings_usd=three_year_net_savings,
            risk_vs_reward=risk_reward,
            full_value_prop_markdown=full_value_prop,
        )
