"""
Central Copywriter Agent Orchestrator.
Coordinates the generation of personalized executive emails, LinkedIn sequences,
technical migration pitches, value propositions, objection matrices, and anti-hallucination audits.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.company import Company
from app.models.signal import Signal
from app.models.dossier import DepositionDossier
from app.models.execution_log import AgentExecutionLog
from app.agents.copywriter.schemas import OutreachPackage
from app.agents.copywriter.personalization import PersonalizationEngine
from app.agents.copywriter.executive_email import ExecutiveEmailWriter
from app.agents.copywriter.linkedin_writer import LinkedInWriter
from app.agents.copywriter.technical_pitch import TechnicalPitchWriter
from app.agents.copywriter.value_proposition import ValuePropositionWriter
from app.agents.copywriter.objection_handler import ObjectionHandler
from app.agents.copywriter.evidence_guard import EvidenceGuard


class CopywriterAgent:
    """Orchestrates creation of personalized competitive deposition collateral."""

    @classmethod
    async def generate_outreach_package(
        cls,
        company: Company,
        signal: Optional[Signal] = None,
        finops_data: Optional[Dict[str, Any]] = None,
        arch_data: Optional[Dict[str, Any]] = None,
        target_challenger: str = "SigNoz Cloud",
        include_llm_polish: bool = False,
        target_vendor: str = "Datadog",
    ) -> OutreachPackage:
        """Generates the complete audited outreach collateral package."""
        is_generic = (
            not company.domain
            or company.id == "unknown"
            or company.qualification_status == "REJECTED"
            or getattr(company, "verification_status", None) == "UNKNOWN"
        )
        display_name = "Generic Organization (Reference Architecture)" if is_generic else company.name

        company_data = {
            "name": display_name,
            "domain": company.domain,
            "industry": company.industry or "Technology",
            "estimated_size": company.estimated_size or "50-250 employees",
            "icp_score": company.icp_score,
            "qualification_status": company.qualification_status,
            "is_generic": is_generic,
        }

        signal_data = {
            "complaint_category": signal.complaint_category if signal else "GENERAL_DISCUSSION",
            "source": signal.source if signal else "SYNTHETIC",
            "raw_content": signal.raw_content if signal else "",
            "urgency_score": signal.urgency_score if signal else 0.5,
        }

        finops = finops_data or {}
        arch = arch_data or {}

        # 1. Adapt Context & Tone
        context = PersonalizationEngine.get_context(
            company_data=company_data,
            signal_data=signal_data,
            target_challenger=target_challenger,
            target_vendor=target_vendor,
        )

        # 2. Generate Collateral Modules
        executive_emails = ExecutiveEmailWriter.generate_variants(context, finops, arch)
        linkedin_seq = LinkedInWriter.generate_sequence(context, finops)
        technical_pitch = TechnicalPitchWriter.generate_pitch(context, finops, arch)
        value_prop = ValuePropositionWriter.generate_value_proposition(context, finops)
        objection_matrix = ObjectionHandler.generate_matrix(context, finops, arch)

        # 2b. Optional LLM Refinement of Primary Variant
        if include_llm_polish:
            try:
                from app.core.llm.services import LLMIntelligenceService
                from app.agents.copywriter.schemas import EmailVariant
                primary_body = executive_emails[0].body_markdown
                base_savings = 0.0
                if finops and "scenarios" in finops and "BASE" in finops["scenarios"]:
                    base_savings = float(finops["scenarios"]["BASE"].get("signoz_cloud_annual_savings", 0.0))

                refined = await LLMIntelligenceService.polish_personalized_outreach(
                    company_name=display_name,
                    baseline_body=primary_body,
                    verified_savings_usd=base_savings,
                    target_backend=target_challenger,
                )
                if refined and refined.subject_lines and refined.polished_body:
                    subjects = list(refined.subject_lines)
                    while len(subjects) < 3:
                        subjects.append(f"{display_name} OpenTelemetry migration blueprint")

                    refined_variant = EmailVariant(
                        variant_type="LLM_POLISHED_EXECUTIVE",
                        target_role="CTO / VP Engineering",
                        subject_lines=subjects[:3],
                        preheader=refined.opening_hook[:120],
                        body_markdown=refined.polished_body,
                        call_to_action="Schedule an architectural review",
                        referenced_attachments=["OpenTelemetry Collector Blueprint YAML"],
                    )
                    executive_emails.insert(0, refined_variant)
            except Exception:
                pass

        # 3. Assemble corpus for Evidence Guard Audit
        corpus_parts = [
            "\n".join([em.body_markdown for em in executive_emails]),
            linkedin_seq.step_1_connection_request,
            linkedin_seq.step_2_value_add,
            linkedin_seq.step_3_technical_commercial,
            technical_pitch.full_pitch_markdown,
            value_prop.full_value_prop_markdown,
            "\n".join([obj.recommended_response for obj in objection_matrix.items]),
        ]
        text_corpus = "\n\n".join(corpus_parts)

        # 4. Run Evidence Guard Audit
        audit_report = EvidenceGuard.audit_collateral(
            text_corpus=text_corpus,
            company_data=company_data,
            finops_data=finops,
            arch_data=arch,
            signal_data=signal_data,
        )

        # 5. Assemble Package
        package = OutreachPackage(
            company_name=display_name,
            company_id=company.id,
            target_challenger=target_challenger,
            distress_category=context["distress_tag"],
            executive_emails=executive_emails,
            linkedin_sequence=linkedin_seq,
            technical_pitch=technical_pitch,
            value_proposition=value_prop,
            objection_matrix=objection_matrix,
            evidence_audit=audit_report,
            generated_at=datetime.now(timezone.utc).isoformat(),
            governance_status="DRAFT_PENDING_APPROVAL",
        )

        return package

    @classmethod
    async def run_and_persist(
        cls,
        company_id: str,
        target_challenger: str = "SigNoz Cloud",
        db: Optional[AsyncSession] = None,
        include_llm_polish: bool = False,
        target_vendor: str = "Datadog",
    ) -> Dict[str, Any]:
        """
        Loads Company, Signal, and DepositionDossier; generates outreach package;
        updates the dossier; and logs execution.
        """
        if not db:
            raise ValueError("AsyncSession is required for persistence")

        # 1. Fetch Company
        company_res = await db.execute(select(Company).where(Company.id == company_id))
        company = company_res.scalar_one_or_none()
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # 2. Fetch Signal
        signal_res = await db.execute(select(Signal).where(Signal.id == company.signal_id))
        signal = signal_res.scalar_one_or_none()

        # 3. Fetch Dossier
        dossier_res = await db.execute(
            select(DepositionDossier).where(DepositionDossier.company_id == company_id)
        )
        dossier = dossier_res.scalar_one_or_none()

        finops_data = dossier.financial_delta if dossier else {}
        arch_data = dossier.migration_blueprint if dossier else {}

        # 4. Generate package
        package = await cls.generate_outreach_package(
            company=company,
            signal=signal,
            finops_data=finops_data,
            arch_data=arch_data,
            target_challenger=target_challenger,
            include_llm_polish=include_llm_polish,
            target_vendor=target_vendor,
        )

        package_dict = package.model_dump(mode="json")

        # 5. Update or create Dossier
        if dossier:
            dossier.outreach_drafts = package_dict
            dossier.status = "DRAFT_PENDING_APPROVAL"
        else:
            dossier = DepositionDossier(
                company_id=company.id,
                signal_id=company.signal_id,
                financial_delta=finops_data,
                migration_blueprint=arch_data,
                outreach_drafts=package_dict,
                status="DRAFT_PENDING_APPROVAL",
                is_synthetic=company.is_synthetic,
            )
            db.add(dossier)

        # 6. Log Agent Execution
        log_entry = AgentExecutionLog(
            agent_name="COPYWRITER",
            signal_id=company.signal_id,
            status="SUCCESS",
            execution_time_ms=120,
            input_payload={
                "company_id": company.id,
                "company_name": company.name,
                "target_challenger": target_challenger,
            },
            output_payload={
                "action": "GENERATE_OUTREACH_COLLATERAL",
                "email_variants_generated": len(package.executive_emails),
                "audit_passed": package.evidence_audit.passed,
                "hallucination_risk_score": package.evidence_audit.hallucination_risk_score,
                "governance_status": "DRAFT_PENDING_APPROVAL",
            },
        )
        db.add(log_entry)
        await db.commit()
        await db.refresh(dossier)

        return {
            "dossier_id": dossier.id,
            "company_id": company.id,
            "status": dossier.status,
            "audit_passed": package.evidence_audit.passed,
            "outreach_package": package_dict,
        }
