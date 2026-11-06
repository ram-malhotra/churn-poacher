"""
Objective Natural Language Interpreter.
Translates unstructured user opportunity descriptions into structured search criteria
and tailored public listener search queries without inventing unspecified criteria.
"""

import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TargetCompanySize(BaseModel):
    min: Optional[int] = Field(None, description="Minimum employee headcount")
    max: Optional[int] = Field(None, description="Maximum employee headcount")


class ObjectiveCriteria(BaseModel):
    raw_objective: str = Field(..., description="Original user prompt or description")
    target_geography: List[str] = Field(default_factory=list, description="Target countries or regions")
    target_company_size: Optional[TargetCompanySize] = Field(None, description="Employee headcount range")
    target_industry: Optional[str] = Field(None, description="Specific target industry if mentioned")
    target_vendor: str = Field(default="Datadog", description="Primary incumbent vendor targeted")
    pain_points: List[str] = Field(default_factory=list, description="Targeted pain points / dissatisfaction themes")
    migration_intent: bool = Field(default=False, description="Whether migration or replacement intent is specified")
    alternative_technologies: List[str] = Field(default_factory=list, description="Alternative or challenger technologies")
    priority_signals: List[str] = Field(default_factory=list, description="Priority signal themes extracted from prompt")
    search_queries: List[str] = Field(default_factory=list, description="Tailored search queries for public listener sources")
    filter_summary: str = Field(default="", description="Human-readable summary of applied criteria")


class ObjectiveInterpreter:
    """
    Deterministically parses freeform natural language targeting objectives into structured criteria.
    Guarantees that unspecified filters are not invented.
    """

    # Country pattern mapping (canonical name, aliases)
    GEOGRAPHY_PATTERNS = [
        (r"\b(united\s+states|usa|\bus\b)\b", "US"),
        (r"\b(india|\bind\b)\b", "India"),
        (r"\b(united\s+kingdom|uk|great\s+britain)\b", "UK"),
        (r"\b(germany|deutschland)\b", "Germany"),
        (r"\b(france)\b", "France"),
        (r"\b(canada)\b", "Canada"),
        (r"\b(australia)\b", "Australia"),
        (r"\b(europe|\beu\b)\b", "Europe"),
        (r"\b(singapore)\b", "Singapore"),
        (r"\b(japan)\b", "Japan"),
    ]

    # Common industries
    INDUSTRY_PATTERNS = [
        (r"\b(saas|software\s+as\s+a\s+service)\b", "SaaS"),
        (r"\b(fintech|financial\s+services|banking)\b", "Fintech"),
        (r"\b(e-?commerce|retail)\b", "E-Commerce"),
        (r"\b(healthcare|healthtech|biotech)\b", "Healthcare"),
        (r"\b(edtech|education)\b", "EdTech"),
        (r"\b(gaming|entertainment)\b", "Gaming"),
        (r"\b(telecom|telecommunications)\b", "Telecommunications"),
    ]

    # Challenger alternatives
    CHALLENGER_PATTERNS = [
        (r"\b(opentelemetry|otel)\b", "OpenTelemetry"),
        (r"\b(grafana|grafana\s+cloud|mimir|loki|tempo)\b", "Grafana"),
        (r"\b(signoz|signoz\s+cloud)\b", "SigNoz"),
        (r"\b(prometheus)\b", "Prometheus"),
        (r"\b(hyperdx)\b", "HyperDX"),
        (r"\b(jaeger)\b", "Jaeger"),
        (r"\b(clickhouse)\b", "ClickHouse"),
        (r"\b(victoria\s*metrics)\b", "VictoriaMetrics"),
    ]

    # Competitor vendors
    VENDOR_PATTERNS = [
        (r"\b(datadog)\b", "Datadog"),
        (r"\b(new\s*relic)\b", "New Relic"),
        (r"\b(dynatrace)\b", "Dynatrace"),
        (r"\b(splunk)\b", "Splunk"),
        (r"\b(appdynamics)\b", "AppDynamics"),
        (r"\b(sumo\s*logic)\b", "Sumo Logic"),
    ]

    @classmethod
    def interpret(cls, text: str) -> ObjectiveCriteria:
        """Parses natural-language objective into structured criteria."""
        if not text or not text.strip():
            return ObjectiveCriteria(
                raw_objective="",
                search_queries=["datadog pricing", "datadog opentelemetry", "datadog outage"],
                filter_summary="Default Datadog discovery across public sources.",
            )

        q = text.strip()
        q_lower = q.lower()

        # 1. Target Vendor
        target_vendor = "Datadog"
        for pattern, vendor in cls.VENDOR_PATTERNS:
            if re.search(pattern, q_lower):
                target_vendor = vendor
                break

        # 2. Target Geography
        geographies: List[str] = []
        for pattern, country in cls.GEOGRAPHY_PATTERNS:
            if re.search(pattern, q_lower):
                if country not in geographies:
                    geographies.append(country)

        # 3. Headcount / Company Size Range
        target_company_size: Optional[TargetCompanySize] = None
        # Range formats: 200–5000, 200-5000, 200 to 5000
        range_match = re.search(r"(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:employees|people|heads|headcount)?", q_lower)
        if range_match:
            min_val = int(range_match.group(1))
            max_val = int(range_match.group(2))
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            target_company_size = TargetCompanySize(min=min_val, max=max_val)
        else:
            # Format: > 500, more than 500, 500+
            more_than = re.search(r"(?:>|more\s+than|greater\s+than|\+)\s*(\d+)", q_lower) or re.search(r"(\d+)\s*\+\s*(?:employees|people)?", q_lower)
            if more_than:
                target_company_size = TargetCompanySize(min=int(more_than.group(1)), max=None)
            else:
                # Format: < 500, less than 500
                less_than = re.search(r"(?:<|less\s+than|under)\s*(\d+)", q_lower)
                if less_than:
                    target_company_size = TargetCompanySize(min=None, max=int(less_than.group(1)))

        # 4. Industry
        target_industry: Optional[str] = None
        for pattern, industry in cls.INDUSTRY_PATTERNS:
            if re.search(pattern, q_lower):
                target_industry = industry
                break

        # 5. Pain Points
        pain_points: List[str] = []
        if re.search(r"\b(high\s+costs?|costly|expensive|overpriced|spend|spending|bill|billing|price|pricing)\b", q_lower):
            pain_points.append("HIGH_OBSERVABILITY_COSTS")
        if re.search(r"\b(unexpected\s+bill|billing\s+increases?|billing\s+shocks?|invoice\s+shock|overage)\b", q_lower):
            pain_points.append("UNEXPECTED_BILLING_INCREASES")
        if re.search(r"\b(outages?|downtime|unreliable|incident|service\s+disruption)\b", q_lower):
            pain_points.append("OUTAGES_AND_DOWNTIME")
        if re.search(r"\b(performance\s+issues?|slow|latency|lag|high\s+overhead|agent\s+overhead)\b", q_lower):
            pain_points.append("PERFORMANCE_AND_OVERHEAD")
        if re.search(r"\b(deprecation|deprecated|breaking\s+changes?)\b", q_lower):
            pain_points.append("DEPRECATIONS_AND_BREAKING_CHANGES")

        # 6. Migration Intent
        migration_intent = bool(
            re.search(r"\b(migrat(e|ing|ion)|switch(ing)?|replac(e|ing)|churn(ing)?|move|moving\s+to|alternative|ditching|leaving)\b", q_lower)
        )

        # 7. Alternative Technologies
        alternatives: List[str] = []
        for pattern, tech in cls.CHALLENGER_PATTERNS:
            if re.search(pattern, q_lower):
                if tech not in alternatives:
                    alternatives.append(tech)

        # 8. Priority Signals
        priority_signals: List[str] = []
        if "HIGH_OBSERVABILITY_COSTS" in pain_points or "UNEXPECTED_BILLING_INCREASES" in pain_points:
            priority_signals.append("Pricing & Unexpected Billing Complaints")
        if migration_intent or alternatives:
            tech_str = "/".join(alternatives) if alternatives else "Open Source"
            priority_signals.append(f"Migration Discussions to {tech_str}")
        if "OUTAGES_AND_DOWNTIME" in pain_points:
            priority_signals.append("Recent Incidents & Outage Frustrations")
        if "PERFORMANCE_AND_OVERHEAD" in pain_points:
            priority_signals.append("Performance Degradation Reports")

        # 9. Build Tailored Listener Search Queries
        search_queries: List[str] = []
        vendor_slug = target_vendor.lower()

        if "HIGH_OBSERVABILITY_COSTS" in pain_points or "UNEXPECTED_BILLING_INCREASES" in pain_points:
            search_queries.append(f"{vendor_slug} pricing")
            search_queries.append(f"{vendor_slug} bill")

        if migration_intent or "OpenTelemetry" in alternatives:
            search_queries.append(f"{vendor_slug} opentelemetry")
        if "Grafana" in alternatives:
            search_queries.append(f"{vendor_slug} grafana")
        if "SigNoz" in alternatives:
            search_queries.append(f"{vendor_slug} signoz")
        if migration_intent and not alternatives:
            search_queries.append(f"{vendor_slug} migration")

        if "OUTAGES_AND_DOWNTIME" in pain_points:
            search_queries.append(f"{vendor_slug} outage")

        # Fallback if no specific queries matched
        if not search_queries:
            search_queries = [
                f"{vendor_slug} pricing",
                f"{vendor_slug} opentelemetry",
                f"{vendor_slug} outage",
            ]

        # Deduplicate search queries while preserving order
        deduped_queries = list(dict.fromkeys(search_queries))

        # 10. Filter summary string
        summary_parts = [f"Vendor: {target_vendor}"]
        if geographies:
            summary_parts.append(f"Geography: {', '.join(geographies)}")
        if target_company_size:
            if target_company_size.min and target_company_size.max:
                summary_parts.append(f"Employees: {target_company_size.min}–{target_company_size.max}")
            elif target_company_size.min:
                summary_parts.append(f"Employees: >{target_company_size.min}")
            elif target_company_size.max:
                summary_parts.append(f"Employees: <{target_company_size.max}")
        if target_industry:
            summary_parts.append(f"Industry: {target_industry}")
        if pain_points:
            summary_parts.append(f"Pain Points: {', '.join(pain_points)}")
        if alternatives:
            summary_parts.append(f"Challengers: {', '.join(alternatives)}")
        if migration_intent:
            summary_parts.append("Migration Intent: Active")

        return ObjectiveCriteria(
            raw_objective=text,
            target_geography=geographies,
            target_company_size=target_company_size,
            target_industry=target_industry,
            target_vendor=target_vendor,
            pain_points=pain_points,
            migration_intent=migration_intent,
            alternative_technologies=alternatives,
            priority_signals=priority_signals,
            search_queries=deduped_queries,
            filter_summary=" | ".join(summary_parts),
        )
