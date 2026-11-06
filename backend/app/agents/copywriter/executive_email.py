"""
Executive Email Generator for the Copywriter Agent.
Produces tailored, high-converting B2B emails for CTOs, VPs of Engineering,
and Heads of Infrastructure without spammy tropes or creepy tracking language.
"""

from typing import List, Dict, Any
from app.agents.copywriter.schemas import EmailVariant


class ExecutiveEmailWriter:
    """Generates concise executive and detailed technical-commercial email collateral."""

    @classmethod
    def generate_variants(
        cls,
        context: Dict[str, Any],
        finops_data: Dict[str, Any],
        arch_data: Dict[str, Any],
    ) -> List[EmailVariant]:
        """Generates both Executive Concise and Technical-Commercial email variants."""
        company_name = context["company_name"]
        target_challenger = context["target_challenger"]
        challenger_tech = context["challenger_tech"]
        primary_pain = context["primary_pain"]
        strategic_solution = context["strategic_solution"]

        # Financial metrics
        base_scenario = finops_data.get("scenarios", {}).get("BASE") or finops_data.get("base_scenario") or {}
        datadog_annual = base_scenario.get("current_datadog_annual", 120000.0)
        target_annual = base_scenario.get("signoz_cloud_annual", 36000.0)
        annual_savings = base_scenario.get("signoz_cloud_annual_savings", 84000.0)
        savings_pct = base_scenario.get("signoz_cloud_savings_pct", 70.0)
        payback_months = base_scenario.get("payback_period_months", 1.8)

        # Format dollar amounts cleanly
        savings_str = f"${annual_savings:,.0f}"
        datadog_str = f"${datadog_annual:,.0f}"
        target_str = f"${target_annual:,.0f}"

        # -------------------------------------------------------------
        # Variant 1: Executive Concise (CTO / VP Engineering)
        # -------------------------------------------------------------
        exec_subject_lines = [
            f"{company_name}: modeled {savings_pct:.0f}% reduction in observability spend via OpenTelemetry",
            f"OpenTelemetry migration blueprint for {company_name} (zero-code :8126 receiver)",
            f"Benchmarking {company_name}'s telemetry run-rate vs {target_challenger}",
        ]

        target_vendor = context.get("target_vendor", "Datadog")
        exec_preheader = f"Modeled potential savings of ~{savings_str}/year by migrating from {target_vendor} to {target_challenger}."

        exec_body = f"""Hi Team,

In our engineering work benchmarking observability architectures for scaling {context['industry'].lower()} infrastructure, we frequently encounter teams grappling with {primary_pain}.

Based on typical infrastructure profiles in your tier, our telemetry FinOps model indicates {company_name} could realize an **estimated {savings_pct:.0f}% annual savings (~{savings_str}/yr)** by transitioning monitoring workloads from {target_vendor} to **{challenger_tech}**.

Three technical pillars make this feasible without operational disruption:
1. **Zero-Code Agent Ingestion**: The OpenTelemetry Collector includes a native Datadog trace receiver on port `:8126`, ingesting existing `dd-trace` traffic with zero application code rewrites.
2. **Risk-Free Dual-Shipping**: Both backends receive mirrored telemetry during validation, guaranteeing continuous coverage until full parity is verified.
3. **Payback in ~{payback_months:.1f} Months**: Total engineering migration investment is recouped within the first quarter of deployment.

Would you or your infrastructure lead be open to a 15-minute peer review of our OpenTelemetry migration blueprint and financial delta model?

Best regards,  
The Engineering Team
"""

        variant_executive = EmailVariant(
            variant_type="EXECUTIVE_CONCISE",
            target_role="CTO / VP Engineering",
            subject_lines=exec_subject_lines,
            preheader=exec_preheader,
            body_markdown=exec_body.strip(),
            call_to_action="15-minute technical peer review of the OpenTelemetry migration blueprint",
            referenced_attachments=[
                f"Financial Delta Matrix ({savings_str}/yr estimated savings)",
                "OpenTelemetry Collector Dual-Shipping Architecture YAML",
            ],
        )

        # -------------------------------------------------------------
        # Variant 2: Technical-Commercial (Head of Infra / DevOps / FinOps)
        # -------------------------------------------------------------
        tech_subject_lines = [
            f"Technical architecture: dual-shipping OTel collector for {company_name}",
            f"{company_name} FinOps breakdown: eliminating Datadog host tax (~{savings_str}/yr)",
            f"Datadog agent receiver (:8126) -> {target_challenger} migration plan",
        ]

        tech_preheader = f"Detailed architectural plan for dual-shipping telemetry and saving an estimated {savings_str}/year."

        tech_body = f"""Hi Team,

I put together an architectural evaluation for {company_name} comparing your current Datadog telemetry pipeline against modern OpenTelemetry standards running on **{challenger_tech}**.

### 1. Financial Delta Overview (Base Scenario)
- **Estimated Current Datadog Spend**: ~{datadog_str}/yr (driven heavily by host-based fees and custom metric indexing)
- **Projected {target_challenger} Spend**: ~{target_str}/yr (purely usage/ingestion-based)
- **Net Modeled Savings**: **~{savings_str}/year ({savings_pct:.0f}% reduction)**
- **Estimated Payback Period**: **~{payback_months:.1f} months**

### 2. Zero-Disruption Dual-Shipping Blueprint
To avoid migration risk, we use a 7-phase dual-shipping strategy:
- Deploy an OpenTelemetry Collector DaemonSet configured with a Datadog-compatible receiver (`receiver: datadog: endpoint: 0.0.0.0:8126`).
- Applications continue emitting traces/metrics without SDK changes or rebuilds.
- Telemetry is simultaneously exported to Datadog and {target_challenger}.
- Alert and dashboard parity is validated across parallel environments before decommission.
- Automated rollback capability ensures zero risk of telemetry gaps.

We have compiled the complete OpenTelemetry Collector configuration YAML and 7-stage rollout schedule.

Would you be open to a 20-minute architecture review to walk through the collector pipeline and verify our assumptions?

Best regards,  
The Infrastructure Architecture Team
"""

        variant_technical = EmailVariant(
            variant_type="TECHNICAL_COMMERCIAL",
            target_role="Head of Infrastructure / DevOps / FinOps Lead",
            subject_lines=tech_subject_lines,
            preheader=tech_preheader,
            body_markdown=tech_body.strip(),
            call_to_action="20-minute architecture walkthrough of the OpenTelemetry collector configuration",
            referenced_attachments=[
                f"Financial Delta Matrix (Estimated annual savings: {savings_str})",
                "OpenTelemetry Collector Production YAML Configuration",
                "7-Phase Zero-Downtime Migration Blueprint",
            ],
        )

        return [variant_executive, variant_technical]
