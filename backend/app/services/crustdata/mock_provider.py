"""
Deterministic Mock Provider for Crustdata Intelligence.
Used exclusively in DEMO mode or unit testing without API credits.
Always tags records with is_mock=True and data_origin='DEMO' to prevent
confusing synthetic fixtures with real production data.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.services.crustdata.schemas import (
    EntityType,
    EnrichmentLevel,
    VerificationClassification,
    EntityCandidate,
    PaginatedCandidateList,
    CrustdataCreditsInfo,
    CompanyIntelligenceProfile,
    PersonIntelligenceProfile,
    TechnographicItem,
    FundingRoundItem,
    JobListingItem,
    WorkHistoryItem,
    IntelligenceEvidenceItem,
)


class CrustdataMockProvider:
    """Provides structured, high-fidelity mock data strictly for DEMO mode."""

    MOCK_CREDITS = CrustdataCreditsInfo(
        total_credits=1450.0,
        remaining_credits=1450.0,
        used_credits=0.0,
        renewal_date="2026-12-01T00:00:00Z",
        enabled_endpoints=[
            "/company/search",
            "/company/enrich",
            "/person/search",
            "/person/enrich",
            "/job/search",
            "/company/search/autocomplete",
            "/account/credits",
        ],
        is_mock=True,
    )

    MOCK_COMPANIES: Dict[str, Dict[str, Any]] = {
        "spacex": {
            "name": "SpaceX",
            "primary_domain": "spacex.com",
            "website": "https://www.spacex.com",
            "linkedin_url": "https://www.linkedin.com/company/spacex",
            "description": "Space exploration technologies and orbital aerospace manufacturer.",
            "industry": "Aerospace & Defense",
            "headcount": "10,000+ employees",
            "annual_revenue_range": "$5B - $10B",
            "headquarters": "Hawthorne, California, USA",
            "founding_year": 2002,
            "technographics": [
                {"name": "Kubernetes", "category": "Containers", "classification": "VERIFIED"},
                {"name": "Prometheus", "category": "Observability", "classification": "VERIFIED"},
                {"name": "Grafana", "category": "Observability", "classification": "VERIFIED"},
                {"name": "Datadog", "category": "Observability", "classification": "INFERRED", "source_url": "https://spacex.com/careers/observability-engineer"},
                {"name": "Python", "category": "Languages", "classification": "VERIFIED"},
                {"name": "C++", "category": "Languages", "classification": "VERIFIED"},
            ],
            "funding_rounds": [
                {"round_name": "Private Equity", "amount_usd": 750000000.0, "round_date": "2023-01-02", "investors": ["Andreessen Horowitz", "Founders Fund"]},
            ],
            "total_funding_usd": 9800000000.0,
            "leadership": [
                {"name": "Elon Musk", "title": "CEO & Chief Engineer", "linkedin": "https://linkedin.com/in/elonmusk"},
                {"name": "Gwynne Shotwell", "title": "President & COO", "linkedin": "https://linkedin.com/in/gwynneshotwell"},
            ],
            "active_jobs": [
                {"title": "Senior Telemetry & Observability Engineer", "department": "Avionics Software", "location": "Hawthorne, CA", "required_technologies": ["OpenTelemetry", "Grafana", "Datadog", "C++"]},
            ],
        },
        "openai": {
            "name": "OpenAI",
            "primary_domain": "openai.com",
            "website": "https://openai.com",
            "linkedin_url": "https://www.linkedin.com/company/openai",
            "description": "AI research and deployment company behind ChatGPT and foundation models.",
            "industry": "Artificial Intelligence / Software",
            "headcount": "1,000 - 5,000 employees",
            "annual_revenue_range": "$1B - $5B",
            "headquarters": "San Francisco, California, USA",
            "founding_year": 2015,
            "technographics": [
                {"name": "Kubernetes", "category": "Containers", "classification": "VERIFIED"},
                {"name": "Microsoft Azure", "category": "Cloud Provider", "classification": "VERIFIED"},
                {"name": "Datadog", "category": "Observability", "classification": "VERIFIED", "source_url": "https://openai.com/careers/infrastructure-eng"},
                {"name": "PyTorch", "category": "AI Framework", "classification": "VERIFIED"},
                {"name": "Ray", "category": "Distributed Compute", "classification": "VERIFIED"},
            ],
            "funding_rounds": [
                {"round_name": "Corporate Venture", "amount_usd": 10000000000.0, "round_date": "2023-01-23", "investors": ["Microsoft"]},
            ],
            "total_funding_usd": 14000000000.0,
            "leadership": [
                {"name": "Sam Altman", "title": "CEO", "linkedin": "https://linkedin.com/in/samaltman"},
                {"name": "Greg Brockman", "title": "President", "linkedin": "https://linkedin.com/in/gregbrockman"},
            ],
            "active_jobs": [
                {"title": "Systems Reliability Engineer (SRE)", "department": "Platform", "location": "San Francisco, CA", "required_technologies": ["Datadog", "Kubernetes", "Azure", "Terraform"]},
            ],
        },
        "nvidia": {
            "name": "NVIDIA",
            "primary_domain": "nvidia.com",
            "website": "https://www.nvidia.com",
            "linkedin_url": "https://www.linkedin.com/company/nvidia",
            "description": "Pioneer of GPU-accelerated computing, AI platforms, and enterprise data centers.",
            "industry": "Semiconductors & AI Hardware",
            "headcount": "25,000+ employees",
            "annual_revenue_range": "$50B+",
            "headquarters": "Santa Clara, California, USA",
            "founding_year": 1993,
            "technographics": [
                {"name": "CUDA", "category": "Parallel Computing", "classification": "VERIFIED"},
                {"name": "Kubernetes", "category": "Containers", "classification": "VERIFIED"},
                {"name": "Prometheus", "category": "Observability", "classification": "VERIFIED"},
                {"name": "Datadog", "category": "Observability", "classification": "INFERRED"},
                {"name": "AWS", "category": "Cloud Provider", "classification": "VERIFIED"},
            ],
            "funding_rounds": [],
            "total_funding_usd": 0.0,
            "leadership": [
                {"name": "Jensen Huang", "title": "Founder & CEO", "linkedin": "https://linkedin.com/in/jensenhuang"},
            ],
            "active_jobs": [
                {"title": "Principal Infrastructure Architect", "department": "AI Enterprise", "location": "Santa Clara, CA", "required_technologies": ["Kubernetes", "Datadog", "Prometheus", "OpenTelemetry"]},
            ],
        },
        "datadog": {
            "name": "Datadog",
            "primary_domain": "datadoghq.com",
            "website": "https://www.datadoghq.com",
            "linkedin_url": "https://www.linkedin.com/company/datadog",
            "description": "Essential observability and security platform for cloud applications.",
            "industry": "Cloud Observability & Security",
            "headcount": "5,000+ employees",
            "annual_revenue_range": "$2B+",
            "headquarters": "New York, New York, USA",
            "founding_year": 2010,
            "technographics": [
                {"name": "AWS", "category": "Cloud Provider", "classification": "VERIFIED"},
                {"name": "Kubernetes", "category": "Containers", "classification": "VERIFIED"},
                {"name": "Go", "category": "Languages", "classification": "VERIFIED"},
                {"name": "Kafka", "category": "Streaming", "classification": "VERIFIED"},
            ],
            "funding_rounds": [],
            "total_funding_usd": 147000000.0,
            "leadership": [
                {"name": "Olivier Pomel", "title": "CEO", "linkedin": "https://linkedin.com/in/olivierpomel"},
                {"name": "Alexis Lê-Quôc", "title": "CTO", "linkedin": "https://linkedin.com/in/alexislequoc"},
            ],
            "active_jobs": [],
        },
    }

    MOCK_PEOPLE: Dict[str, Dict[str, Any]] = {
        "elon musk": {
            "full_name": "Elon Musk",
            "current_title": "CEO & Chief Engineer",
            "current_company": "SpaceX",
            "headline": "CEO of SpaceX, Tesla, xAI, CTO of X",
            "location": "Austin, Texas, USA",
            "linkedin_url": "https://www.linkedin.com/in/elonmusk",
            "twitter_url": "https://twitter.com/elonmusk",
            "verified_work_email": "elon@spacex.com",
            "summary_bio": "Founder and technology leader focusing on sustainable transport, reusable spaceflight, and AI.",
            "is_decision_maker": True,
            "decision_maker_score": 0.99,
            "work_history": [
                {"company_name": "SpaceX", "title": "CEO & Chief Engineer", "start_date": "2002-05", "is_current": True},
                {"company_name": "Tesla", "title": "CEO & Product Architect", "start_date": "2004-02", "is_current": True},
                {"company_name": "xAI", "title": "Founder", "start_date": "2023-03", "is_current": True},
            ],
            "skills": ["Systems Architecture", "Aerospace Engineering", "Distributed Systems", "Venture Capital"],
        },
        "sam altman": {
            "full_name": "Sam Altman",
            "current_title": "CEO",
            "current_company": "OpenAI",
            "headline": "CEO at OpenAI, former President of Y Combinator",
            "location": "San Francisco, California, USA",
            "linkedin_url": "https://www.linkedin.com/in/samaltman",
            "twitter_url": "https://twitter.com/sama",
            "verified_work_email": "sam@openai.com",
            "summary_bio": "Entrepreneur and investor, leading research in safe artificial general intelligence.",
            "is_decision_maker": True,
            "decision_maker_score": 0.98,
            "work_history": [
                {"company_name": "OpenAI", "title": "CEO", "start_date": "2019-03", "is_current": True},
                {"company_name": "Y Combinator", "title": "President", "start_date": "2014-02", "end_date": "2019-03", "is_current": False},
            ],
            "skills": ["Artificial Intelligence", "Corporate Strategy", "Venture Capital", "Product Management"],
        },
        "olivier pomel": {
            "full_name": "Olivier Pomel",
            "current_title": "Co-founder & CEO",
            "current_company": "Datadog",
            "headline": "CEO at Datadog",
            "location": "New York, New York, USA",
            "linkedin_url": "https://www.linkedin.com/in/olivierpomel",
            "twitter_url": "https://twitter.com/olivierpomel",
            "verified_work_email": "olivier@datadoghq.com",
            "summary_bio": "Co-founder and CEO of Datadog, leading SaaS observability and cloud monitoring.",
            "is_decision_maker": True,
            "decision_maker_score": 0.99,
            "work_history": [
                {"company_name": "Datadog", "title": "CEO", "start_date": "2010-06", "is_current": True},
            ],
            "skills": ["Cloud Monitoring", "Observability", "Distributed Systems", "Enterprise SaaS"],
        },
    }

    @classmethod
    def get_credits(cls) -> CrustdataCreditsInfo:
        return cls.MOCK_CREDITS

    @classmethod
    def search_candidates(
        cls,
        query: str,
        entity_type: Optional[EntityType] = None,
        limit: int = 10,
        cursor: Optional[str] = None,
    ) -> PaginatedCandidateList:
        q_clean = query.lower().strip()
        all_candidates: List[EntityCandidate] = []

        # Check companies
        if entity_type in (EntityType.COMPANY, None):
            for key, c in cls.MOCK_COMPANIES.items():
                if key in q_clean or q_clean in c["name"].lower() or c["primary_domain"] in q_clean:
                    all_candidates.append(
                        EntityCandidate(
                            candidate_id=f"comp_{key}",
                            entity_type=EntityType.COMPANY,
                            name=c["name"],
                            primary_domain=c["primary_domain"],
                            headline=c["description"][:80],
                            location=c["headquarters"],
                            confidence_score=0.95,
                            is_mock=True,
                            data_origin="DEMO",
                            source="DEMO Mock Provider",
                            verification_status="VERIFIED",
                            buying_intent_status="INTELLIGENCE_ONLY",
                            provenance={
                                "name": "DEMO_FIXTURE",
                                "primary_domain": "DEMO_FIXTURE",
                                "location": "DEMO_FIXTURE",
                            },
                            field_verification={
                                "name": "VERIFIED",
                                "primary_domain": "VERIFIED",
                                "location": "VERIFIED",
                                "employee_count": "VERIFIED",
                                "industry": "VERIFIED",
                            },
                            raw_data=c,
                        )
                    )

        # Check people
        if entity_type in (EntityType.PERSON, None):
            person_slug = q_clean.replace("https://www.linkedin.com/in/", "").replace("https://linkedin.com/in/", "").strip("/")
            for key, p in cls.MOCK_PEOPLE.items():
                p_url = p.get("linkedin_url", "").lower()
                p_name = p["full_name"].lower()
                if (
                    key in q_clean
                    or p_name in q_clean
                    or q_clean in p_name
                    or (p_url and (q_clean in p_url or person_slug in p_url or person_slug == key.replace(" ", "")))
                ):
                    all_candidates.append(
                        EntityCandidate(
                            candidate_id=f"person_{key.replace(' ', '_')}",
                            entity_type=EntityType.PERSON,
                            name=p["full_name"],
                            current_title=p["current_title"],
                            company_name=p["current_company"],
                            headline=p["headline"],
                            profile_url=p["linkedin_url"],
                            location=p["location"],
                            confidence_score=0.95,
                            is_mock=True,
                            data_origin="DEMO",
                            source="DEMO Mock Provider",
                            verification_status="VERIFIED",
                            buying_intent_status="INTELLIGENCE_ONLY",
                            provenance={
                                "name": "DEMO_FIXTURE",
                                "current_title": "DEMO_FIXTURE",
                                "current_company": "DEMO_FIXTURE",
                            },
                            field_verification={
                                "name": "VERIFIED",
                                "current_title": "VERIFIED",
                                "company_name": "VERIFIED",
                                "profile_url": "VERIFIED",
                                "location": "VERIFIED",
                            },
                            raw_data=p,
                        )
                    )

        # Handle mock offset pagination
        offset = 0
        if cursor and cursor.startswith("mock_offset_"):
            try:
                offset = int(cursor.split("_")[-1])
            except ValueError:
                offset = 0

        paged = all_candidates[offset : offset + limit]
        next_cursor = None
        if offset + limit < len(all_candidates):
            next_cursor = f"mock_offset_{offset + limit}"

        return PaginatedCandidateList(paged, next_cursor=next_cursor, total_count=len(all_candidates))

    @classmethod
    def enrich_company(
        cls,
        identifier: str,
        level: EnrichmentLevel = EnrichmentLevel.LEVEL_2_STANDARD,
    ) -> CompanyIntelligenceProfile:
        q_clean = identifier.lower().strip().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]

        matched_key = None
        for key, c in cls.MOCK_COMPANIES.items():
            if key in q_clean or c["primary_domain"] in q_clean:
                matched_key = key
                break

        if matched_key:
            data = cls.MOCK_COMPANIES[matched_key]
            techs = [TechnographicItem(**t) for t in data.get("technographics", [])]
            fundings = [FundingRoundItem(**f) for f in data.get("funding_rounds", [])]
            jobs = [JobListingItem(**j) for j in data.get("active_jobs", [])]

            evidence_list = [
                IntelligenceEvidenceItem(
                    data_category="FIRMOGRAPHICS",
                    claim=f"Operating domain verified as {data['primary_domain']}",
                    source_url=data.get("website"),
                    confidence=0.95,
                    verification_classification=VerificationClassification.VERIFIED,
                    metadata={"headcount": data.get("headcount"), "industry": data.get("industry")},
                )
            ]
            for t in techs:
                evidence_list.append(
                    IntelligenceEvidenceItem(
                        data_category="TECHNOGRAPHICS",
                        claim=f"Installed software: {t.name} ({t.category})",
                        source_url=t.source_url or data.get("website"),
                        confidence=0.90 if t.classification == VerificationClassification.VERIFIED else 0.70,
                        verification_classification=t.classification,
                    )
                )

            credits = 1.0 if level == EnrichmentLevel.LEVEL_2_STANDARD else 15.0

            return CompanyIntelligenceProfile(
                entity_id=f"comp_{matched_key}",
                name=data["name"],
                primary_domain=data["primary_domain"],
                website=data.get("website"),
                linkedin_url=data.get("linkedin_url"),
                description=data.get("description"),
                industry=data.get("industry"),
                headcount=data.get("headcount"),
                annual_revenue_range=data.get("annual_revenue_range"),
                headquarters=data.get("headquarters"),
                founding_year=data.get("founding_year"),
                technographics=techs,
                funding_rounds=fundings,
                total_funding_usd=data.get("total_funding_usd"),
                leadership=data.get("leadership", []),
                active_jobs=jobs,
                evidence=evidence_list,
                enrichment_level=level,
                credits_consumed=credits,
                data_freshness="REALTIME_CRAWL" if level == EnrichmentLevel.LEVEL_3_DEEP else "CACHED",
                is_mock=True,
                data_origin="DEMO",
                source="DEMO Mock Provider",
                verification_status="VERIFIED",
                buying_intent_status="INTELLIGENCE_ONLY",
                provenance={"name": "MOCK_FIXTURE", "primary_domain": "MOCK_FIXTURE"},
            )
        else:
            # Unknown entity in demo mode: return unverified profile without synthetic fabrication
            comp_name = identifier.strip()
            return CompanyIntelligenceProfile(
                entity_id=f"comp_{uuid.uuid4().hex[:8]}",
                name=comp_name,
                primary_domain=f"{comp_name.lower().replace(' ', '')}.com" if "." not in comp_name else comp_name,
                description=f"Company '{comp_name}' not found in demo fixtures.",
                enrichment_level=level,
                credits_consumed=0.0,
                data_freshness="UNVERIFIED",
                is_mock=True,
                data_origin="DEMO",
                source="DEMO Mock Provider",
                verification_status="UNVERIFIED",
                buying_intent_status="INTELLIGENCE_ONLY",
                provenance={"name": "QUERY_INPUT"},
            )

    @classmethod
    def enrich_person(
        cls,
        identifier: str,
        level: EnrichmentLevel = EnrichmentLevel.LEVEL_2_STANDARD,
    ) -> PersonIntelligenceProfile:
        q_clean = identifier.lower().strip()
        person_slug = q_clean.replace("https://www.linkedin.com/in/", "").replace("https://linkedin.com/in/", "").strip("/")

        matched_key = None
        for key, p in cls.MOCK_PEOPLE.items():
            p_url = p.get("linkedin_url", "").lower()
            p_name = p["full_name"].lower()
            if (
                key in q_clean
                or p_name in q_clean
                or (p_url and (q_clean in p_url or person_slug in p_url or person_slug == key.replace(" ", "")))
            ):
                matched_key = key
                break

        if matched_key:
            data = cls.MOCK_PEOPLE[matched_key]
            history = [WorkHistoryItem(**h) for h in data.get("work_history", [])]
            evidence = [
                IntelligenceEvidenceItem(
                    data_category="PROFESSIONAL_IDENTITY",
                    claim=f"{data['full_name']} verified as {data.get('current_title')} at {data.get('current_company')}",
                    source_url=data.get("linkedin_url"),
                    confidence=0.95,
                    verification_classification=VerificationClassification.VERIFIED,
                )
            ]
            credits = 1.0 if level == EnrichmentLevel.LEVEL_2_STANDARD else 12.0

            return PersonIntelligenceProfile(
                entity_id=f"person_{matched_key.replace(' ', '_')}",
                full_name=data["full_name"],
                current_title=data.get("current_title"),
                current_company=data.get("current_company"),
                headline=data.get("headline"),
                location=data.get("location"),
                linkedin_url=data.get("linkedin_url"),
                twitter_url=data.get("twitter_url"),
                verified_work_email=data.get("verified_work_email"),
                summary_bio=data.get("summary_bio"),
                is_decision_maker=data.get("is_decision_maker", False),
                decision_maker_score=data.get("decision_maker_score", 0.95),
                work_history=history,
                skills=data.get("skills", []),
                evidence=evidence,
                enrichment_level=level,
                credits_consumed=credits,
                data_freshness="REALTIME_CRAWL" if level == EnrichmentLevel.LEVEL_3_DEEP else "CACHED",
                is_mock=True,
                data_origin="DEMO",
                source="DEMO Mock Provider",
                verification_status="VERIFIED",
                buying_intent_status="INTELLIGENCE_ONLY",
                provenance={
                    "full_name": "MOCK_FIXTURE",
                    "current_title": "MOCK_FIXTURE",
                    "current_company": "MOCK_FIXTURE",
                    "linkedin_url": "MOCK_FIXTURE",
                },
            )
        else:
            # Unknown entity: never synthesize fake company or role (e.g. Apex Dynamics)
            name = identifier.title().strip()
            return PersonIntelligenceProfile(
                entity_id=f"person_{uuid.uuid4().hex[:8]}",
                full_name=name,
                current_title="Unverified Title",
                current_company="Unknown Entity",
                headline=f"Unverified entity profile for {name}",
                location="Location Unverified",
                linkedin_url=identifier if "http" in identifier else None,
                verified_work_email=None,
                summary_bio="Entity not recognized in demo fixtures. Identity unverified.",
                is_decision_maker=False,
                decision_maker_score=0.0,
                work_history=[],
                skills=[],
                evidence=[
                    IntelligenceEvidenceItem(
                        data_category="PROFESSIONAL_IDENTITY",
                        claim=f"No verified professional record found for {name}",
                        confidence=0.20,
                        verification_classification=VerificationClassification.UNKNOWN,
                    )
                ],
                enrichment_level=level,
                credits_consumed=0.0,
                data_freshness="UNVERIFIED",
                is_mock=True,
                data_origin="DEMO",
                source="DEMO Mock Provider",
                verification_status="UNVERIFIED",
                buying_intent_status="INTELLIGENCE_ONLY",
                provenance={"full_name": "QUERY_INPUT"},
            )
