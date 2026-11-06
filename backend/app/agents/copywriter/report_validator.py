"""
Automated Report Validation Engine.
Runs comprehensive Technical, Financial, Editorial, and Evidence validation checks
before allowing any report or collateral bundle to be exported.
Blocks export or flags critical errors if validation requirements fail.
"""

import re
from typing import Dict, Any, List, Tuple
from pydantic import BaseModel, Field

from app.agents.finops_architect.otel_generator import OTelCollectorGenerator


class ReportValidationResult(BaseModel):
    """Structured results from pre-export validation."""
    passed: bool
    critical_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    technical_checks_passed: bool = True
    financial_checks_passed: bool = True
    editorial_checks_passed: bool = True
    evidence_checks_passed: bool = True
    details: Dict[str, Any] = Field(default_factory=dict)


class ReportValidator:
    """Validates technical accuracy, financial integrity, editorial quality, and factual provenance."""

    FORBIDDEN_PHRASES = [
        "risk-free",
        "risk free",
        "zero risk",
        "zero downtime guaranteed",
        "zero data loss guaranteed",
        "we identified your datadog expenditure",
        "your company will save $84,000",
        "we completely respect this constraint",
    ]

    @classmethod
    def validate_report(
        cls,
        bundle_markdown: str,
        package: Dict[str, Any],
        finops_data: Dict[str, Any],
        arch_data: Dict[str, Any],
        is_synthetic: bool = False,
    ) -> ReportValidationResult:
        """
        Executes all 4 validation suites:
        1. Technical (YAML syntax, ports, signal separation, TLS/auth)
        2. Financial (Formula consistency, overlap inclusion, labor inclusion, payback)
        3. Editorial (Repeated paragraphs, repeated objections, forbidden claims)
        4. Evidence (Provenance tracking, synthetic labeling)
        """
        critical_errors: List[str] = []
        warnings: List[str] = []
        lower_md = bundle_markdown.lower()

        # =====================================================================
        # 1. TECHNICAL VALIDATION
        # =====================================================================
        technical_passed = True
        collector_yaml = arch_data.get("collector_config_yaml") or ""
        
        # Extract full Section 6 YAML block from markdown if not passed directly in arch_data
        if not collector_yaml and "## 6. Validated OpenTelemetry Collector Configuration" in bundle_markdown:
            sec6_text = bundle_markdown.split("## 6. Validated OpenTelemetry Collector Configuration", 1)[1]
            match = re.search(r"```yaml\n(.*?)\n```", sec6_text, re.DOTALL)
            if match:
                collector_yaml = match.group(1)

        if collector_yaml:
            y_valid, y_errs = OTelCollectorGenerator.validate_collector_yaml(collector_yaml)
            if not y_valid:
                technical_passed = False
                for err in y_errs:
                    critical_errors.append(f"TECHNICAL: {err}")

        # Check port and protocol claims in text
        if "8126" in lower_md:
            # Check if text claims port 8126 handles/ingests metrics or logs
            for match in re.finditer(r"(?:port\s+8126|8126\/tcp)[^\.\n]{0,80}(?:metric|log)", lower_md):
                snippet = match.group(0)
                if not any(neg in snippet for neg in ["cannot", "not", "only", "neither", "distinct", "never", "unable"]):
                    technical_passed = False
                    critical_errors.append(f"TECHNICAL: Port 8126 erroneously claimed to ingest metrics or logs: '{snippet}'.")
                    break

            for match in re.finditer(r"(?:metrics?|logs?)[^\.\n]{0,60}(?:on\s+port\s+8126|via\s+8126)", lower_md):
                snippet = match.group(0)
                if not any(neg in snippet for neg in ["cannot", "not", "never", "unable", "neither"]):
                    technical_passed = False
                    critical_errors.append(f"TECHNICAL: Erroneous claim of metrics/logs on port 8126: '{snippet}'.")
                    break

        # =====================================================================
        # 2. FINANCIAL VALIDATION
        # =====================================================================
        financial_passed = True
        base_scenario = finops_data.get("scenarios", {}).get("BASE") or finops_data.get("base_scenario") or {}
        is_verified_spend = base_scenario.get("is_verified_spend", False) or finops_data.get("is_verified_spend", False)

        # Formula check 1: Net First Year Savings
        recurring_savings = base_scenario.get("recurring_annual_savings") or base_scenario.get("signoz_cloud_annual_savings", 0.0)
        total_one_time = base_scenario.get("total_one_time_investment", 0.0)
        labor_cost = base_scenario.get("migration_labor_cost", 0.0)
        overlap_cost = base_scenario.get("dual_shipping_overlap_cost", 0.0)
        infra_annual = base_scenario.get("additional_infrastructure_annual_cost", 0.0)
        net_first_year = base_scenario.get("net_first_year_savings", 0.0)

        # Dual-shipping overlap and labor cost must be accounted for
        if recurring_savings > 0:
            if total_one_time <= 0 and (labor_cost <= 0 or overlap_cost <= 0):
                financial_passed = False
                critical_errors.append("FINANCIAL: Total one-time migration investment must include labor and dual-shipping overlap.")

            expected_net_yr1 = round(recurring_savings - (total_one_time or (labor_cost + overlap_cost)) - infra_annual, 2)
            if net_first_year > 0 and abs(net_first_year - expected_net_yr1) > 2.0:
                financial_passed = False
                critical_errors.append(
                    f"FINANCIAL: Net first-year savings calculation mismatch (expected {expected_net_yr1}, got {net_first_year})."
                )

        # Disclaimer check: If spend is unverified, disclaimer MUST be present in markdown
        if not is_verified_spend:
            if "illustrative model" not in lower_md and "not verified" not in lower_md and "unverified" not in lower_md:
                financial_passed = False
                critical_errors.append("FINANCIAL: Missing mandatory disclaimer 'ILLUSTRATIVE MODEL — NOT VERIFIED CUSTOMER SPEND'.")

        # =====================================================================
        # 3. EDITORIAL VALIDATION
        # =====================================================================
        editorial_passed = True

        # Check for forbidden buzzwords and unproven claims
        for phrase in cls.FORBIDDEN_PHRASES:
            if phrase in lower_md:
                editorial_passed = False
                critical_errors.append(f"EDITORIAL: Prohibited unproven or repetitive phrase detected: '{phrase}'.")

        # Repeated objection responses check
        objection_items = package.get("objection_matrix", {}).get("items", [])
        seen_responses = set()
        seen_openings = set()
        for obj in objection_items:
            resp = (obj.get("recommended_response") or "").strip()
            if resp:
                if resp in seen_responses:
                    editorial_passed = False
                    critical_errors.append(f"EDITORIAL: Duplicate objection response detected for '{obj.get('objection')}'.")
                seen_responses.add(resp)

                # Check for repeated opening 30 chars
                opening = resp[:35].lower()
                if opening in seen_openings:
                    editorial_passed = False
                    critical_errors.append(f"EDITORIAL: Repetitive objection opening detected: '{opening}...'.")
                seen_openings.add(opening)

        # Repeated non-empty paragraphs check (> 60 chars)
        paragraphs = [p.strip() for p in bundle_markdown.split("\n\n") if len(p.strip()) > 60]
        seen_paragraphs = set()
        for p in paragraphs:
            # Normalize whitespace
            norm = " ".join(p.split())
            if norm in seen_paragraphs:
                warnings.append(f"EDITORIAL: Repeated paragraph detected: '{norm[:50]}...'.")
            seen_paragraphs.add(norm)

        # =====================================================================
        # 4. EVIDENCE & PROVENANCE VALIDATION
        # =====================================================================
        evidence_passed = True
        if is_synthetic:
            # Synthetic companies must be prominently labeled and never presented as verified
            if "synthetic" not in lower_md and "illustrative" not in lower_md and "generic" not in lower_md:
                evidence_passed = False
                critical_errors.append("EVIDENCE: Synthetic prospect must be explicitly labeled as synthetic or illustrative.")

        passed = len(critical_errors) == 0

        return ReportValidationResult(
            passed=passed,
            critical_errors=critical_errors,
            warnings=warnings,
            technical_checks_passed=technical_passed,
            financial_checks_passed=financial_passed,
            editorial_checks_passed=editorial_passed,
            evidence_checks_passed=evidence_passed,
            details={
                "yaml_validated": bool(collector_yaml),
                "is_verified_spend": is_verified_spend,
                "is_synthetic": is_synthetic,
                "objection_count": len(objection_items),
                "critical_error_count": len(critical_errors),
                "warning_count": len(warnings),
            },
        )
