"""
Rollback Planner.
Generates documented operational rollback procedures and clearly delineates
architectural limitations of emergency reversions.
"""

from typing import List
from app.agents.finops_architect.architecture_models import RollbackPlan


class RollbackPlanner:
    @classmethod
    def generate_rollback_strategy(
        cls,
        company_name: str,
        target_backend: str = "SigNoz Cloud",
    ) -> RollbackPlan:
        """Produces a structured rollback playbook with explicit operational limitations."""
        return RollbackPlan(
            revert_steps=[
                "Phase 1: Disable target exporter in OTel Collector DaemonSet configmap/helm values.",
                "Phase 2: Perform rolling restart of collector pods; telemetry routes exclusively to incumbent backend.",
                "Phase 3: If collector infrastructure is unstable, revert application DD_TRACE_AGENT_URL back to legacy DaemonSet.",
                "Phase 4: Verify incumbent dashboard reception and alert rule health within 10 minutes of cutback.",
                "Phase 5: Execute post-incident review (PIR) to isolate failure root cause prior to re-attempting rollout.",
            ],
            data_preservation_strategy=(
                "Dual-shipping ensures the incumbent platform continues receiving live telemetry during all validation phases. "
                "In the event of an emergency rollback, the incumbent platform remains fully populated with historical data up "
                "to the moment of reversion."
            ),
            monitoring_and_parity_checks=[
                "Trace ingestion rate (spans/sec) monitored on incumbent agent status endpoints.",
                "Process memory and CPU utilization verified post-reversion.",
                "Sentry / error tracking systems audited for any instrumentation-induced socket exceptions.",
            ],
            irreversible_actions_warning=[
                "Terminating an incumbent contract or deleting custom monitor history is IRREVERSIBLE. Never cancel licenses until 14 days of standalone production operation on the target platform are complete.",
                "Uninstalling legacy agent packages from bare-metal hosts should be deferred until the final decommission phase.",
            ],
            limitations=[
                "Historical telemetry ingested exclusively into the target platform during dual-shipping cannot be backfilled or reverse-synchronized into the incumbent platform.",
                "Alert history, mute configurations, and incident annotations created in the target platform do not sync back.",
                "Rollback requires active incumbent agent licenses; if licenses have already expired, rollback is impossible.",
            ],
        )
