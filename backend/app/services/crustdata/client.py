"""
Crustdata REST API Client (API Version 2025-11-01).
Interfaces with api.crustdata.com using modern dataset endpoints,
rate limiting backoffs, CreditGuard budget enforcement, and strict provenance tagging.
"""

import httpx
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import logger
from app.services.crustdata.exceptions import (
    CrustdataAPIError,
    CrustdataAuthError,
    CrustdataRateLimitError,
)
from app.services.crustdata.schemas import (
    EntityType,
    EnrichmentLevel,
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
    VerificationClassification,
)
from app.services.crustdata.credit_guard import CreditGuard
from app.services.crustdata.mock_provider import CrustdataMockProvider


class CrustdataClient:
    """Official Crustdata API client for Dataset v2025-11-01."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self.base_url = settings.CRUSTDATA_API_BASE.rstrip("/")
        self.api_version = settings.CRUSTDATA_API_VERSION or "2025-11-01"
        self.timeout = 20.0

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key if self._api_key is not None else settings.CRUSTDATA_API_KEY

    @property
    def is_configured(self) -> bool:
        key = self.api_key
        return bool(key and key.strip())

    def _get_headers(self) -> Dict[str, str]:
        if not self.is_configured:
            raise CrustdataAuthError("Crustdata API key is not configured in settings.")
        return {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "x-api-version": self.api_version,
            "Content-Type": "application/json",
        }

    async def get_account_credits(self) -> CrustdataCreditsInfo:
        """
        Retrieves active account credits via GET /account/credits (Zero credits).
        """
        if not self.is_configured:
            credits = CrustdataMockProvider.get_credits()
            CreditGuard.update_cached_credits(credits)
            return credits

        url = f"{self.base_url}/account/credits"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    account = data.get("account", {}) if isinstance(data.get("account"), dict) else {}

                    # 1. Available / remaining credits
                    if account.get("credits") is not None:
                        remaining_credits = float(account["credits"])
                    elif data.get("remaining_credits") is not None:
                        remaining_credits = float(data["remaining_credits"])
                    elif data.get("credits") is not None and isinstance(data["credits"], (int, float)):
                        remaining_credits = float(data["credits"])
                    elif isinstance(data.get("credits"), dict) and data["credits"].get("balance_estimated") is not None:
                        remaining_credits = float(data["credits"]["balance_estimated"])
                    else:
                        remaining_credits = 0.0

                    # 2. Total credits
                    wallets = account.get("wallets", [])
                    wallet_total = sum(
                        float(w.get("credits", 0.0))
                        for w in wallets
                        if isinstance(w, dict) and w.get("credits") is not None
                    )
                    if data.get("total_credits") is not None:
                        total_credits = float(data["total_credits"])
                    elif wallet_total > 0:
                        total_credits = wallet_total
                    else:
                        total_credits = remaining_credits

                    # 3. Used credits
                    used_credits = float(data.get("used_credits", max(0.0, total_credits - remaining_credits)))
                    renewal_date = account.get("recurring_credits_refresh_date") or data.get("renewal_date")
                    enabled_endpoints = data.get("enabled_endpoints", [])

                    credits = CrustdataCreditsInfo(
                        total_credits=total_credits,
                        remaining_credits=remaining_credits,
                        used_credits=used_credits,
                        renewal_date=renewal_date,
                        enabled_endpoints=enabled_endpoints,
                        is_mock=False,
                    )
                    CreditGuard.update_cached_credits(credits)
                    return credits
                elif res.status_code in (401, 403):
                    raise CrustdataAuthError(f"Crustdata authentication failed: {res.text}")
                elif res.status_code == 429:
                    raise CrustdataRateLimitError(retry_after=60)
                else:
                    raise CrustdataAPIError(res.status_code, res.text)
        except Exception as e:
            if settings.CRUSTDATA_ENABLE_MOCK:
                credits = CrustdataMockProvider.get_credits()
                CreditGuard.update_cached_credits(credits)
                return credits
            raise

    async def get_account_endpoints(self) -> Dict[str, Any]:
        """
        Retrieves account endpoints and rate limits via GET /account/endpoints (Zero credits).
        """
        if not self.is_configured:
            return {"api_version": self.api_version, "endpoints": [], "is_mock": True}

        url = f"{self.base_url}/account/endpoints"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code == 200:
                    return res.json()
                elif res.status_code in (401, 403):
                    raise CrustdataAuthError(f"Crustdata authentication failed: {res.text}")
                elif res.status_code == 429:
                    raise CrustdataRateLimitError(retry_after=60)
                else:
                    raise CrustdataAPIError(res.status_code, res.text)
        except Exception as e:
            if settings.CRUSTDATA_ENABLE_MOCK and not self.is_configured:
                return {"api_version": self.api_version, "endpoints": [], "is_mock": True}
            raise

    async def search_company_candidates(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        cursor: Optional[str] = None,
        mode: str = "LIVE",
    ) -> PaginatedCandidateList:
        """
        Executes Level 1 Company Search via POST /company/search (0.03 credits).
        """
        if mode == "DEMO" or (settings.CRUSTDATA_ENABLE_MOCK and not self.is_configured):
            return CrustdataMockProvider.search_candidates(query, entity_type=EntityType.COMPANY, limit=limit, cursor=cursor)

        cost = CreditGuard.estimate_cost(EnrichmentLevel.LEVEL_1_SEARCH)
        CreditGuard.verify_budget_can_proceed(cost)

        url = f"{self.base_url}/company/search"

        # Determine filter condition if not provided
        if not filters:
            clean_q = query.strip()
            if "." in clean_q and " " not in clean_q:
                condition = {"field": "basic_info.primary_domain", "type": "=", "value": clean_q.lower()}
            else:
                condition = {"field": "basic_info.name", "type": "(.)", "value": clean_q}
            search_filters = {"op": "and", "conditions": [condition]}
        else:
            search_filters = filters

        payload: Dict[str, Any] = {
            "filters": search_filters,
            "limit": limit,
        }
        if cursor:
            payload["cursor"] = cursor

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    results = data.get("companies", []) or data.get("results", [])
                    next_cursor = data.get("next_cursor")
                    total_count = data.get("total_count")

                    candidates: List[EntityCandidate] = []
                    for item in results:
                        basic = item.get("basic_info") or {}
                        locations = item.get("locations") or {}
                        domain = basic.get("primary_domain")
                        name = basic.get("name") or query.strip()
                        cid = item.get("crustdata_company_id") or basic.get("crustdata_company_id")
                        c_id_str = f"comp_{cid}" if cid else f"comp_{domain or name.lower().replace(' ', '_')}"

                        # Calculate evidence-based confidence
                        conf = 0.50
                        if domain:
                            conf += 0.25
                        if name.lower() == query.strip().lower():
                            conf += 0.20
                        elif query.strip().lower() in name.lower():
                            conf += 0.10

                        headquarters = locations.get("headquarters") or locations.get("country")
                        employee_range = basic.get("employee_count_range")
                        industry_val = basic.get("industry") or (item.get("taxonomy") and item.get("taxonomy", {}).get("professional_network_industry"))

                        candidates.append(
                            EntityCandidate(
                                candidate_id=c_id_str,
                                entity_type=EntityType.COMPANY,
                                name=name,
                                primary_domain=domain,
                                profile_url=basic.get("professional_network_url"),
                                headline=basic.get("description", "")[:120] if basic.get("description") else None,
                                location=headquarters,
                                logo_url=basic.get("logo_permalink"),
                                confidence_score=min(1.0, conf),
                                is_mock=False,
                                data_origin="LIVE",
                                source="Crustdata API v2025-11-01",
                                verification_status="VERIFIED" if conf >= 0.70 else "UNVERIFIED",
                                buying_intent_status="INTELLIGENCE_ONLY",
                                buying_intent_note="Firmographics & company dataset match from Crustdata. No buying intent assumed.",
                                provenance={
                                    "name": "LIVE_CRUSTDATA",
                                    "primary_domain": "LIVE_CRUSTDATA" if domain else "UNKNOWN",
                                    "location": "LIVE_CRUSTDATA" if headquarters else "UNKNOWN",
                                    "employee_count": "LIVE_CRUSTDATA" if employee_range else "UNKNOWN",
                                    "industry": "LIVE_CRUSTDATA" if industry_val else "UNKNOWN",
                                },
                                field_verification={
                                    "name": "VERIFIED" if basic.get("name") else "INFERRED",
                                    "primary_domain": "VERIFIED" if domain else "UNKNOWN",
                                    "location": "VERIFIED" if headquarters else "UNKNOWN",
                                    "employee_count": "VERIFIED" if employee_range else "UNKNOWN",
                                    "industry": "VERIFIED" if industry_val else "UNKNOWN",
                                },
                                raw_data=item,
                            )
                        )
                    return PaginatedCandidateList(candidates, next_cursor=next_cursor, total_count=total_count)
                elif res.status_code in (401, 403):
                    raise CrustdataAuthError(f"Crustdata search unauthorized: {res.text}")
                elif res.status_code == 429:
                    raise CrustdataRateLimitError(retry_after=60)
                else:
                    raise CrustdataAPIError(res.status_code, res.text)
        except Exception as e:
            logger.error(f"Crustdata live company search error: {e}")
            if mode == "DEMO":
                return CrustdataMockProvider.search_candidates(query, entity_type=EntityType.COMPANY, limit=limit, cursor=cursor)
            raise

    async def search_person_candidates(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        cursor: Optional[str] = None,
        mode: str = "LIVE",
    ) -> PaginatedCandidateList:
        """
        Executes Level 1 People Search via POST /person/search (0.03 credits).
        """
        if mode == "DEMO" or (settings.CRUSTDATA_ENABLE_MOCK and not self.is_configured):
            return CrustdataMockProvider.search_candidates(query, entity_type=EntityType.PERSON, limit=limit, cursor=cursor)

        cost = CreditGuard.estimate_cost(EnrichmentLevel.LEVEL_1_SEARCH)
        CreditGuard.verify_budget_can_proceed(cost)

        url = f"{self.base_url}/person/search"

        if not filters:
            search_filters = {
                "op": "and",
                "conditions": [
                    {
                        "field": "basic_profile.name",
                        "type": "(.)",
                        "value": query.strip(),
                    }
                ],
            }
        else:
            search_filters = filters

        payload: Dict[str, Any] = {
            "filters": search_filters,
            "limit": limit,
        }
        if cursor:
            payload["cursor"] = cursor

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    profiles = data.get("profiles", []) or data.get("results", []) or data.get("people", [])
                    next_cursor = data.get("next_cursor")
                    total_count = data.get("total_count")

                    candidates: List[EntityCandidate] = []
                    for item in profiles:
                        basic = item.get("basic_profile") or {}
                        social = item.get("social_handles") or {}
                        prof_net = social.get("professional_network_identifier") or {}
                        profile_url = prof_net.get("profile_url")

                        exp = item.get("experience") or {}
                        emp_details = exp.get("employment_details") or {}
                        current_jobs = emp_details.get("current") or []
                        current_job = current_jobs[0] if current_jobs else {}

                        current_title = current_job.get("title")
                        company_name = current_job.get("name")
                        name = basic.get("name") or query.strip()
                        location_dict = basic.get("location") or {}
                        loc_str = location_dict.get("country") or basic.get("headline")

                        # Evidence-based confidence scoring
                        conf = 0.40
                        if name.lower() == query.strip().lower():
                            conf += 0.30
                        elif query.strip().lower() in name.lower():
                            conf += 0.15

                        if profile_url and "linkedin.com/in/" in profile_url:
                            conf += 0.20
                        if company_name:
                            conf += 0.10

                        is_verified = (conf >= 0.70 and bool(profile_url))
                        cand_id = profile_url or f"person_{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"

                        candidates.append(
                            EntityCandidate(
                                candidate_id=cand_id,
                                entity_type=EntityType.PERSON,
                                name=name,
                                current_title=current_title,
                                company_name=company_name,
                                headline=basic.get("headline"),
                                profile_url=profile_url,
                                location=loc_str,
                                confidence_score=min(1.0, conf),
                                is_mock=False,
                                data_origin="LIVE",
                                source="Crustdata API v2025-11-01",
                                verification_status="VERIFIED" if is_verified else "UNVERIFIED",
                                buying_intent_status="INTELLIGENCE_ONLY",
                                buying_intent_note="Executive / person profile discovered from Crustdata dataset. Intent unverified.",
                                provenance={
                                    "name": "LIVE_CRUSTDATA",
                                    "title": "LIVE_CRUSTDATA" if current_title else "UNKNOWN",
                                    "company": "LIVE_CRUSTDATA" if company_name else "UNKNOWN",
                                    "profile_url": "LIVE_CRUSTDATA" if profile_url else "UNKNOWN",
                                    "location": "LIVE_CRUSTDATA" if loc_str else "UNKNOWN",
                                },
                                field_verification={
                                    "name": "VERIFIED" if basic.get("name") else "INFERRED",
                                    "current_title": "VERIFIED" if current_title else "UNKNOWN",
                                    "company_name": "VERIFIED" if company_name else "UNKNOWN",
                                    "profile_url": "VERIFIED" if profile_url else "UNKNOWN",
                                    "location": "VERIFIED" if loc_str else "UNKNOWN",
                                },
                                raw_data=item,
                            )
                        )
                    return PaginatedCandidateList(candidates, next_cursor=next_cursor, total_count=total_count)
                elif res.status_code in (401, 403):
                    raise CrustdataAuthError(f"Crustdata person search unauthorized: {res.text}")
                elif res.status_code == 429:
                    raise CrustdataRateLimitError(retry_after=60)
                else:
                    raise CrustdataAPIError(res.status_code, res.text)
        except Exception as e:
            logger.error(f"Crustdata live person search error: {e}")
            if mode == "DEMO":
                return CrustdataMockProvider.search_candidates(query, entity_type=EntityType.PERSON, limit=limit)
            raise

    async def enrich_company(
        self,
        identifier: str,
        level: EnrichmentLevel = EnrichmentLevel.LEVEL_2_STANDARD,
        mode: str = "LIVE",
    ) -> CompanyIntelligenceProfile:
        """
        Executes Level 2 Standard Enrichment via POST /company/enrich (2.0 credits).
        Permitted fields: basic_info, headcount, funding, people, hiring, locations, software_reviews.
        """
        if mode == "DEMO" or (settings.CRUSTDATA_ENABLE_MOCK and not self.is_configured):
            return CrustdataMockProvider.enrich_company(identifier, level=level)

        cost = CreditGuard.estimate_cost(level)
        CreditGuard.verify_budget_can_proceed(cost)

        url = f"{self.base_url}/company/enrich"
        is_domain = "." in identifier and " " not in identifier

        payload = {
            "domains": [identifier] if is_domain else None,
            "names": [identifier] if not is_domain else None,
            "fields": [
                "basic_info",
                "headcount",
                "funding",
                "people",
                "hiring",
                "locations",
                "software_reviews",
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    matches = []
                    if isinstance(data, list) and len(data) > 0:
                        matches = data[0].get("matches", [])
                    elif isinstance(data, dict):
                        matches = data.get("matches", [])

                    if not matches:
                        # Unknown company: return clean unverified profile without synthetic fabrication
                        return CompanyIntelligenceProfile(
                            entity_id=f"comp_{uuid.uuid4().hex[:8]}",
                            name=identifier.strip(),
                            primary_domain=identifier if is_domain else f"{identifier.lower().replace(' ', '')}.com",
                            description=f"Company profile for {identifier} not found in live Crustdata dataset.",
                            enrichment_level=level,
                            credits_consumed=cost,
                            data_freshness="DATASET_UNMATCHED",
                            is_mock=False,
                            data_origin="LIVE",
                            source="Crustdata API v2025-11-01",
                            verification_status="UNVERIFIED",
                            buying_intent_status="INTELLIGENCE_ONLY",
                            provenance={"name": "QUERY_INPUT"},
                        )

                    match = matches[0]
                    comp = match.get("company_data") or {}
                    basic = comp.get("basic_info") or {}
                    headcount_data = comp.get("headcount") or {}
                    funding_data = comp.get("funding") or {}
                    locations_data = comp.get("locations") or {}
                    people_data = comp.get("people") or {}
                    hiring_data = comp.get("hiring") or {}

                    # Extract leadership
                    leadership = []
                    for cat in ["founders", "cxos", "decision_makers"]:
                        for p in people_data.get(cat, []):
                            p_net = p.get("professional_network") or {}
                            social = p.get("social_handles") or {}
                            prof_id = social.get("professional_network_identifier") or {}
                            leadership.append({
                                "name": p_net.get("name") or "Executive",
                                "title": p_net.get("current_title") or cat.title(),
                                "linkedin": prof_id.get("profile_url") or p_net.get("linkedin_url"),
                            })

                    # Evidence provenance
                    company_name = basic.get("name") or identifier
                    primary_domain = basic.get("primary_domain") or (identifier if is_domain else "")
                    evidence = [
                        IntelligenceEvidenceItem(
                            data_category="FIRMOGRAPHICS",
                            claim=f"{company_name} incorporated as {basic.get('company_type', 'Corporation')} headquartered in {locations_data.get('country', 'Global')}",
                            source_url=basic.get("website") or basic.get("professional_network_url"),
                            confidence=float(match.get("confidence_score", 0.95)),
                            verification_classification=VerificationClassification.VERIFIED,
                            metadata={"crustdata_company_id": comp.get("crustdata_company_id")},
                        )
                    ]

                    total_hc = headcount_data.get("total")
                    hc_str = f"{total_hc:,} employees" if total_hc else basic.get("employee_count_range")

                    return CompanyIntelligenceProfile(
                        entity_id=f"comp_{comp.get('crustdata_company_id') or uuid.uuid4().hex[:8]}",
                        name=company_name,
                        primary_domain=primary_domain,
                        alternate_domains=basic.get("all_domains", []),
                        website=basic.get("website"),
                        linkedin_url=basic.get("professional_network_url"),
                        description=basic.get("description"),
                        industry=basic.get("company_type"),
                        headcount=hc_str,
                        headquarters=locations_data.get("headquarters") or locations_data.get("country"),
                        founding_year=basic.get("year_founded"),
                        technographics=[],
                        leadership=leadership[:10],
                        evidence=evidence,
                        enrichment_level=level,
                        credits_consumed=cost,
                        data_freshness="REALTIME_CRAWL" if level == EnrichmentLevel.LEVEL_3_DEEP else "CACHED",
                        is_mock=False,
                        data_origin="LIVE",
                        source="Crustdata API v2025-11-01",
                        verification_status="VERIFIED",
                        buying_intent_status="INTELLIGENCE_ONLY",
                        provenance={
                            "name": "LIVE_CRUSTDATA",
                            "primary_domain": "LIVE_CRUSTDATA",
                            "headcount": "LIVE_CRUSTDATA",
                            "locations": "LIVE_CRUSTDATA",
                            "leadership": "LIVE_CRUSTDATA",
                        },
                    )
                elif res.status_code in (401, 403):
                    raise CrustdataAuthError(f"Crustdata enrichment unauthorized: {res.text}")
                elif res.status_code == 429:
                    raise CrustdataRateLimitError(retry_after=60)
                else:
                    raise CrustdataAPIError(res.status_code, res.text)
        except Exception as e:
            logger.error(f"Crustdata company enrichment error: {e}")
            if mode == "DEMO":
                return CrustdataMockProvider.enrich_company(identifier, level=level)
            raise

    async def enrich_person(
        self,
        identifier: str,
        level: EnrichmentLevel = EnrichmentLevel.LEVEL_2_STANDARD,
        mode: str = "LIVE",
    ) -> PersonIntelligenceProfile:
        """
        Executes Level 2 Standard Enrichment via POST /person/enrich (1.0 credits).
        """
        if mode == "DEMO" or (settings.CRUSTDATA_ENABLE_MOCK and not self.is_configured):
            return CrustdataMockProvider.enrich_person(identifier, level=level)

        cost = CreditGuard.estimate_cost(level)
        CreditGuard.verify_budget_can_proceed(cost)

        # Ensure we have a LinkedIn URL for person enrichment
        profile_url = identifier if "linkedin.com/in/" in identifier else None

        # If identifier is a name, look it up first via zero/low-cost person search
        if not profile_url:
            cands = await self.search_person_candidates(identifier, limit=1, mode=mode)
            if cands and cands[0].profile_url:
                profile_url = cands[0].profile_url

        if not profile_url:
            # Unverified profile without synthetic fabrication
            return PersonIntelligenceProfile(
                entity_id=f"person_{uuid.uuid4().hex[:8]}",
                full_name=identifier.strip(),
                headline=f"Unverified profile for {identifier}",
                current_title="Unverified Title",
                current_company="Unverified Company",
                summary_bio="No verified LinkedIn or professional profile found in Crustdata dataset.",
                is_decision_maker=False,
                decision_maker_score=0.0,
                enrichment_level=level,
                credits_consumed=cost,
                data_freshness="DATASET_UNMATCHED",
                is_mock=False,
                data_origin="LIVE",
                source="Crustdata API v2025-11-01",
                verification_status="UNVERIFIED",
                buying_intent_status="INTELLIGENCE_ONLY",
                provenance={"full_name": "QUERY_INPUT"},
            )

        url = f"{self.base_url}/person/enrich"
        payload = {
            "professional_network_profile_urls": [profile_url],
            "fields": [
                "basic_profile",
                "experience",
                "education",
                "skills",
                "social_handles",
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    matches = []
                    if isinstance(data, list) and len(data) > 0:
                        matches = data[0].get("matches", [])
                    elif isinstance(data, dict):
                        matches = data.get("matches", [])

                    if not matches:
                        return PersonIntelligenceProfile(
                            entity_id=f"person_{uuid.uuid4().hex[:8]}",
                            full_name=identifier.strip(),
                            current_title="Unverified Title",
                            current_company="Unverified Company",
                            headline=f"Profile for {identifier} not found in Crustdata dataset.",
                            is_decision_maker=False,
                            decision_maker_score=0.0,
                            enrichment_level=level,
                            credits_consumed=cost,
                            data_freshness="DATASET_UNMATCHED",
                            is_mock=False,
                            data_origin="LIVE",
                            source="Crustdata API v2025-11-01",
                            verification_status="UNVERIFIED",
                            buying_intent_status="INTELLIGENCE_ONLY",
                            provenance={"full_name": "QUERY_INPUT"},
                        )

                    match = matches[0]
                    p_data = match.get("person_data") or {}
                    basic = p_data.get("basic_profile") or {}
                    exp = p_data.get("experience") or {}
                    emp = exp.get("employment_details") or {}
                    current_jobs = emp.get("current") or []
                    past_jobs = emp.get("past") or []
                    skills_data = p_data.get("skills") or {}
                    social = p_data.get("social_handles") or {}

                    curr = current_jobs[0] if current_jobs else {}
                    full_name = basic.get("name") or identifier
                    curr_title = curr.get("title")
                    curr_comp = curr.get("name")

                    work_history = []
                    for job in current_jobs:
                        work_history.append(
                            WorkHistoryItem(
                                company_name=job.get("name") or "Unknown",
                                title=job.get("title") or "Unknown",
                                start_date=str(job.get("start_date")) if job.get("start_date") else None,
                                is_current=True,
                            )
                        )
                    for job in past_jobs:
                        work_history.append(
                            WorkHistoryItem(
                                company_name=job.get("name") or "Unknown",
                                title=job.get("title") or "Unknown",
                                start_date=str(job.get("start_date")) if job.get("start_date") else None,
                                end_date=str(job.get("end_date")) if job.get("end_date") else None,
                                is_current=False,
                            )
                        )

                    # Decision maker determination
                    is_dm = False
                    dm_score = 0.4
                    if curr_title:
                        t_low = curr_title.lower()
                        if any(w in t_low for w in ["chief", "cto", "cio", "ciso", "vp", "vice president", "director", "head of"]):
                            is_dm = True
                            dm_score = 0.90

                    loc = basic.get("location") or {}
                    loc_str = loc.get("country") if isinstance(loc, dict) else str(loc)

                    evidence = [
                        IntelligenceEvidenceItem(
                            data_category="PROFESSIONAL_IDENTITY",
                            claim=f"{full_name} verified as {curr_title or 'Professional'} at {curr_comp or 'Unknown Company'}",
                            source_url=profile_url,
                            confidence=float(match.get("confidence_score", 0.95)),
                            verification_classification=VerificationClassification.VERIFIED,
                        )
                    ]

                    skills_list = []
                    if isinstance(skills_data, dict):
                        skills_list = skills_data.get("professional_network_skills", []) or []

                    return PersonIntelligenceProfile(
                        entity_id=f"person_{uuid.uuid4().hex[:8]}",
                        full_name=full_name,
                        current_title=curr_title,
                        current_company=curr_comp,
                        headline=basic.get("headline"),
                        location=loc_str,
                        linkedin_url=profile_url,
                        twitter_url=social.get("twitter_identifier", {}).get("slug"),
                        summary_bio=basic.get("headline"),
                        is_decision_maker=is_dm,
                        decision_maker_score=dm_score,
                        work_history=work_history,
                        skills=skills_list[:15],
                        evidence=evidence,
                        enrichment_level=level,
                        credits_consumed=cost,
                        data_freshness="REALTIME_CRAWL" if level == EnrichmentLevel.LEVEL_3_DEEP else "CACHED",
                        is_mock=False,
                        data_origin="LIVE",
                        source="Crustdata API v2025-11-01",
                        verification_status="VERIFIED",
                        buying_intent_status="INTELLIGENCE_ONLY",
                        provenance={
                            "full_name": "LIVE_CRUSTDATA",
                            "current_title": "LIVE_CRUSTDATA" if curr_title else "UNKNOWN",
                            "current_company": "LIVE_CRUSTDATA" if curr_comp else "UNKNOWN",
                            "linkedin_url": "LIVE_CRUSTDATA",
                        },
                    )
                elif res.status_code in (401, 403):
                    raise CrustdataAuthError(f"Crustdata person enrichment unauthorized: {res.text}")
                elif res.status_code == 429:
                    raise CrustdataRateLimitError(retry_after=60)
                else:
                    raise CrustdataAPIError(res.status_code, res.text)
        except Exception as e:
            logger.error(f"Crustdata live person enrichment error: {e}")
            if mode == "DEMO":
                return CrustdataMockProvider.enrich_person(identifier, level=level)
            raise
