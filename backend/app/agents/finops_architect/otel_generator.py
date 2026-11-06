"""
OpenTelemetry Collector Configuration Generator.
Produces valid, production-grade OpenTelemetry Collector YAML with strict signal isolation,
resilient retry policies, authenticated TLS endpoints, and environment-variable placeholders.
"""

from typing import Dict, Any, List, Optional, Tuple
import yaml


class OTelCollectorGenerator:
    """Generates and validates production OpenTelemetry Collector configurations."""

    SUPPORTED_COLLECTOR_DISTRO = "opentelemetry-collector-contrib"
    TARGET_COLLECTOR_VERSION = "v0.100.0+"

    @classmethod
    def generate_collector_yaml(
        cls,
        company_name: str,
        target_backend: str = "SigNoz Cloud",
        enable_dual_shipping: bool = True,
        region: str = "us",
    ) -> str:
        """
        Generates production-grade OpenTelemetry Collector YAML.
        Distinguishes:
        - Port 8126 (HTTP): Datadog APM trace ingestion (Beta)
        - Port 8125 (UDP): DogStatsD metrics ingestion (Beta)
        - Port 4317 (gRPC) & 4318 (HTTP): Standard OTLP (Stable)
        - /var/log/pods: Container log ingestion via filelog (Beta)
        """
        # Determine SigNoz endpoint based on target region
        signoz_endpoint = f"ingest.{region.lower()}.signoz.cloud:443" if region else "ingest.us.signoz.cloud:443"

        exporters_dict: Dict[str, Any] = {
            "otlp/signoz": {
                "endpoint": signoz_endpoint,
                "tls": {
                    "insecure": False,
                },
                "headers": {
                    "signoz-access-token": "${SIGNOZ_INGESTION_KEY}",
                },
                "retry_on_failure": {
                    "enabled": True,
                    "initial_interval": "5s",
                    "max_interval": "30s",
                    "max_elapsed_time": "5m",
                },
                "sending_queue": {
                    "enabled": True,
                    "num_consumers": 4,
                    "queue_size": 5000,
                },
                "timeout": "15s",
            }
        }

        trace_exporters = ["otlp/signoz"]
        metric_exporters = ["otlp/signoz"]
        log_exporters = ["otlp/signoz"]

        if enable_dual_shipping:
            exporters_dict["datadog"] = {
                "api": {
                    "key": "${DD_API_KEY}",
                    "site": "datadoghq.com",
                },
                "retry_on_failure": {
                    "enabled": True,
                    "initial_interval": "5s",
                    "max_interval": "30s",
                    "max_elapsed_time": "5m",
                },
                "sending_queue": {
                    "enabled": True,
                    "num_consumers": 4,
                    "queue_size": 5000,
                },
                "timeout": "15s",
            }
            trace_exporters.append("datadog")
            metric_exporters.append("datadog")
            log_exporters.append("datadog")

        config = {
            "receivers": {
                # 1. Native OTLP (Stable) - gRPC & HTTP
                "otlp": {
                    "protocols": {
                        "grpc": {"endpoint": "0.0.0.0:4317"},
                        "http": {"endpoint": "0.0.0.0:4318"},
                    }
                },
                # 2. Datadog APM Traces (Beta) - HTTP only
                "datadog": {
                    "endpoint": "0.0.0.0:8126",
                    "read_timeout": "60s",
                },
                # 3. DogStatsD Metrics (Beta) - UDP only
                "statsd": {
                    "endpoint": "0.0.0.0:8125",
                    "aggregation_interval": "10s",
                },
                # 4. Container Logs (Beta) - Filelog
                "filelog/std": {
                    "include": ["/var/log/pods/*/*/*.log"],
                    "exclude": ["/var/log/pods/opentelemetry-collector_*/*/*.log"],
                    "start_at": "end",
                    "retry_on_failure": {"enabled": True},
                },
            },
            "processors": {
                "memory_limiter": {
                    "check_interval": "1s",
                    "limit_percentage": 75,
                    "spike_limit_percentage": 20,
                },
                "batch": {
                    "send_batch_size": 8192,
                    "timeout": "5s",
                },
                "resourcedetection": {
                    "detectors": ["env", "system"],
                    "timeout": "2s",
                },
            },
            "exporters": exporters_dict,
            "extensions": {
                "health_check": {
                    "endpoint": "0.0.0.0:13133",
                },
            },
            "service": {
                "extensions": ["health_check"],
                "pipelines": {
                    "traces": {
                        "receivers": ["otlp", "datadog"],
                        "processors": ["memory_limiter", "resourcedetection", "batch"],
                        "exporters": trace_exporters,
                    },
                    "metrics": {
                        "receivers": ["otlp", "statsd"],
                        "processors": ["memory_limiter", "resourcedetection", "batch"],
                        "exporters": metric_exporters,
                    },
                    "logs": {
                        "receivers": ["otlp", "filelog/std"],
                        "processors": ["memory_limiter", "resourcedetection", "batch"],
                        "exporters": log_exporters,
                    },
                },
                "telemetry": {
                    "logs": {
                        "level": "info",
                    },
                },
            },
        }

        # Header commentary with technical maturity warnings
        header = f"""# ==============================================================================
# OpenTelemetry Collector Configuration Blueprint
# Target Organization: {company_name}
# Distribution: {cls.SUPPORTED_COLLECTOR_DISTRO} ({cls.TARGET_COLLECTOR_VERSION})
# Primary Target: {target_backend} ({signoz_endpoint})
# Dual-Shipping Active: {enable_dual_shipping}
#
# PROTOCOL & MATURITY MATRIX:
# - Traces (port 8126 HTTP): Datadog trace receiver (Beta - requires otelcol-contrib)
# - Metrics (port 8125 UDP): StatsD/DogStatsD receiver (Beta - requires aggregation tuning)
# - Logs (filelog): Container log tailing (Beta - requires DaemonSet host volume mount)
# - Native OTLP (4317/4318): OpenTelemetry standard protocol (Stable)
#
# SECURITY & COMPLIANCE:
# - Auth tokens are loaded exclusively via environment variables (${{SIGNOZ_INGESTION_KEY}}).
# - TLS is strictly enforced (insecure: false) on remote endpoints.
# ==============================================================================
"""
        yaml_body = yaml.dump(config, sort_keys=False, default_flow_style=False)
        return header + yaml_body

    @classmethod
    def validate_yaml(cls, yaml_content: str) -> bool:
        valid, _ = cls.validate_collector_yaml(yaml_content)
        return valid

    @classmethod
    def validate_collector_yaml(cls, yaml_str: str) -> Tuple[bool, List[str]]:
        """
        Validates OpenTelemetry Collector YAML syntax and structural compliance:
        - Must parse as valid YAML
        - Must contain receivers, processors, exporters, and service.pipelines
        - Traces, metrics, and logs must be separate pipelines
        - No plaintext API keys or credentials exposed
        - TLS must be configured with insecure: false
        - Datadog receiver must not be assigned to metrics or logs pipeline
        """
        errors: List[str] = []

        # Strip header comments for parsing
        try:
            parsed = yaml.safe_load(yaml_str)
        except Exception as e:
            return False, [f"YAML syntax parsing error: {str(e)}"]

        if not isinstance(parsed, dict):
            return False, ["Parsed YAML root is not a mapping/dictionary."]

        # Check top-level keys
        for key in ["receivers", "processors", "exporters", "service"]:
            if key not in parsed:
                errors.append(f"Missing required top-level configuration section: '{key}'.")

        receivers = parsed.get("receivers", {})
        processors = parsed.get("processors", {})
        exporters = parsed.get("exporters", {})
        service = parsed.get("service", {})
        pipelines = service.get("pipelines", {})

        # Signal separation validation
        for sig in ["traces", "metrics", "logs"]:
            if sig not in pipelines:
                errors.append(f"Missing separate pipeline for signal: '{sig}'.")

        # Receiver protocol check
        dd_rx = receivers.get("datadog", {})
        if dd_rx and dd_rx.get("endpoint") != "0.0.0.0:8126":
            errors.append(f"Datadog trace receiver endpoint must be port 8126, found: {dd_rx.get('endpoint')}")

        statsd_rx = receivers.get("statsd", {})
        if statsd_rx and statsd_rx.get("endpoint") != "0.0.0.0:8125":
            errors.append(f"DogStatsD receiver endpoint must be port 8125, found: {statsd_rx.get('endpoint')}")

        # Pipeline integrity: Datadog receiver only in traces pipeline
        traces_rx = pipelines.get("traces", {}).get("receivers", [])
        metrics_rx = pipelines.get("metrics", {}).get("receivers", [])
        logs_rx = pipelines.get("logs", {}).get("receivers", [])

        if "datadog" in metrics_rx:
            errors.append("Invalid pipeline: 'datadog' receiver is a trace-only receiver and cannot process metrics pipeline.")
        if "datadog" in logs_rx:
            errors.append("Invalid pipeline: 'datadog' receiver is a trace-only receiver and cannot process logs pipeline.")

        # Security check: Check for plaintext secret leaks
        for exp_name, exp_cfg in exporters.items():
            if isinstance(exp_cfg, dict):
                # Check headers
                headers = exp_cfg.get("headers", {})
                for h_name, h_val in headers.items():
                    if isinstance(h_val, str) and not h_val.startswith("${"):
                        errors.append(f"Security violation in {exp_name}: header '{h_name}' exposes hardcoded key instead of environment variable.")
                # Check api key in datadog exporter
                api_key = exp_cfg.get("api", {}).get("key")
                if api_key and isinstance(api_key, str) and not api_key.startswith("${"):
                    errors.append(f"Security violation in {exp_name}: API key exposed in plaintext instead of environment variable.")
                # Check TLS
                tls_cfg = exp_cfg.get("tls", {})
                if "insecure" in tls_cfg and tls_cfg["insecure"] is True:
                    errors.append(f"Security violation in {exp_name}: TLS is configured with insecure: true.")

        return len(errors) == 0, errors
