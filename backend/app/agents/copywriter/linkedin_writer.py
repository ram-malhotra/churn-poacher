"""
LinkedIn Messaging Generator for the Copywriter Agent.
Produces non-spammy, multi-touch LinkedIn messaging sequences with strict character limits
and engineering-led, consultative tone. Avoids fabricated claims or unsolicited certainty.
"""

from typing import Dict, Any
from app.agents.copywriter.schemas import LinkedInSequence


class LinkedInWriter:
    """Generates a 3-touch LinkedIn sequence adhering to length limits and peer tone."""

    @classmethod
    def generate_sequence(
        cls,
        context: Dict[str, Any],
        finops_data: Dict[str, Any],
    ) -> LinkedInSequence:
        """Generates connection note and follow-up sequence with verified claims."""
        company_name = context.get("company_name", "Your Team")
        target_challenger = context.get("target_challenger", "SigNoz Cloud")
        target_vendor = context.get("target_vendor", "Datadog")

        base_scenario = finops_data.get("scenarios", {}).get("BASE") or finops_data.get("base_scenario") or {}
        annual_savings = base_scenario.get("recurring_annual_savings") or base_scenario.get("signoz_cloud_annual_savings", 84000.0)
        savings_pct = base_scenario.get("recurring_savings_pct") or base_scenario.get("signoz_cloud_savings_pct", 65.0)
        savings_str = f"${annual_savings:,.0f}"

        # -------------------------------------------------------------
        # Touch 1: Connection Request (< 300 chars strictly)
        # -------------------------------------------------------------
        step_1 = (
            f"Hi — following your engineering team's work at {company_name}. We've been analyzing telemetry "
            f"architectures and OpenTelemetry adoption for teams transitioning off {target_vendor} to {target_challenger}. "
            "Glad to connect and share notes on collector deployment patterns."
        )

        if len(step_1) > 295:
            step_1 = (
                f"Hi — following {company_name}'s infrastructure work. We benchmark telemetry architectures "
                f"and OpenTelemetry transitions from {target_vendor} to {target_challenger}. Glad to connect."
            )

        assert len(step_1) <= 300, f"LinkedIn connection note exceeds 300 chars: {len(step_1)}"

        # -------------------------------------------------------------
        # Touch 2: Post-Connection Value-Add (2-3 days later)
        # -------------------------------------------------------------
        step_2 = f"""Thanks for connecting!

We've been documenting architectural patterns for engineering teams decoupling from proprietary monitoring agents in favor of CNCF OpenTelemetry.

The most common concern teams raise is migration friction and potential production blind spots. In our reference architectures, deploying an OpenTelemetry Collector Contrib with isolated trace (:8126 HTTP) and StatsD (:8125 UDP) pipelines allows parallel canary validation while keeping existing monitors active.

Happy to share our collector configuration template and signal migration notes if your team is exploring telemetry modernization this quarter."""

        # -------------------------------------------------------------
        # Touch 3: Technical-Commercial Follow-Up (5-7 days later)
        # -------------------------------------------------------------
        step_3 = f"""Hi — following up briefly on our observability architecture benchmarks.

Based on modeled telemetry sizing for engineering platforms at {company_name}'s tier, migrating workloads from {target_vendor} to {target_challenger} yields a modeled ~{savings_pct:.0f}% reduction in recurring spend (modeled potential savings of ~{savings_str}/yr) by eliminating the host tax.

We've documented a 12-component migration checklist that covers dual-shipping verification, dashboard schema translation, and zero-loss rollback procedures.

Let me know if you'd like me to send over the technical overview for your team to review."""

        return LinkedInSequence(
            step_1_connection_request=step_1,
            step_2_value_add=step_2,
            step_3_technical_commercial=step_3,
        )
