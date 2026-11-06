"""
Scenario Analyzer & Sensitivity Model.
Computes low/base/high financial comparisons, temporary dual-shipping overlap costs,
granular migration labor investments, net first-year savings, payback periods,
and 3-year TCO projections using transparent, verifiable formulas.
"""

from typing import Dict, List, Tuple
from app.agents.finops_architect.financial_models import (
    FinancialScenario,
    SensitivityVariable,
    InfrastructureInput,
)
from app.agents.finops_architect.pricing_engine import PricingEngine


class ScenarioAnalyzer:
    HOURLY_ENGINEERING_RATE_USD = 125.0
    OVERLAP_MONTHS = 1.0  # 30-day dual-shipping validation window

    @classmethod
    def analyze_scenarios(
        cls,
        inputs: List[InfrastructureInput],
        is_verified_spend: bool = False,
    ) -> Tuple[Dict[str, FinancialScenario], List[SensitivityVariable]]:
        """Generates LOW, BASE, HIGH scenarios and sensitivity variance rankings."""
        input_map = {item.name: item.value for item in inputs}
        base_hosts = input_map.get("monitored_hosts", 100.0)
        base_apm = input_map.get("apm_hosts", 70.0)
        base_metrics = input_map.get("custom_metrics", 10000.0)
        base_logs = input_map.get("monthly_log_gb", 2500.0)
        base_traces = input_map.get("monthly_trace_gb", 1500.0)

        # Scenario definitions with explicit labor hours and infrastructure scaling
        scenario_configs = {
            "LOW": {
                "mult": 0.65,
                "desc": "Conservative telemetry volume (-35% scale), lower baseline savings, higher operational labor",
                "labor_hours": 140,
                "collector_infra_monthly": 150.0,
            },
            "BASE": {
                "mult": 1.00,
                "desc": "Reasonable baseline telemetry volume and standard migration labor model",
                "labor_hours": 240,
                "collector_infra_monthly": 200.0,
            },
            "HIGH": {
                "mult": 1.50,
                "desc": "Heavy telemetry growth (+50% custom metrics and logs) with full enterprise microservices scope",
                "labor_hours": 450,
                "collector_infra_monthly": 300.0,
            },
        }

        scenarios: Dict[str, FinancialScenario] = {}
        for sc_name, cfg in scenario_configs.items():
            mult = cfg["mult"]
            desc = cfg["desc"]
            hours = cfg["labor_hours"]
            collector_infra_annual = cfg["collector_infra_monthly"] * 12.0

            h = base_hosts * mult
            apm = base_apm * mult
            metrics = base_metrics * mult
            logs = base_logs * mult
            traces = base_traces * mult

            dd = PricingEngine.calculate_datadog(h, apm, metrics, logs, traces)
            signoz_c = PricingEngine.calculate_signoz_cloud(h, apm, metrics, logs, traces)

            current_annual = dd.total_annual_cost
            current_monthly = dd.total_monthly_cost
            target_annual = signoz_c.total_annual_cost
            target_monthly = signoz_c.total_monthly_cost

            # 1. Recurring Annual Savings
            recurring_annual_savings = round(max(0.0, current_annual - target_annual), 2)
            recurring_savings_pct = round(
                (recurring_annual_savings / current_annual * 100.0) if current_annual > 0 else 0.0,
                1,
            )

            # 2. One-Time Migration Investment (Labor + Dual-Shipping Overlap)
            migration_labor_cost = round(hours * cls.HOURLY_ENGINEERING_RATE_USD, 2)
            dual_shipping_overlap_cost = round(target_monthly * cls.OVERLAP_MONTHS, 2)
            total_one_time_investment = round(migration_labor_cost + dual_shipping_overlap_cost, 2)

            # 3. Net First-Year Savings
            # Formula: Recurring Annual Savings - Total One-Time Investment - Additional Collector Infra
            net_first_year_savings = round(
                recurring_annual_savings - total_one_time_investment - collector_infra_annual,
                2,
            )
            first_year_savings_pct = round(
                (net_first_year_savings / current_annual * 100.0) if current_annual > 0 else 0.0,
                1,
            )

            # 4. Payback Period (Months)
            # Formula: Total One-Time Investment / Monthly Recurring Savings Run-Rate
            monthly_savings_runrate = max(1.0, current_monthly - target_monthly)
            payback_months = round(total_one_time_investment / monthly_savings_runrate, 1)

            # 5. Three-Year Total Cost of Ownership (36 Months)
            # Incumbent: 36 months of incumbent run-rate
            # Target: 36 months of target run-rate + 36 months of collector infra + total one-time investment
            tco_incumbent = round(current_annual * 3.0, 2)
            tco_target = round((target_annual * 3.0) + (collector_infra_annual * 3.0) + total_one_time_investment, 2)
            three_year_net_savings = round(tco_incumbent - tco_target, 2)

            scenarios[sc_name] = FinancialScenario(
                scenario_name=sc_name,
                assumptions_description=desc,
                is_verified_spend=is_verified_spend,
                data_label="VERIFIED CUSTOMER EXPENDITURE" if is_verified_spend else "ILLUSTRATIVE MODEL — NOT VERIFIED CUSTOMER SPEND",
                current_annual_spend=current_annual,
                current_monthly_spend=current_monthly,
                target_annual_spend=target_annual,
                target_monthly_spend=target_monthly,
                recurring_annual_savings=recurring_annual_savings,
                recurring_savings_pct=recurring_savings_pct,
                migration_labor_hours=hours,
                migration_labor_cost=migration_labor_cost,
                dual_shipping_overlap_months=cls.OVERLAP_MONTHS,
                dual_shipping_overlap_cost=dual_shipping_overlap_cost,
                additional_infrastructure_annual_cost=collector_infra_annual,
                total_one_time_investment=total_one_time_investment,
                net_first_year_savings=net_first_year_savings,
                first_year_savings_pct=first_year_savings_pct,
                payback_period_months=payback_months,
                three_year_tco_incumbent=tco_incumbent,
                three_year_tco_target=tco_target,
                three_year_net_savings=three_year_net_savings,
                # Backward-compatibility mappings
                current_datadog_monthly=current_monthly,
                current_datadog_annual=current_annual,
                signoz_cloud_monthly=target_monthly,
                signoz_cloud_annual=target_annual,
                signoz_cloud_annual_savings=recurring_annual_savings,
                signoz_cloud_savings_pct=recurring_savings_pct,
                estimated_migration_cost=total_one_time_investment,
                three_year_tco_datadog=tco_incumbent,
                three_year_tco_signoz_cloud=tco_target,
            )

        # Sensitivity Analysis: evaluate variance impact by perturbing single variables by +50%
        base_dd_cost = scenarios["BASE"].current_annual_spend / 12.0
        impact_metrics = PricingEngine.calculate_datadog(base_hosts, base_apm, base_metrics * 1.5, base_logs, base_traces).total_monthly_cost - base_dd_cost
        impact_hosts = PricingEngine.calculate_datadog(base_hosts * 1.5, base_apm * 1.5, base_metrics, base_logs, base_traces).total_monthly_cost - base_dd_cost
        impact_logs = PricingEngine.calculate_datadog(base_hosts, base_apm, base_metrics, base_logs * 1.5, base_traces).total_monthly_cost - base_dd_cost

        sensitivity = [
            SensitivityVariable(
                variable_name="Custom Metrics Surge (+50%)",
                baseline_value=base_metrics,
                tested_range=f"{base_metrics:,.0f} -> {base_metrics * 1.5:,.0f} metrics",
                monthly_impact_usd=round(impact_metrics, 2),
                sensitivity_rank=2,
            ),
            SensitivityVariable(
                variable_name="Host & APM Node Expansion (+50%)",
                baseline_value=base_hosts,
                tested_range=f"{base_hosts:,.0f} -> {base_hosts * 1.5:,.0f} hosts",
                monthly_impact_usd=round(impact_hosts, 2),
                sensitivity_rank=1,
            ),
            SensitivityVariable(
                variable_name="Log Ingestion Burst (+50%)",
                baseline_value=base_logs,
                tested_range=f"{base_logs:,.0f} -> {base_logs * 1.5:,.0f} GB",
                monthly_impact_usd=round(impact_logs, 2),
                sensitivity_rank=3,
            ),
        ]
        sensitivity.sort(key=lambda s: s.monthly_impact_usd, reverse=True)
        for i, s in enumerate(sensitivity, start=1):
            s.sensitivity_rank = i

        return scenarios, sensitivity
