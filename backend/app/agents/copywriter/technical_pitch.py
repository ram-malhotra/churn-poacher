"""
Technical Migration Pitch Generator for the Copywriter Agent.
Produces deep-dive technical briefing collateral covering OpenTelemetry architecture,
signal-specific receiver compatibility, component maturity, dual-shipping operational reality,
and dashboard/alert parity.
"""

from typing import Dict, Any
from app.agents.copywriter.schemas import TechnicalMigrationPitch


class TechnicalPitchWriter:
    """Generates an in-depth technical migration document and slide-deck narrative."""

    @classmethod
    def generate_pitch(
        cls,
        context: Dict[str, Any],
        finops_data: Dict[str, Any],
        arch_data: Dict[str, Any],
    ) -> TechnicalMigrationPitch:
        """Generates comprehensive technical migration brief with strict technical accuracy."""
        company_name = context.get("company_name", "Your Team")
        target_challenger = context.get("target_challenger", "SigNoz Cloud")
        challenger_tech = context.get("challenger_tech", "SigNoz Cloud (OpenTelemetry native)")
        target_vendor = context.get("target_vendor", "Datadog")

        base_scenario = finops_data.get("scenarios", {}).get("BASE") or finops_data.get("base_scenario") or {}
        recurring_savings = base_scenario.get("recurring_annual_savings") or base_scenario.get("signoz_cloud_annual_savings", 84000.0)
        savings_pct = base_scenario.get("recurring_savings_pct") or base_scenario.get("signoz_cloud_savings_pct", 65.0)
        net_first_year = base_scenario.get("net_first_year_savings", recurring_savings * 0.6)
        payback_months = base_scenario.get("payback_period_months", 3.2)
        effort_hours = base_scenario.get("migration_labor_hours", 240)
        savings_str = f"${recurring_savings:,.0f}"
        net_yr1_str = f"${net_first_year:,.0f}"

        arch_comparison = {
            "Agent Architecture": f"{target_vendor} uses a proprietary closed-source daemonset; target uses standard CNCF OpenTelemetry Collector Contrib.",
            "Tracing Ingestion": f"Port 8126 (HTTP) provides Beta translation for existing dd-trace spans via collector datadogreceiver; new workloads adopt standard OTLP (port 4317/4318).",
            "Metrics Ingestion": f"Port 8125 (UDP) captures DogStatsD gauges and counters via collector statsdreceiver (Beta); Prometheus metrics ingested natively.",
            "Log Collection": f"Container logs ingested via filelog receiver (Beta) tailing /var/log/pods with multiline parsing; avoids proprietary agent log shippers.",
            "Storage & Economics": f"{target_vendor} levies host taxes, APM host fees, and custom metric overages; target utilizes pure ingestion volume on ClickHouse columnar storage.",
        }

        signal_architecture = (
            "### Signal Ingestion & Protocol Matrix\n\n"
            "An accurate OpenTelemetry migration requires distinct pipeline routing for each telemetry signal:\n\n"
            "1. **Distributed Tracing (Port 8126 HTTP - Beta)**:\n"
            "   Microservices instrumented with `dd-trace` continue emitting traces to `http://<collector>:8126`. "
            "   The OpenTelemetry Collector `datadog` receiver converts spans into OTLP format in-memory. "
            "   *Maturity*: Beta in `opentelemetry-collector-contrib`. Suitable for HTTP services; complex asynchronous "
            "   queue tracing (e.g. Kafka headers) should be validated during canary testing.\n\n"
            "2. **Custom Metrics (Port 8125 UDP - Beta)**:\n"
            "   DogStatsD metrics cannot be ingested on port 8126. A dedicated `statsd` receiver on UDP port `8125` "
            "   aggregates application counters and gauges, mapping them into standard OpenTelemetry metric data points.\n\n"
            "3. **Container Logs (/var/log/pods - Beta)**:\n"
            "   Container stdout/stderr is collected via the `filelog` receiver mounted to `/var/log/pods` as a DaemonSet. "
            "   Regex and JSON operators parse structured logs before batch export.\n\n"
            "4. **Native OTLP (Ports 4317 gRPC / 4318 HTTP - Stable)**:\n"
            "   Any new greenfield services or refactored workloads emit standard OTLP directly to the collector, "
            "   achieving full vendor neutrality.\n\n"
            "```yaml\n"
            "# OpenTelemetry Collector Ingestion Architecture\n"
            "receivers:\n"
            "  datadog:\n"
            "    endpoint: 0.0.0.0:8126\n"
            "  statsd:\n"
            "    endpoint: 0.0.0.0:8125\n"
            "exporters:\n"
            "  otlp/signoz:\n"
            "    endpoint: ingest.us.signoz.cloud:443\n"
            "```\n"
        )

        dual_shipping = (
            "### Dual-Shipping Operational Reality & Risk Governance\n\n"
            "Dual shipping provides essential verification, but is NOT without operational trade-offs:\n"
            "- **Temporary Ingestion Overlap**: Both platforms ingest telemetry simultaneously during the 14-30 day "
            "  validation window, incurring temporary double-ingestion costs modeled at ~1 month of target spend.\n"
            "- **Collector Resource Governance**: Collector pods must enforce a `memory_limiter` processor at 75% limit "
            "  with a 20% spike threshold. In high-volume clusters, allocate 2 CPU cores and 4GB RAM per collector pod.\n"
            "- **Network Egress Impact**: Multiplexing telemetry doubles outbound data egress. Egress should be monitored "
            "  on NAT gateways during peak traffic.\n"
            "- **Failure Isolation**: Dedicated `sending_queue` (5,000 items) and exponential `retry_on_failure` policies "
            f"  guarantee that target network blips never induce backpressure or dropped spans on {target_vendor}.\n"
            "- **Rollback Limitations**: Disabling the target exporter immediately restores exclusive legacy routing, "
            f"  but data stored only in the target platform cannot be backfilled into {target_vendor}.\n"
        )

        parity = (
            "### Parity Verification & Telemetry Migration\n\n"
            "1. **Monitors & Alerts**: Incumbent monitor definitions are extracted via API and translated to PromQL / "
            "   SigNoz alert rules. Staged dry-runs verify identical threshold firing.\n"
            "2. **Dashboards**: Core Kubernetes and APM dashboards are imported using standard community Grafana / SigNoz "
            "   templates, decoupling visualization from proprietary widget schemas.\n"
            "3. **Historical Logs**: Active live logs transition forward into the new platform, while historical audit "
            "   records remain accessible in cold object storage (S3/GCS Glacier) without ongoing indexing costs.\n"
        )

        timeline = (
            "### Phased Migration Roadmap & Scoped Labor\n\n"
            f"Migration is organized into 12 discrete engineering components across 7 phases, requiring a "
            f"modeled investment of approximately **{effort_hours} engineering hours** (Base Scenario):\n"
            "- Phase 1: Architecture Discovery & Footprint Audit (5 days)\n"
            "- Phase 2: OpenTelemetry Collector Contrib Deployment (5 days)\n"
            "- Phase 3: Canary Dual-Shipping & Ingestion Verification (7 days)\n"
            "- Phase 4: Signal Parity & Alert/Dashboard Translation (10 days)\n"
            "- Phase 5: Phased Production Cutover in Canary Waves (10 days)\n"
            "- Phase 6: Cutover Validation & Incumbent De-commissioning (5 days)\n"
            "- Phase 7: Post-Migration Optimization & Team Runbooks (5 days)\n\n"
            f"Modeled Financial Impact: **{savings_str}/year** in recurring run-rate reduction, yielding an estimated "
            f"**{net_yr1_str}** in net first-year savings after fully accounting for migration labor and dual-shipping overlap."
        )

        full_pitch = f"""# OpenTelemetry Technical Migration Blueprint: {company_name}
**Target Backend**: {challenger_tech} | **Incumbent Target**: {target_vendor}
*Disclaimer: Technical specifications reflect OpenTelemetry Collector Contrib v0.100+ architecture.*

---
{signal_architecture}

---
{dual_shipping}

---
{parity}

---
{timeline}
"""

        return TechnicalMigrationPitch(
            title=f"OpenTelemetry Technical Migration Blueprint: {company_name}",
            target_audience="CTO, VP Engineering, Head of Infrastructure",
            architecture_comparison=arch_comparison,
            zero_code_migration_path=signal_architecture,
            dual_shipping_poc=dual_shipping,
            alert_and_dashboard_parity=parity,
            timeline_and_effort=timeline,
            full_pitch_markdown=full_pitch,
        )
