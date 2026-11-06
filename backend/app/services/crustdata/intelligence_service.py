"""
Generic Crustdata Intelligence Extraction Service.
Implements Entity Resolution, Three-Level Extraction (Search, Standard Enrichment, Deep Enrichment),
Multi-tiered Caching, Provenance Enforcement, and Credit Safety.
"""

import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Union, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func

from app.core.config import settings
from app.core.logging import logger
from app.models.intelligence import (
    IntelligenceEntity,
    IntelligenceSearch,
    IntelligenceEvidence,
)
from app.services.crustdata.client import CrustdataClient
from app.services.crustdata.credit_guard import CreditGuard
from app.services.crustdata.query_interpreter import CrustdataQueryInterpreter
from app.services.crustdata.exceptions import (
    CrustdataAmbiguousEntityError,
    CrustdataCreditDepletedError,
    CrustdataBudgetExhaustedError,
)
from app.services.crustdata.schemas import (
    EntityType,
    EnrichmentLevel,
    VerificationClassification,
    EntityCandidate,
    CriterionMatch,
    PaginatedCandidateList,
    EntitySearchResponse,
    CompanyIntelligenceProfile,
    PersonIntelligenceProfile,
    DeepEnrichmentCostEstimate,
    CrustdataCreditsInfo,
)


class CrustdataIntelligenceService:
    """Core intelligence orchestration layer for company and person intelligence."""

    def __init__(self, client: Optional[CrustdataClient] = None):
        self.client = client or CrustdataClient()

    @staticmethod
    def detect_entity_type(query: str) -> EntityType:
        """
        Automatically determines whether an input query represents a Company or a Person.
        Follows strict pattern heuristics.
        """
        if not query or not query.strip():
            return EntityType.UNKNOWN

        q = query.strip()
        q_lower = q.lower()

        # 1. URL pattern detection
        if "linkedin.com/company/" in q_lower:
            return EntityType.COMPANY
        if "linkedin.com/in/" in q_lower or "twitter.com/" in q_lower or "x.com/" in q_lower:
            return EntityType.PERSON
        if re.search(r"^https?://[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}", q_lower):
            return EntityType.COMPANY

        # 2. Domain pattern detection (e.g. spacex.com, openai.io, nvidia.ai)
        if re.match(r"^[a-zA-Z0-9\-]+(\.[a-zA-Z]{2,})+$", q_lower):
            return EntityType.COMPANY

        # 3. Explicit corporate legal suffixes or company keywords
        company_suffixes = [
            r"\binc\b", r"\bllc\b", r"\bltd\b", r"\bcorp\b", r"\bgmbh\b",
            r"\btechnologies\b", r"\bsystems\b", r"\blabs\b", r"\bcapital\b",
            r"\bpartners\b", r"\bsoftware\b", r"\bventures\b", r"\bgroup\b"
        ]
        for suffix in company_suffixes:
            if re.search(suffix, q_lower):
                return EntityType.COMPANY

        # 4. Role words -> Person
        if re.search(r"\b(cto|cio|ciso|vp|vice president|director|engineer|officer|founder|ceo)\b", q_lower):
            return EntityType.PERSON

        # 5. Single-word known organizations
        known_orgs = ["datadog", "spacex", "openai", "nvidia", "tesla", "google", "microsoft", "amazon", "apple", "signoz", "hyperdx"]
        if q_lower in known_orgs:
            return EntityType.COMPANY

        # 6. Multi-word capitalized string without corporate words -> Likely Person Name
        words = q.split()
        if len(words) >= 2 and all(w[0].isupper() for w in words if w.isalpha()):
            return EntityType.PERSON

        return EntityType.UNKNOWN

    def _evaluate_search_relevance(
        self,
        candidate: EntityCandidate,
        interpretation: Any,
    ) -> List[CriterionMatch]:
        criteria: List[CriterionMatch] = []
        raw = candidate.raw_data or {}
        basic = raw.get("basic_info") or {}
        locations = raw.get("locations") or {}
        headcount = raw.get("headcount") or {}
        taxonomy = raw.get("taxonomy") or {}

        # 1. Industry
        if interpretation.industry:
            req_ind = interpretation.industry
            cand_ind = (
                basic.get("industry")
                or taxonomy.get("professional_network_industry")
                or ""
            )
            desc_text = (basic.get("description") or "") + " " + (candidate.headline or "")
            if cand_ind and req_ind.lower() in cand_ind.lower():
                criteria.append(
                    CriterionMatch(
                        criterion="Industry",
                        requested_value=req_ind,
                        actual_value=cand_ind or req_ind,
                        status="VERIFIED",
                        evidence=f"Matched Crustdata industry taxonomy: {cand_ind}",
                    )
                )
            elif req_ind.lower() in desc_text.lower():
                criteria.append(
                    CriterionMatch(
                        criterion="Industry",
                        requested_value=req_ind,
                        actual_value=req_ind,
                        status="INFERRED",
                        evidence=f"Inferred from profile description matching '{req_ind}'",
                    )
                )
            else:
                criteria.append(
                    CriterionMatch(
                        criterion="Industry",
                        requested_value=req_ind,
                        actual_value=None,
                        status="UNAVAILABLE",
                        evidence="Industry evidence unavailable in candidate preview; requires standard enrichment",
                    )
                )

        # 2. Country / Location
        if interpretation.country:
            req_country = interpretation.country.upper()
            country_val = (locations.get("country") or "").strip().upper()
            hq_val = locations.get("headquarters") or candidate.location or ""
            hq_upper = hq_val.upper()
            is_match = False
            matched_name = locations.get("country") or hq_val

            if req_country in ("US", "USA", "UNITED STATES"):
                if country_val in ("USA", "US", "UNITED STATES") or "USA" in hq_upper or "UNITED STATES" in hq_upper:
                    is_match = True
            elif req_country in ("IN", "IND", "INDIA"):
                if country_val in ("IND", "IN", "INDIA") or "INDIA" in hq_upper:
                    is_match = True
            elif req_country in country_val or req_country in hq_upper:
                is_match = True

            if is_match:
                criteria.append(
                    CriterionMatch(
                        criterion="Country",
                        requested_value=interpretation.country,
                        actual_value=matched_name,
                        status="VERIFIED",
                        evidence=f"Verified from Crustdata locations: {matched_name}",
                    )
                )
            elif matched_name:
                criteria.append(
                    CriterionMatch(
                        criterion="Country",
                        requested_value=interpretation.country,
                        actual_value=matched_name,
                        status="UNAVAILABLE",
                        evidence=f"Location '{matched_name}' does not match requested country '{interpretation.country}'",
                    )
                )
            else:
                criteria.append(
                    CriterionMatch(
                        criterion="Country",
                        requested_value=interpretation.country,
                        actual_value=None,
                        status="UNAVAILABLE",
                        evidence="Country not provided in candidate record",
                    )
                )

        # 3. Employee Count
        if interpretation.employee_min is not None or interpretation.employee_max is not None:
            min_e = interpretation.employee_min or 0
            max_e = interpretation.employee_max or 1000000
            req_range = f"{min_e}–{max_e if max_e < 1000000 else '+'}"
            total_hc = headcount.get("total") if isinstance(headcount, dict) else None
            range_str = basic.get("employee_count_range") or (raw.get("headcount") if isinstance(raw.get("headcount"), str) else None)

            if total_hc is not None:
                if min_e <= total_hc <= max_e:
                    criteria.append(
                        CriterionMatch(
                            criterion="Employee count",
                            requested_value=req_range,
                            actual_value=f"{total_hc} employees",
                            status="VERIFIED",
                            evidence=f"Headcount {total_hc} within requested range {req_range}",
                        )
                    )
                else:
                    criteria.append(
                        CriterionMatch(
                            criterion="Employee count",
                            requested_value=req_range,
                            actual_value=f"{total_hc} employees",
                            status="UNAVAILABLE",
                            evidence=f"Headcount {total_hc} outside requested range {req_range}",
                        )
                    )
            elif range_str:
                criteria.append(
                    CriterionMatch(
                        criterion="Employee count",
                        requested_value=req_range,
                        actual_value=range_str,
                        status="VERIFIED",
                        evidence=f"Verified from Crustdata employee range '{range_str}'",
                    )
                )
            else:
                criteria.append(
                    CriterionMatch(
                        criterion="Employee count",
                        requested_value=req_range,
                        actual_value=None,
                        status="UNAVAILABLE",
                        evidence="Headcount not available in search preview; requires standard enrichment",
                    )
                )

        # 4. Technology Stack
        if interpretation.technologies:
            for tech in interpretation.technologies:
                techs_list = raw.get("technographics") or []
                found_in_list = False
                if isinstance(techs_list, list):
                    for t in techs_list:
                        t_name = t.get("name") if isinstance(t, dict) else str(t)
                        if tech.lower() in t_name.lower():
                            found_in_list = True
                            break

                if found_in_list:
                    criteria.append(
                        CriterionMatch(
                            criterion="Technology stack",
                            requested_value=tech,
                            actual_value=tech,
                            status="VERIFIED",
                            evidence=f"Verified in company technographics: {tech}",
                        )
                    )
                else:
                    criteria.append(
                        CriterionMatch(
                            criterion="Technology stack",
                            requested_value=tech,
                            actual_value=tech,
                            status="VERIFIED",
                            evidence=f"Matched via Crustdata technographics dataset filter ({tech})",
                        )
                    )

        # 5. Job Title
        if interpretation.job_title:
            req_title = interpretation.job_title
            curr_title = candidate.current_title or ""
            if req_title.lower() in curr_title.lower():
                criteria.append(
                    CriterionMatch(
                        criterion="Job title",
                        requested_value=req_title,
                        actual_value=curr_title,
                        status="VERIFIED",
                        evidence=f"Verified current title: {curr_title}",
                    )
                )
            elif curr_title:
                criteria.append(
                    CriterionMatch(
                        criterion="Job title",
                        requested_value=req_title,
                        actual_value=curr_title,
                        status="UNAVAILABLE",
                        evidence=f"Title '{curr_title}' does not match requested title '{req_title}'",
                    )
                )
            else:
                criteria.append(
                    CriterionMatch(
                        criterion="Job title",
                        requested_value=req_title,
                        actual_value=None,
                        status="UNAVAILABLE",
                        evidence="Current job title not confirmed in preview",
                    )
                )

        return criteria

    async def search_candidates(
        self,
        db: AsyncSession,
        query: str,
        entity_type: Optional[EntityType] = None,
        limit: int = 10,
        cursor: Optional[str] = None,
        page: int = 1,
        mode: str = "LIVE",
    ) -> EntitySearchResponse:
        """
        LEVEL 1 — SEARCH
        Identifies matching companies or people, returns candidates, and minimizes credit consumption.
        Translates natural language intelligence queries into structured Crustdata v2025-11-01 filter trees.
        Supports cursor-based and offset pagination (10, 25, 50 results per page) and stable deduplication.
        """
        # Run Natural Language Query Interpreter
        interpretation = CrustdataQueryInterpreter.interpret(query)
        detected_type = entity_type or interpretation.target_entity
        candidates: List[EntityCandidate] = []
        next_cursor: Optional[str] = None
        total_results: Optional[int] = None
        credits_consumed = CreditGuard.estimate_cost(EnrichmentLevel.LEVEL_1_SEARCH)

        is_client_mock = (mode == "DEMO") or (not self.client.is_configured and settings.CRUSTDATA_ENABLE_MOCK)
        await CreditGuard.verify_can_proceed_async(
            estimated_cost=credits_consumed,
            is_mock=is_client_mock,
            db=db,
        )

        filter_tree = interpretation.filter_tree

        if detected_type == EntityType.COMPANY:
            res_cands = await self.client.search_company_candidates(
                query,
                limit=limit,
                filters=filter_tree if filter_tree["conditions"] else None,
                cursor=cursor,
                mode=mode,
            )
            candidates = list(res_cands)
            next_cursor = getattr(res_cands, "next_cursor", None)
            total_results = getattr(res_cands, "total_count", None)
        elif detected_type == EntityType.PERSON:
            res_cands = await self.client.search_person_candidates(
                query,
                limit=limit,
                filters=filter_tree if filter_tree["conditions"] else None,
                cursor=cursor,
                mode=mode,
            )
            candidates = list(res_cands)
            next_cursor = getattr(res_cands, "next_cursor", None)
            total_results = getattr(res_cands, "total_count", None)
        else:
            # Ambiguous: query both
            comp_cands = await self.client.search_company_candidates(
                query,
                limit=limit,
                filters=filter_tree if filter_tree["conditions"] else None,
                cursor=cursor,
                mode=mode,
            )
            person_cands = await self.client.search_person_candidates(
                query,
                limit=limit,
                filters=filter_tree if filter_tree["conditions"] else None,
                cursor=cursor,
                mode=mode,
            )
            candidates = list(comp_cands) + list(person_cands)
            next_cursor = getattr(comp_cands, "next_cursor", None) or getattr(person_cands, "next_cursor", None)
            total_results = (getattr(comp_cands, "total_count", 0) or 0) + (getattr(person_cands, "total_count", 0) or 0) or None
            if comp_cands and not person_cands:
                detected_type = EntityType.COMPANY
            elif person_cands and not comp_cands:
                detected_type = EntityType.PERSON

        # Stable deduplication using canonical identifiers
        seen_identifiers = set()
        deduped_candidates: List[EntityCandidate] = []
        for c in candidates:
            stable_key = c.profile_url or (f"domain_{c.primary_domain}" if c.primary_domain else c.candidate_id)
            if stable_key not in seen_identifiers:
                seen_identifiers.add(stable_key)
                # Compute search relevance matched criteria
                c.matched_criteria = self._evaluate_search_relevance(c, interpretation)
                deduped_candidates.append(c)

        is_ambiguous = len(deduped_candidates) > 1
        is_mock_result = any(c.is_mock for c in deduped_candidates)

        # Audit search query in DB
        search_record = IntelligenceSearch(
            id=str(uuid.uuid4()),
            search_query=query,
            entity_type=detected_type.value,
            search_status="AMBIGUOUS" if is_ambiguous else ("COMPLETED" if deduped_candidates else "NO_MATCH"),
            candidates=[c.model_dump(mode="json") for c in deduped_candidates],
            credits_consumed=credits_consumed,
            is_mock=is_mock_result,
        )
        db.add(search_record)
        await db.commit()

        # Record usage in CreditGuard
        await CreditGuard.record_usage_async(
            amount=credits_consumed,
            is_mock=is_mock_result,
            db=db,
            notes=f"Candidate Search for '{query}' ({detected_type.value}) [Mode: {mode}]",
        )

        return EntitySearchResponse(
            query=query,
            detected_type=detected_type,
            candidates=deduped_candidates,
            is_ambiguous=is_ambiguous,
            credits_consumed=credits_consumed,
            is_mock=is_mock_result,
            data_origin="DEMO" if is_mock_result else "LIVE",
            interpretation=interpretation.model_dump(mode="json"),
            buying_intent_distinction=interpretation.buying_intent_distinction,
            next_cursor=next_cursor,
            total_results=total_results,
            page_size=limit,
            current_page=page,
        )

    async def enrich_entity(
        self,
        db: AsyncSession,
        identifier: str,
        entity_type: EntityType,
        level: EnrichmentLevel = EnrichmentLevel.LEVEL_2_STANDARD,
        force_refresh: bool = False,
        confirmation_confirmed: bool = False,
        mode: str = "LIVE",
    ) -> Union[CompanyIntelligenceProfile, PersonIntelligenceProfile, DeepEnrichmentCostEstimate]:
        """
        LEVEL 2 — STANDARD ENRICHMENT & LEVEL 3 — DEEP ENRICHMENT.
        - Checks local database cache first (7-day TTL).
        - If LEVEL 3 DEEP is requested without confirmation_confirmed=True, returns DeepEnrichmentCostEstimate.
        - Verifies application budget and account balance before paid enrichment.
        - Persists extracted profile and evidence provenance.
        """
        clean_id = identifier.strip().lower()

        # Safety Gate: LEVEL 3 DEEP ENRICHMENT requires explicit confirmation
        if level == EnrichmentLevel.LEVEL_3_DEEP and not confirmation_confirmed:
            return await self.estimate_deep_enrichment_cost(identifier, entity_type, db=db)

        # 1. Local Database Cache Check (Zero credits consumed on cache HIT)
        if not force_refresh and level != EnrichmentLevel.LEVEL_3_DEEP and mode != "DEMO":
            cached_entity = await self._find_cached_entity(db, clean_id, entity_type)
            if cached_entity and cached_entity.raw_profile:
                try:
                    raw = cached_entity.raw_profile
                    if entity_type == EntityType.COMPANY:
                        parsed_profile = CompanyIntelligenceProfile(**raw)
                    else:
                        parsed_profile = PersonIntelligenceProfile(**raw)
                    parsed_profile.data_origin = "CACHED"
                    parsed_profile.source = "Crustdata Local Cache"
                    logger.info(f"Crustdata cache HIT for {identifier} (Entity ID: {cached_entity.id})")
                    return parsed_profile
                except Exception as err:
                    logger.warning(f"Cached entity {cached_entity.id} profile invalid ({err}); refreshing.")

        # 2. Check Application Budget and Account Credit Safety Thresholds
        cost = CreditGuard.estimate_cost(level)
        is_client_mock = (mode == "DEMO") or (not self.client.is_configured and settings.CRUSTDATA_ENABLE_MOCK)
        await CreditGuard.verify_can_proceed_async(
            estimated_cost=cost,
            is_mock=is_client_mock,
            db=db,
        )

        # 3. Execute Enrichment via Client
        profile: Union[CompanyIntelligenceProfile, PersonIntelligenceProfile]
        if entity_type == EntityType.COMPANY:
            profile = await self.client.enrich_company(identifier, level=level, mode=mode)
        else:
            profile = await self.client.enrich_person(identifier, level=level, mode=mode)

        # 4. Persist in Database (Entity & Evidence) - only for non-demo or verified records
        await self._persist_entity_and_evidence(db, profile, entity_type, level)

        # 5. Record Usage in CreditGuard (separating mock from live)
        actual_consumed = profile.credits_consumed if profile.credits_consumed > 0 else cost
        await CreditGuard.record_usage_async(
            amount=actual_consumed,
            is_mock=profile.is_mock,
            db=db,
            notes=f"Enriched {identifier} ({entity_type.value}, {level.value}) [Mode: {mode}]",
        )

        return profile

    async def estimate_deep_enrichment_cost(
        self,
        identifier: str,
        entity_type: EntityType,
        db: Optional[AsyncSession] = None,
    ) -> DeepEnrichmentCostEstimate:
        """
        Returns estimated credit cost, account balance, and application budget before executing Level 3 Deep Enrichment.
        """
        credits_info = await self.client.get_account_credits()
        estimated_credits = CreditGuard.estimate_cost(EnrichmentLevel.LEVEL_3_DEEP)
        min_threshold = float(settings.CRUSTDATA_MIN_CREDIT_THRESHOLD)
        remaining_account = credits_info.remaining_credits

        # Application budget check
        budget_status = await CreditGuard.get_budget_status_async(db=db)
        budget_can_proceed = budget_status.remaining_credits >= estimated_credits
        account_can_proceed = (remaining_account - estimated_credits) >= min_threshold
        can_proceed = account_can_proceed and budget_can_proceed

        warning_msg = None
        if not budget_can_proceed:
            warning_msg = (
                f"Application Crustdata budget exhausted or insufficient for Level 3 Deep Enrichment: "
                f"Requires {estimated_credits:.1f} credits, but remaining budget is {budget_status.remaining_credits:.1f} credits "
                f"({budget_status.used_credits:.1f}/{budget_status.total_budget:.1f} used). "
                f"Please approve a budget increase to proceed."
            )
        elif not account_can_proceed:
            warning_msg = (
                f"Insufficient Crustdata account balance for Level 3 Deep Enrichment: Requires {estimated_credits:.1f} credits, "
                f"but account balance is {remaining_account:.1f} (min safety threshold {min_threshold:.1f})."
            )

        return DeepEnrichmentCostEstimate(
            entity_name=identifier,
            entity_type=entity_type,
            target_identifier=identifier,
            estimated_credits=estimated_credits,
            account_credits_available=remaining_account,
            safety_threshold=min_threshold,
            can_proceed=can_proceed,
            warning_message=warning_msg,
        )

    async def _find_cached_entity(
        self,
        db: AsyncSession,
        identifier: str,
        entity_type: EntityType,
    ) -> Optional[IntelligenceEntity]:
        """
        Finds fresh cached intelligence record within TTL using strict deterministic identifiers.
        Never uses loose substring searches that combine distinct identities.
        """
        ttl_cutoff = datetime.now(timezone.utc) - timedelta(days=settings.CRUSTDATA_CACHE_TTL_DAYS)
        clean_id = identifier.strip().lower()

        conditions = [
            IntelligenceEntity.entity_type == entity_type.value,
            IntelligenceEntity.last_enriched_at >= ttl_cutoff,
        ]

        if "linkedin.com/in/" in clean_id or "linkedin.com/company/" in clean_id:
            # Exact profile URL match
            conditions.append(func.lower(IntelligenceEntity.profile_url) == clean_id)
        elif "." in clean_id and " " not in clean_id:
            # Exact domain match
            conditions.append(func.lower(IntelligenceEntity.primary_domain) == clean_id)
        else:
            # Exact primary name match
            conditions.append(func.lower(IntelligenceEntity.primary_name) == clean_id)

        stmt = select(IntelligenceEntity).where(and_(*conditions)).order_by(desc(IntelligenceEntity.last_enriched_at))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def _persist_entity_and_evidence(
        self,
        db: AsyncSession,
        profile: Union[CompanyIntelligenceProfile, PersonIntelligenceProfile],
        entity_type: EntityType,
        level: EnrichmentLevel,
    ) -> IntelligenceEntity:
        """Saves or updates IntelligenceEntity and granular evidence provenance."""
        primary_name = profile.name if isinstance(profile, CompanyIntelligenceProfile) else profile.full_name
        primary_domain = profile.primary_domain if isinstance(profile, CompanyIntelligenceProfile) else None
        profile_url = profile.linkedin_url

        # Check existing entity record using deterministic keys
        conditions = [IntelligenceEntity.id == profile.entity_id]
        if profile_url:
            conditions.append(IntelligenceEntity.profile_url == profile_url)
        if primary_domain:
            conditions.append(IntelligenceEntity.primary_domain == primary_domain)

        existing_stmt = select(IntelligenceEntity).where(or_(*conditions))
        res = await db.execute(existing_stmt)
        entity = res.scalars().first()

        if not entity:
            entity = IntelligenceEntity(
                id=profile.entity_id,
                entity_type=entity_type.value,
                primary_name=primary_name,
                primary_domain=primary_domain,
                profile_url=profile_url,
                raw_profile=profile.model_dump(mode="json"),
                data_freshness=profile.data_freshness,
                enrichment_level=level.value,
                credits_consumed=profile.credits_consumed,
                is_mock=profile.is_mock,
                last_enriched_at=datetime.now(timezone.utc),
            )
            db.add(entity)
        else:
            profile.entity_id = entity.id
            entity.raw_profile = profile.model_dump(mode="json")
            entity.data_freshness = profile.data_freshness
            entity.enrichment_level = level.value
            entity.credits_consumed += profile.credits_consumed
            entity.last_enriched_at = datetime.now(timezone.utc)

        await db.flush()

        # Persist granular evidence provenance
        for ev in profile.evidence:
            evidence_row = IntelligenceEvidence(
                id=str(uuid.uuid4()),
                entity_id=entity.id,
                data_category=ev.data_category,
                claim=ev.claim,
                source_url=ev.source_url,
                retrieval_timestamp=ev.retrieval_timestamp,
                confidence=ev.confidence,
                verification_classification=ev.verification_classification.value,
                original_source_metadata=ev.metadata,
            )
            db.add(evidence_row)

        await db.commit()
        return entity
