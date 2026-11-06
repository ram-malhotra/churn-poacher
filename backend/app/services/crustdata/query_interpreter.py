"""
Crustdata Natural Language Query Interpreter
Translates unstructured English queries into valid Crustdata v2025-11-01 filter trees.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from app.services.crustdata.schemas import EntityType


class QueryInterpretation(BaseModel):
    raw_query: str
    target_entity: EntityType
    company_name: Optional[str] = None
    person_name: Optional[str] = None
    job_title: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    country: Optional[str] = None
    headcount_min: Optional[int] = None
    headcount_max: Optional[int] = None
    industry: Optional[str] = None
    crustdata_endpoint: str
    filter_tree: Dict[str, Any]
    requires_external_evidence: bool = False
    evidence_notes: str
    buying_intent_distinction: str

    @property
    def employee_min(self) -> Optional[int]:
        return self.headcount_min

    @property
    def employee_max(self) -> Optional[int]:
        return self.headcount_max


class CrustdataQueryInterpreter:
    """
    Parses natural language queries and builds official Crustdata v2025-11-01 filter trees.
    """

    KNOWN_TECH_MAP = {
        "datadog": "Datadog",
        "aws": "Amazon AWS Platform",
        "amazon web services": "Amazon AWS Platform",
        "kubernetes": "Kubernetes",
        "snowflake": "Snowflake",
        "new relic": "New Relic",
        "dynatrace": "Dynatrace",
        "splunk": "Splunk",
        "grafana": "Grafana",
        "prometheus": "Prometheus",
        "docker": "Docker",
        "azure": "Microsoft Azure",
        "gcp": "Google Cloud Platform (GCP)",
        "google cloud": "Google Cloud Platform (GCP)",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "redis": "Redis",
        "kafka": "Apache Kafka",
    }

    COUNTRY_MAP = {
        "us": "USA",
        "usa": "USA",
        "united states": "USA",
        "uk": "GBR",
        "united kingdom": "GBR",
        "india": "IND",
        "germany": "DEU",
        "france": "FRA",
        "canada": "CAN",
    }

    ROLE_PATTERNS = [
        (r"\b(ctos?|chief\s+technology\s+officers?)\b", "CTO"),
        (r"\b(cios?|chief\s+information\s+officers?)\b", "CIO"),
        (r"\b(cisos?|chief\s+information\s+security\s+officers?)\b", "CISO"),
        (r"\b(vps?\s+of\s+engineering|vps?\s+engineering|vice\s+presidents?\s+engineering)\b", "VP Engineering"),
        (r"\b(directors?\s+of\s+engineering|engineering\s+directors?)\b", "Director of Engineering"),
        (r"\b(heads?\s+of\s+engineering)\b", "Head of Engineering"),
        (r"\b(heads?\s+of\s+infrastructure|vps?\s+infrastructure)\b", "Head of Infrastructure"),
        (r"\b(sre\s+leads?|site\s+reliability\s+engineers?)\b", "Site Reliability Engineer"),
        (r"\b(observability\s+engineers?)\b", "Observability Engineer"),
        (r"\b(devops\s+engineers?|devops\s+leads?)\b", "DevOps Engineer"),
    ]

    @classmethod
    def interpret(cls, query: str) -> QueryInterpretation:
        q_lower = query.lower().strip()

        # 1. Detect target entity type
        is_person_query = bool(
            re.search(r"\b(ctos?|vps?|vice\s+presidents?|directors?|engineers?|officers?|founders?|ceos?|executives?|people|person|leads?)\b", q_lower)
            or re.search(r"\b(find|who is|show)\s+[A-Z][a-z]+\s+[A-Z][a-z]+", query)
        )
        is_job_query = bool(
            re.search(r"\b(hiring|job openings?|jobs?|vacancies|open positions?)\b", q_lower)
        )

        target_entity = EntityType.COMPANY
        if is_job_query:
            target_entity = EntityType.COMPANY  # Or job-backed company discovery
        elif is_person_query:
            target_entity = EntityType.PERSON

        # 2. Extract technologies
        detected_tech = []
        for kw, official_name in cls.KNOWN_TECH_MAP.items():
            if re.search(r"\b" + re.escape(kw) + r"\b", q_lower):
                if official_name not in detected_tech:
                    detected_tech.append(official_name)

        # 3. Extract country / location
        country = None
        for kw, code in cls.COUNTRY_MAP.items():
            if re.search(r"\b" + re.escape(kw) + r"\b", q_lower):
                country = code
                break

        # 4. Extract employee / headcount range
        hc_min, hc_max = None, None
        # Pattern 1: "200-1000 employees" or "200 to 1000 employees" or "200–1000"
        hc_match = re.search(r"(\d+)\s*(?:–|-|to)\s*(\d+)", q_lower)
        if hc_match:
            hc_min = int(hc_match.group(1))
            hc_max = int(hc_match.group(2))
        else:
            # Pattern 2: "more than 500", "over 500", "> 500", "at least 500"
            gt_match = re.search(r"(?:more than|greater than|over|above|at least|>=|>)\s*(\d+)", q_lower)
            if gt_match:
                hc_min = int(gt_match.group(1))

            # Pattern 3: "less than 500", "under 500", "< 500", "at most 500"
            lt_match = re.search(r"(?:less than|under|below|at most|<=|<)\s*(\d+)", q_lower)
            if lt_match:
                hc_max = int(lt_match.group(1))

        if hc_min is None and hc_max is None:
            if re.search(r"\b(large engineering teams?|large enterprise)\b", q_lower):
                hc_min = 500
            elif re.search(r"\b(small business|startup)\b", q_lower):
                hc_max = 200

        # 5. Extract role / job title
        job_title = None
        for pattern, role_title in cls.ROLE_PATTERNS:
            if re.search(pattern, q_lower):
                job_title = role_title
                break

        # 6. Extract company name if specified (e.g. "at NVIDIA", "at Datadog", "of Datadog")
        company_name = None
        comp_match = re.search(r"\b(?:at|for|of|in)\s+([A-Z][A-Za-z0-9&\.\-]+(?:\s+[A-Z][A-Za-z0-9&\.\-]+)?)", query)
        if comp_match:
            candidate_comp = comp_match.group(1).strip()
            # Verify candidate_comp is not a country or tech or common filler
            if (
                candidate_comp.lower() not in cls.COUNTRY_MAP
                and candidate_comp.lower() not in cls.KNOWN_TECH_MAP
                and candidate_comp.lower() not in ("companies", "startups", "firms", "enterprises")
            ):
                company_name = candidate_comp

        # If it's a simple search for a known company like "NVIDIA" or "OpenAI" without keywords:
        if not company_name and not is_person_query and not detected_tech and not hc_min:
            clean_name = re.sub(r"^(find|search|show|lookup|companies?)\s+", "", query, flags=re.IGNORECASE).strip()
            if len(clean_name.split()) <= 3 and "." not in clean_name:
                company_name = clean_name

        # 7. Extract industry
        industry = None
        if "saas" in q_lower:
            industry = "SaaS"
        elif "fintech" in q_lower or "finance" in q_lower or "financial" in q_lower:
            industry = "Financial Services / FinTech"
        elif "healthcare" in q_lower:
            industry = "Healthcare"

        # 8. Build filter tree based on entity type
        filter_tree: Dict[str, Any] = {}
        conditions = []

        if target_entity == EntityType.PERSON:
            endpoint = "/person/search"
            if job_title:
                conditions.append({
                    "field": "experience.employment_details.current.title",
                    "type": "(.)",
                    "value": job_title,
                })
            if company_name:
                conditions.append({
                    "field": "experience.employment_details.current.company_name",
                    "type": "(.)",
                    "value": company_name,
                })
            if detected_tech:
                # Filter on profile headline mentioning the technology stack
                conditions.append({
                    "field": "basic_profile.headline",
                    "type": "(.)",
                    "value": detected_tech[0],
                })
            if country:
                conditions.append({
                    "field": "basic_profile.location.country",
                    "type": "=",
                    "value": country,
                })
            # If plain name search without title/company
            if not job_title and not company_name and not detected_tech:
                person_clean = re.sub(r"^(find|search|lookup|who is)\s+", "", query, flags=re.IGNORECASE).strip()
                conditions.append({
                    "field": "basic_profile.name",
                    "type": "(.)",
                    "value": person_clean,
                })
        else:
            endpoint = "/company/search"
            if company_name and not detected_tech and not hc_min:
                if "." in company_name:
                    conditions.append({
                        "field": "basic_info.primary_domain",
                        "type": "=",
                        "value": company_name.lower(),
                    })
                else:
                    conditions.append({
                        "field": "basic_info.name",
                        "type": "(.)",
                        "value": company_name,
                    })

            if country:
                conditions.append({
                    "field": "locations.country",
                    "type": "=",
                    "value": country,
                })

            if hc_min is not None:
                conditions.append({
                    "field": "headcount.total",
                    "type": "=>",
                    "value": hc_min,
                })
            if hc_max is not None:
                conditions.append({
                    "field": "headcount.total",
                    "type": "=<",
                    "value": hc_max,
                })

            if industry:
                ind_val = "Fintech" if "FinTech" in industry else industry
                conditions.append({
                    "field": "basic_info.description",
                    "type": "(.)",
                    "value": ind_val,
                })

            if detected_tech:
                # Add technographics condition
                conditions.append({
                    "field": "technographics.technologies.name",
                    "type": "in",
                    "value": detected_tech,
                })

            # If no conditions were added, fallback to name contains
            if not conditions:
                conditions.append({
                    "field": "basic_info.name",
                    "type": "(.)",
                    "value": query.strip(),
                })

        filter_tree = {
            "op": "and",
            "conditions": conditions,
        }

        # 9. Buying intent and external evidence explanation
        has_buying_intent_claim = bool(
            re.search(r"\b(unhappy|complaint|takeout|churn|switch|leaving|expensive|bill shock|dissatisfied)\b", q_lower)
        )
        if has_buying_intent_claim or detected_tech:
            evidence_notes = (
                "Crustdata identifies matching companies, headcount, verified technologies and relevant decision-makers. "
                "However, Crustdata presence alone does NOT constitute buying intent. Public distress signals "
                "(from Reddit, X, customer forums) must be corroborated to qualify switching or churn intent."
            )
            buying_intent_distinction = (
                "INTELLIGENCE_ONLY: Technographic footprint and firmographics verified via Crustdata. "
                "Switching intent requires corroboration with Churn Poacher's Signal Monitor."
            )
        else:
            evidence_notes = "Crustdata provides firmographic and professional identity intelligence."
            buying_intent_distinction = "INTELLIGENCE_ONLY: Market data discovery; no customer dissatisfaction signal assumed."

        return QueryInterpretation(
            raw_query=query,
            target_entity=target_entity,
            company_name=company_name,
            job_title=job_title,
            technologies=detected_tech,
            country=country,
            headcount_min=hc_min,
            headcount_max=hc_max,
            industry=industry,
            crustdata_endpoint=endpoint,
            filter_tree=filter_tree,
            requires_external_evidence=has_buying_intent_claim,
            evidence_notes=evidence_notes,
            buying_intent_distinction=buying_intent_distinction,
        )
