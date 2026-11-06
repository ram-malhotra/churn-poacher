"""
LinkedIn Messaging Generator for the Copywriter Agent.
Produces non-spammy, multi-touch LinkedIn messaging sequences with strict character limits
and engineering-led, consultative tone.
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
        """Generates connection note and follow-up sequence."""
        company_name = context["company_name"]
        target_challenger = context["target_challenger"]

        # Financial metrics
        base_scenario = finops_data.get("scenarios", {}).get("BASE") or finops_data.get("base_scenario") or {}
        annual_savings = base_scenario.get("signoz_cloud_annual_savings", 84000.0)
        savings_pct = base_scenario.get("signoz_cloud_savings_pct", 70.0)
        savings_str = f"${annual_savings:,.0f}"

        # -------------------------------------------------------------
        target_vendor = context.get("target_vendor", "Datadog")
        # Touch 1: Connection Request (< 300 chars strictly)
        # -------------------------------------------------------------
        # Keep crisp, respectful, relevant
        step_1 = f"Hi — following your team's work at {company_name}. We've been analyzing telemetry architectures and open standards migrations from {target_vendor} to {target_challenger}. Would love to connect and share insights on dual-shipping patterns."

        # Safety clamp to guarantee under 300 characters
        if len(step_1) > 295:
            step_1 = f"Hi — following {company_name}'s infrastructure work. We benchmark telemetry architectures and open standards transitions from {target_vendor} to {target_challenger}. Glad to connect."

        assert len(step_1) <= 300, f"LinkedIn connection note exceeds 300 chars: {len(step_1)}"

        # -------------------------------------------------------------
        # Touch 2: Post-Connection Value-Add (2-3 days later)
        # -------------------------------------------------------------
        step_2 = f"""Thanks for connecting! 

We recently completed an architectural benchmark analyzing how engineering teams in {context['industry']} are decoupling from proprietary observability agents. 

The biggest challenge teams report is engineering bandwidth and migration risk. We found that deploying an OpenTelemetry collector with a native Datadog trace receiver on port `:8126` allows teams to test parallel pipelines with zero application code changes.

Happy to share our technical notes or collector configuration if your team is exploring open telemetry standards this quarter."""

        # -------------------------------------------------------------
        # Touch 3: Technical-Commercial Follow-Up (5-7 days later)
        # -------------------------------------------------------------
        step_3 = f"""Hi — following up briefly on our observability architecture benchmark.

Based on modeled telemetry profiles for teams at {company_name}'s scale, migrating from Datadog to {target_challenger} typically yields an estimated ~{savings_pct:.0f}% reduction in annual monitoring spend (projected potential savings of ~{savings_str}/yr) by eliminating the host tax.

We've prepared a complete 7-stage dual-shipping blueprint that validates metrics and alerts in parallel before any cutover.

Would you be open to a quick 10-minute peer review of the architecture diagram and financial model?"""

        return LinkedInSequence(
            step_1_connection_request=step_1.strip(),
            step_2_value_add=step_2.strip(),
            step_3_technical_commercial=step_3.strip(),
        )
