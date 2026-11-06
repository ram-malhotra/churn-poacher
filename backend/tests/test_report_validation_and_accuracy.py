import pytest
from app.models.company import Company
from app.agents.finops_architect.otel_generator import OTelCollectorGenerator
from app.agents.finops_architect.scenario_analyzer import ScenarioAnalyzer
from app.agents.finops_architect.financial_models import InfrastructureInput
from app.agents.finops_architect.architecture_analyzer import ArchitectureAnalyzer
from app.agents.finops_architect.architecture_agent import ArchitectureAgent
from app.agents.copywriter.report_validator import ReportValidator
from app.agents.copywriter.objection_handler import ObjectionHandler


class TestReportValidationAndAccuracy:
    """
    Validates technical accuracy, mathematical rigor, and editorial integrity
    of the underlying report-generation and export system.
    """

    def test_collector_yaml_validation_valid(self):
        """Ensures compliant OTel Collector YAML passes validation."""
        valid_yaml = OTelCollectorGenerator.generate_collector_yaml(
            company_name="ApexFin Technologies",
            target_backend="SigNoz Cloud",
            enable_dual_shipping=True,
            region="us",
        )
        is_valid, errors = OTelCollectorGenerator.validate_collector_yaml(valid_yaml)
        assert is_valid is True, f"Valid YAML was unexpectedly rejected: {errors}"
        assert len(errors) == 0

        # Verify separate signal pipelines are generated
        assert "traces:" in valid_yaml
        assert "metrics:" in valid_yaml
        assert "logs:" in valid_yaml

        # Verify port distinction: :8126 HTTP for traces, :8125 UDP for metrics, filelog for logs
        assert "endpoint: 0.0.0.0:8126" in valid_yaml
        assert "endpoint: 0.0.0.0:8125" in valid_yaml
        assert "/var/log/pods" in valid_yaml

        # Verify environment variable secret handling (no plaintext keys)
        assert "${SIGNOZ_INGESTION_KEY}" in valid_yaml
        assert "insecure: false" in valid_yaml

    def test_collector_yaml_validation_rejects_single_port_for_all(self):
        """Ensures validator rejects configurations claiming port 8126 handles all signals."""
        invalid_yaml = """
receivers:
  datadog:
    endpoint: 0.0.0.0:8126

exporters:
  otlp:
    endpoint: ingest.us.signoz.cloud:443
    tls:
      insecure: false

service:
  pipelines:
    traces:
      receivers: [datadog]
      exporters: [otlp]
    metrics:
      receivers: [datadog]
      exporters: [otlp]
    logs:
      receivers: [datadog]
      exporters: [otlp]
"""
        is_valid, errors = OTelCollectorGenerator.validate_collector_yaml(invalid_yaml)
        assert is_valid is False
        assert any("trace-only receiver" in err for err in errors)

    def test_collector_yaml_validation_rejects_plaintext_secret(self):
        """Ensures validator rejects hardcoded plaintext API keys in headers."""
        plaintext_key_yaml = """
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:

exporters:
  otlp/signoz:
    endpoint: ingest.us.signoz.cloud:443
    headers:
      signoz-access-token: "real_secret_token_12345_abcdef"
    tls:
      insecure: false

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/signoz]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/signoz]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/signoz]
"""
        is_valid, errors = OTelCollectorGenerator.validate_collector_yaml(plaintext_key_yaml)
        assert is_valid is False
        assert any("Security violation" in err or "hardcoded key" in err for err in errors)

    def test_finops_scenario_mathematical_consistency(self):
        """Verifies mathematical formulas across Low, Base, and High migration scenarios."""
        inputs = [
            InfrastructureInput(name="monitored_hosts", value=120.0, unit="hosts", source="DEMO", confidence=0.85),
            InfrastructureInput(name="apm_hosts", value=80.0, unit="hosts", source="DEMO", confidence=0.85),
            InfrastructureInput(name="custom_metrics", value=12000.0, unit="metrics", source="DEMO", confidence=0.85),
            InfrastructureInput(name="monthly_log_gb", value=3000.0, unit="GB", source="DEMO", confidence=0.85),
            InfrastructureInput(name="monthly_trace_gb", value=2000.0, unit="GB", source="DEMO", confidence=0.85),
        ]

        scenarios, _ = ScenarioAnalyzer.analyze_scenarios(
            inputs=inputs,
            is_verified_spend=False,
        )

        assert "LOW" in scenarios
        assert "BASE" in scenarios
        assert "HIGH" in scenarios

        for level, s in scenarios.items():
            # Current spend should be positive
            assert s.current_annual_spend > 0

            # Recurring savings = Incumbent - Target
            expected_recurring = round(s.current_annual_spend - s.target_annual_spend, 2)
            assert abs(s.recurring_annual_savings - expected_recurring) <= 0.05

            # Total one-time = labor + dual-shipping overlap
            expected_one_time = round(s.migration_labor_cost + s.dual_shipping_overlap_cost, 2)
            assert abs(s.total_one_time_investment - expected_one_time) <= 0.05

            # Net first-year savings = Recurring - One-Time - Additional Infra
            expected_net_yr1 = round(
                s.recurring_annual_savings - s.total_one_time_investment - s.additional_infrastructure_annual_cost,
                2,
            )
            assert abs(s.net_first_year_savings - expected_net_yr1) <= 0.05

            # 3-Year Net Savings = (3 * Recurring) - One-Time - (3 * Infra)
            expected_3yr_net = round(
                (3 * s.recurring_annual_savings) - s.total_one_time_investment - (3 * s.additional_infrastructure_annual_cost),
                2,
            )
            assert abs(s.three_year_net_savings - expected_3yr_net) <= 0.05

            # Unverified spend must be explicitly flagged
            assert s.is_verified_spend is False
            assert "ILLUSTRATIVE MODEL — NOT VERIFIED CUSTOMER SPEND" in s.data_label

    def test_report_validator_catches_forbidden_buzzwords(self):
        """Ensures the editorial validator blocks 'risk-free' and related buzzwords."""
        bad_markdown = """
# Migration Overview
Our risk-free dual shipping architecture guarantees zero downtime.
"""
        validation = ReportValidator.validate_report(
            bundle_markdown=bad_markdown,
            package={},
            finops_data={},
            arch_data={},
            is_synthetic=False,
        )
        assert validation.passed is False
        assert any("risk-free" in err for err in validation.critical_errors)

    def test_report_validator_catches_repetitive_objections(self):
        """Ensures the objection validator rejects copy-pasted or identical openings."""
        bad_package = {
            "objection_matrix": {
                "items": [
                    {
                        "objection": "Engineering Bandwidth",
                        "recommended_response": "We completely respect this constraint. That is why the migration architecture is built around dual-shipping.",
                    },
                    {
                        "objection": "Production Downtime Risk",
                        "recommended_response": "We completely respect this constraint. That is why the migration architecture is built around dual-shipping.",
                    },
                ]
            }
        }
        validation = ReportValidator.validate_report(
            bundle_markdown="# Report\n\nSome body text",
            package=bad_package,
            finops_data={},
            arch_data={},
            is_synthetic=False,
        )
        assert validation.passed is False
        assert any("Duplicate objection response" in err or "Repetitive objection opening" in err for err in validation.critical_errors)

    def test_objection_matrix_generates_distinct_enterprise_responses(self):
        """Ensures ObjectionHandler produces 7 bespoke responses with no shared boilerplate."""
        context = {
            "company_name": "ApexFin Technologies",
            "target_challenger": "SigNoz Cloud",
            "target_vendor": "Datadog",
        }
        matrix = ObjectionHandler.generate_matrix(
            context=context,
            finops_data={},
            arch_data={},
        )
        assert len(matrix.items) == 7

        seen_openings = set()
        for obj in matrix.items:
            resp = obj.recommended_response
            assert len(resp) > 50
            # Ensure no buzzwords
            assert "risk-free" not in resp.lower()
            assert "zero downtime guaranteed" not in resp.lower()

            # Ensure opening 30 chars are unique across all objections
            opening = resp[:30].lower()
            assert opening not in seen_openings, f"Duplicate opening found in objection: {obj.objection}"
            seen_openings.add(opening)

    @pytest.mark.asyncio
    async def test_unverified_company_receives_generic_blueprint(self):
        """Ensures an unverified/unknown prospect receives a Generic Technical Blueprint."""
        company = Company(
            id="unknown-prospect-123",
            signal_id="sig-999",
            name="Unknown Corp",
            domain="unknowncorp.io",
            industry="Technology",
            tech_stack={},
            infrastructure_indicators={},
            evidence_records=[],
            qualification_status="NEW",
            is_synthetic=True,
        )
        blueprint = await ArchitectureAgent.generate_migration_blueprint(
            company=company,
            target_backend="SigNoz Cloud",
        )
        assert blueprint.is_generic_blueprint is True
        assert blueprint.current_architecture.evidence_provenance == "UNKNOWN"
        assert blueprint.current_architecture.datadog_agents_detected is False
