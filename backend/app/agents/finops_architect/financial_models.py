"""
Financial and Pricing Data Models for the FinOps Intelligence Agent.
Captures telemetry volume inputs, granular scenario modeling (LOW, BASE, HIGH),
dual-shipping overlap costs, migration labor investments, net first-year savings,
and 3-year TCO projections with strict provenance labeling.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class PricingEntry(BaseModel):
    """Configurable pricing unit for a monitoring vendor."""
    vendor: str  # Datadog, SigNoz Cloud, SigNoz Self-Hosted, Grafana Cloud, Grafana OSS
    product: str  # Infrastructure, APM, Custom Metrics, Logs, Traces
    billing_unit: str  # per_host_month, per_gb, per_100_metrics, per_million_spans
    unit_price: float
    currency: str = "USD"
    billing_period: str = "MONTHLY"
    pricing_source_url: str
    last_verified_date: str
    pricing_classification: str = "VERIFIED_PUBLIC"  # VERIFIED_PUBLIC, USER_PROVIDED, ESTIMATED, UNKNOWN


class InfrastructureInput(BaseModel):
    """Quantified infrastructure input used for expenditure estimation."""
    name: str
    value: float
    unit: str
    source: str  # ProfileInferred, UserProvided, SignalEvidence, CompanySizeHeuristic
    confidence: float = Field(ge=0.0, le=1.0)
    is_verified: bool = False
    provenance_note: str = "Inferred from public employee tier and corporate indicators"


class PlatformCostBreakdown(BaseModel):
    """Line-item expenditure breakdown for a single platform."""
    platform_name: str
    infrastructure_hosts_cost: float = 0.0
    apm_cost: float = 0.0
    custom_metrics_cost: float = 0.0
    logs_cost: float = 0.0
    traces_cost: float = 0.0
    hosting_and_compute_cost: float = 0.0
    operational_maintenance_cost: float = 0.0
    total_monthly_cost: float = 0.0
    total_annual_cost: float = 0.0
    notes: List[str] = Field(default_factory=list)


class FinancialScenario(BaseModel):
    """Financial delta comparison under a specific telemetry volume scenario."""
    scenario_name: str  # LOW, BASE, HIGH
    assumptions_description: str
    is_verified_spend: bool = False
    data_label: str = "ILLUSTRATIVE MODEL — NOT VERIFIED CUSTOMER SPEND"
    
    # 1. Operating expenditures
    current_annual_spend: float
    current_monthly_spend: float
    target_annual_spend: float
    target_monthly_spend: float
    recurring_annual_savings: float
    recurring_savings_pct: float
    
    # 2. One-time migration & overlap costs
    migration_labor_hours: int = 240
    migration_labor_cost: float = 30000.0
    dual_shipping_overlap_months: float = 1.0
    dual_shipping_overlap_cost: float = 0.0
    additional_infrastructure_annual_cost: float = 2400.0  # Collector cluster compute
    total_one_time_investment: float = 0.0  # labor + overlap
    
    # 3. First-year net financial impact
    net_first_year_savings: float = 0.0
    first_year_savings_pct: float = 0.0
    
    # 4. Multi-year TCO & payback
    payback_period_months: float = 0.0
    three_year_tco_incumbent: float = 0.0
    three_year_tco_target: float = 0.0
    three_year_net_savings: float = 0.0

    # Backward compatibility mappings for legacy UI views & tests
    current_datadog_monthly: float = 0.0
    current_datadog_annual: float = 0.0
    signoz_cloud_monthly: float = 0.0
    signoz_cloud_annual: float = 0.0
    signoz_cloud_annual_savings: float = 0.0
    signoz_cloud_savings_pct: float = 0.0
    estimated_migration_cost: float = 0.0
    three_year_tco_datadog: float = 0.0
    three_year_tco_signoz_cloud: float = 0.0
    three_year_tco_grafana_cloud: float = 0.0


class SensitivityVariable(BaseModel):
    """Impact analysis of a variable on total monthly cost variance."""
    variable_name: str
    baseline_value: float
    tested_range: str
    monthly_impact_usd: float
    sensitivity_rank: int


class FinancialDeltaReport(BaseModel):
    """Complete Financial Delta Matrix produced by the FinOps Intelligence Agent."""
    company_id: str
    company_name: str
    target_challenger: str = "SigNoz"
    is_verified_spend: bool = False
    disclaimer: str = (
        "ILLUSTRATIVE MODEL — NOT VERIFIED CUSTOMER SPEND. All figures are mathematical models "
        "derived from public list pricing and inferred infrastructure sizing. Actual enterprise "
        "expenditure may vary based on negotiated volume discounts and custom commitments."
    )
    
    inputs_used: List[InfrastructureInput] = Field(default_factory=list)
    base_breakdown_datadog: PlatformCostBreakdown
    base_breakdown_signoz_cloud: PlatformCostBreakdown
    base_breakdown_grafana_cloud: PlatformCostBreakdown
    
    scenarios: Dict[str, FinancialScenario] = Field(default_factory=dict)
    sensitivity_analysis: List[SensitivityVariable] = Field(default_factory=list)
    confidence_score: float = Field(default=0.80, ge=0.0, le=1.0)
    data_sources: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)
