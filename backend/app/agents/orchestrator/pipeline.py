"""
Pipeline Runner for Central Orchestrator.
Executes the sequential multi-agent pipeline with qualification gates, partial resumption,
error handling, and human approval preservation across the seven stages:
LISTENER -> PROFILER -> QUALIFICATION -> FINOPS -> ARCHITECT -> COPYWRITER -> APPROVAL_GATE
"""

import time
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.logging import logger
from app.models.signal import Signal
from app.models.company import Company
from app.models.dossier import DepositionDossier
from app.models.workflow import WorkflowExecution
from app.models.execution_log import AgentExecutionLog
from app.agents.orchestrator.state_machine import WorkflowState, WorkflowStep, StateMachineValidator
from app.agents.listener.agent import ListenerAgent
from app.agents.profiler.entity_resolver import EntityResolver
from app.agents.profiler.domain_verifier import DomainVerifier
from app.agents.profiler.technology_profiler import TechnologyProfiler
from app.agents.profiler.icp_scorer import IcpScorer
from app.agents.finops_architect.finops_agent import FinOpsAgent
from app.agents.finops_architect.architecture_agent import ArchitectureAgent
from app.agents.copywriter.agent import CopywriterAgent
from app.services.objective.objective_interpreter import ObjectiveInterpreter


class PipelineRunner:
    """Executes the end-to-end multi-agent orchestration pipeline."""

    @classmethod
    async def execute_workflow(
        cls,
        workflow: WorkflowExecution,
        db: AsyncSession,
        timeout_seconds: int = 60,
    ) -> WorkflowExecution:
        """Runs or resumes a workflow with timeout enforcement and state transitions."""
        start_time = time.time()
        logger.info(f"Executing workflow {workflow.id} (current_step={workflow.current_step}, status={workflow.status})")

        try:
            # Wrap execution with overall workflow timeout
            await asyncio.wait_for(
                cls._run_pipeline_steps(workflow, db),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            err_msg = f"Workflow timed out after {timeout_seconds} seconds."
            logger.error(f"Workflow {workflow.id} timeout: {err_msg}")
            try:
                await db.rollback()
            except Exception:
                pass
            cls._record_failure(workflow, "TIMEOUT", err_msg)
            await db.commit()
        except Exception as e:
            err_msg = f"Workflow step error: {str(e)}"
            logger.error(f"Workflow {workflow.id} failed: {err_msg}", exc_info=True)
            try:
                await db.rollback()
            except Exception:
                pass
            cls._record_failure(workflow, workflow.current_step, err_msg)
            await db.commit()

        duration_ms = int((time.time() - start_time) * 1000)
        workflow.execution_duration_ms += duration_ms

        # Finalize and persist agent execution log
        log_entry = AgentExecutionLog(
            agent_name="ORCHESTRATOR",
            signal_id=workflow.signal_id,
            status="SUCCESS" if workflow.status in (WorkflowState.DRAFT_PENDING_APPROVAL, WorkflowState.COMPLETED) else "FAILED",
            execution_time_ms=duration_ms,
            input_payload={
                "workflow_id": workflow.id,
                "workflow_type": workflow.workflow_type,
                "target_challenger": workflow.target_challenger,
                "objective": workflow.input_payload.get("objective"),
            },
            output_payload={
                "final_status": workflow.status,
                "current_step": workflow.current_step,
                "company_id": workflow.company_id,
                "dossier_id": workflow.dossier_id,
                "step_count": len(workflow.step_history),
            },
            error_message=workflow.error_details,
        )
        db.add(log_entry)
        await db.commit()
        await db.refresh(workflow)
        return workflow

    @classmethod
    async def _run_pipeline_steps(cls, workflow: WorkflowExecution, db: AsyncSession) -> None:
        """Sequentially executes remaining pipeline steps with partial resumption."""
        completed_steps = {s.get("step_name") for s in workflow.step_history if s.get("status") == "SUCCESS"}

        # -------------------------------------------------------------
        # STEP 1: Listener (Signal Ingestion)
        # -------------------------------------------------------------
        signal: Optional[Signal] = None
        if workflow.signal_id:
            sig_res = await db.execute(select(Signal).where(Signal.id == workflow.signal_id))
            signal = sig_res.scalar_one_or_none()

        if WorkflowStep.LISTENER.value not in completed_steps:
            step_start = time.time()
            if not signal and not workflow.company_id:
                workflow.status = WorkflowState.LISTENER_RUNNING.value
                workflow.current_step = WorkflowStep.LISTENER.value
                await db.commit()

                # Process natural language objective if present
                objective = workflow.input_payload.get("objective")
                parsed_criteria: Optional[Dict[str, Any]] = workflow.input_payload.get("parsed_criteria")
                search_queries: Optional[List[str]] = None
                if objective and not parsed_criteria:
                    criteria = ObjectiveInterpreter.interpret(objective)
                    parsed_criteria = criteria.model_dump()
                    search_queries = criteria.search_queries
                    workflow.input_payload["parsed_criteria"] = parsed_criteria
                    out_p = dict(workflow.output_payload or {})
                    out_p["objective"] = objective
                    out_p["parsed_criteria"] = parsed_criteria
                    workflow.output_payload = out_p
                    await db.commit()
                elif parsed_criteria:
                    search_queries = parsed_criteria.get("search_queries")

                listener = ListenerAgent()
                include_synth = workflow.input_payload.get("include_synthetic", False)
                summary = await listener.run_ingestion_cycle(
                    db,
                    include_synthetic=include_synth,
                    max_items_per_source=5,
                    queries=search_queries,
                    objective_criteria=parsed_criteria,
                )

                # Persist source execution telemetry
                out_p = dict(workflow.output_payload or {})
                out_p["source_execution_results"] = [s.model_dump(mode="json") for s in summary.sources]
                out_p["listener_summary"] = summary.model_dump(mode="json")
                workflow.output_payload = out_p
                await db.commit()

                # Pick an actionable newly ingested signal
                target_sig_id = workflow.input_payload.get("signal_id")
                if target_sig_id:
                    sig_res = await db.execute(select(Signal).where(Signal.id == target_sig_id))
                    signal = sig_res.scalar_one_or_none()

                if not signal:
                    # Look for signals: prioritize those matching objective and identifiable corporate entities
                    all_new_sig_query = select(Signal).where(Signal.status == "NEW").order_by(desc(Signal.urgency_score))
                    all_new_sig_res = await db.execute(all_new_sig_query)
                    all_new_signals = all_new_sig_res.scalars().all()
                    for cand_sig in all_new_signals:
                        ee = cand_sig.extracted_evidence or {}
                        if ee.get("company_name") or ee.get("domain"):
                            signal = cand_sig
                            break
                        cand, _ = EntityResolver.resolve(
                            title=getattr(cand_sig, 'title', "") or "",
                            content=cand_sig.raw_content,
                            author=cand_sig.author_handle,
                            source_url=cand_sig.original_url,
                            extracted_evidence=cand_sig.extracted_evidence,
                        )
                        if cand:
                            signal = cand_sig
                            break
                    if not signal and all_new_signals:
                        signal = all_new_signals[0]

                if signal:
                    workflow.signal_id = signal.id
                    workflow.is_synthetic = signal.is_synthetic

                cls._record_step(
                    workflow=workflow,
                    step_name=WorkflowStep.LISTENER.value,
                    status="SUCCESS",
                    duration_ms=int((time.time() - step_start) * 1000),
                    details={
                        "signals_fetched": summary.total_fetched,
                        "new_signals_saved": summary.new_signals_saved,
                        "selected_signal_id": signal.id if signal else None,
                        "sources_scanned": [s.source_name for s in summary.sources if s.monitoring_status == "COMPLETED"],
                    },
                )
                await db.commit()
            elif signal:
                # Signal was explicitly targeted for this workflow run
                cls._record_step(
                    workflow=workflow,
                    step_name=WorkflowStep.LISTENER.value,
                    status="SUCCESS",
                    duration_ms=0,
                    details={"source": signal.source, "selected_signal_id": signal.id, "urgency": signal.urgency_score},
                )
                await db.commit()

        # -------------------------------------------------------------
        # STEP 2: Profiler (Entity Resolution & Tech Profiling)
        # -------------------------------------------------------------
        company: Optional[Company] = None
        if workflow.company_id:
            comp_res = await db.execute(select(Company).where(Company.id == workflow.company_id))
            company = comp_res.scalar_one_or_none()
            if company and not signal and company.signal_id:
                sig_res = await db.execute(select(Signal).where(Signal.id == company.signal_id))
                signal = sig_res.scalar_one_or_none()

        if not company and WorkflowStep.PROFILER.value not in completed_steps:
            if not signal:
                # If no signal exists to profile, mark as failed
                raise ValueError("No active signal found to profile in workflow.")

            step_start = time.time()
            workflow.status = WorkflowState.PROFILER_RUNNING.value
            workflow.current_step = WorkflowStep.PROFILER.value
            await db.commit()

            # Execute dedicated profiling for the active signal
            candidate, entity_evidence = EntityResolver.resolve(
                title=getattr(signal, 'title', "") or "",
                content=signal.raw_content,
                author=signal.author_handle,
                source_url=signal.original_url,
                extracted_evidence=signal.extracted_evidence,
            )

            if not candidate:
                signal.status = "UNRESOLVED"
                cls._record_step(
                    workflow=workflow,
                    step_name=WorkflowStep.PROFILER.value,
                    status="UNRESOLVED",
                    duration_ms=int((time.time() - step_start) * 1000),
                    details={"reason": "Signal source is anonymous or hobbyist; cannot resolve business entity without hallucination."},
                )
                workflow.status = WorkflowState.REJECTED.value
                workflow.current_step = WorkflowStep.PROFILER.value
                workflow.error_details = "Signal could not be resolved to a corporate entity without hallucination."
                await db.commit()
                return

            evidence_records = [e.model_dump(mode="json") for e in entity_evidence]
            dns_records = []
            if candidate.domain:
                dns_res, dns_evidence = await DomainVerifier.verify(candidate.domain)
                evidence_records.extend([e.model_dump(mode="json") for e in dns_evidence])
                dns_records = [r.model_dump(mode="json") for r in dns_res.records]

            tech_profile = await TechnologyProfiler.profile_company(
                company_name=candidate.company_name,
                domain=candidate.domain,
                raw_signal_text=signal.raw_content,
                signal_evidence=signal.extracted_evidence,
            )
            for te in tech_profile.evidence:
                evidence_records.append(te.model_dump(mode="json"))

            infra_indicators = {
                "inferred_nodes": signal.extracted_evidence.get("inferred_nodes", 100),
                "dns_active": bool(dns_records),
            }
            score_report = IcpScorer.evaluate(
                company_name=candidate.company_name,
                estimated_size=candidate.estimated_size,
                tech_profile=tech_profile,
                identity_confidence=candidate.identity_confidence,
                signal_urgency=signal.urgency_score,
                complaint_category=signal.complaint_category,
                infra_indicators=infra_indicators,
            )

            # Resolve Decision Makers via Crustdata Intelligence (with mock fallback for demo/synthetic)
            resolved_decision_makers = list(candidate.decision_makers) if candidate.decision_makers else []
            if candidate.domain:
                try:
                    from app.services.crustdata.mock_provider import CrustdataMockProvider
                    c_prof = CrustdataMockProvider.enrich_company(candidate.domain)
                    if c_prof and c_prof.leadership:
                        resolved_decision_makers = [
                            {
                                "name": l.get("name"),
                                "title": l.get("title"),
                                "role": l.get("title"),
                                "department": "Engineering",
                            }
                            for l in c_prof.leadership
                        ]
                except Exception:
                    pass

            company = Company(
                signal_id=signal.id,
                name=candidate.company_name,
                domain=candidate.domain,
                company_description=candidate.description,
                estimated_size=candidate.estimated_size,
                industry=candidate.industry,
                tech_stack=tech_profile.detected_technologies,
                infrastructure_indicators=infra_indicators,
                icp_score=score_report.icp_fit_score,
                identity_confidence=score_report.identity_confidence,
                technology_confidence=score_report.technology_confidence,
                qualification_status=score_report.qualification_status,
                decision_makers=resolved_decision_makers,
                evidence_sources=[signal.original_url] if signal.original_url else [],
                evidence_records=evidence_records,
                is_synthetic=signal.is_synthetic,
                last_enriched_at=datetime.now(timezone.utc),
            )
            db.add(company)
            await db.flush()
            workflow.company_id = company.id

            cls._record_step(
                workflow=workflow,
                step_name=WorkflowStep.PROFILER.value,
                status="SUCCESS",
                duration_ms=int((time.time() - step_start) * 1000),
                details={"company_name": company.name, "qualification_status": company.qualification_status, "icp_score": company.icp_score},
            )
            await db.commit()

        # -------------------------------------------------------------
        # STEP 3: Company Qualification Gate
        # -------------------------------------------------------------
        if not company:
            raise ValueError("Company instance is required for qualification check.")

        step_start = time.time()
        workflow.status = WorkflowState.QUALIFICATION_REVIEW.value
        workflow.current_step = WorkflowStep.QUALIFICATION.value

        # Qualification check: Drop unqualified companies from expensive downstream processing
        if company.qualification_status == "REJECTED":
            cls._record_step(
                workflow=workflow,
                step_name=WorkflowStep.QUALIFICATION.value,
                status="DISQUALIFIED",
                duration_ms=int((time.time() - step_start) * 1000),
                details={"company_name": company.name, "reason": "ICP Score or Identity Confidence below enterprise qualification threshold."},
            )
            workflow.status = WorkflowState.REJECTED.value
            workflow.current_step = WorkflowStep.QUALIFICATION.value
            workflow.error_details = f"Company '{company.name}' was disqualified during ICP qualification. Downstream FinOps and collateral generation skipped."
            await db.commit()
            logger.info(f"Workflow {workflow.id}: Company {company.name} disqualified. Downstream pipeline halted.")
            return

        cls._record_step(
            workflow=workflow,
            step_name=WorkflowStep.QUALIFICATION.value,
            status="SUCCESS",
            duration_ms=int((time.time() - step_start) * 1000),
            details={"qualification_status": company.qualification_status, "icp_score": company.icp_score},
        )
        await db.commit()

        # -------------------------------------------------------------
        # STEP 4: FinOps Intelligence Analysis
        # -------------------------------------------------------------
        fin_report = None
        if WorkflowStep.FINOPS.value not in completed_steps:
            step_start = time.time()
            workflow.status = WorkflowState.FINOPS_RUNNING.value
            workflow.current_step = WorkflowStep.FINOPS.value
            await db.commit()

            fin_report = await FinOpsAgent.generate_financial_analysis(company, signal)
            base_scenario = fin_report.scenarios.get("BASE")

            cls._record_step(
                workflow=workflow,
                step_name=WorkflowStep.FINOPS.value,
                status="SUCCESS",
                duration_ms=int((time.time() - step_start) * 1000),
                details={
                    "target_challenger": workflow.target_challenger,
                    "annual_datadog_spend": base_scenario.current_datadog_annual if base_scenario else 0.0,
                    "estimated_annual_savings": base_scenario.signoz_cloud_annual_savings if base_scenario else 0.0,
                    "payback_months": base_scenario.payback_period_months if base_scenario else 0.0,
                },
            )
            await db.commit()

        # -------------------------------------------------------------
        # STEP 5: Architecture Migration Blueprint
        # -------------------------------------------------------------
        arch_blueprint = None
        if WorkflowStep.ARCHITECT.value not in completed_steps:
            step_start = time.time()
            workflow.status = WorkflowState.ARCHITECT_RUNNING.value
            workflow.current_step = WorkflowStep.ARCHITECT.value
            await db.commit()

            arch_blueprint = await ArchitectureAgent.generate_migration_blueprint(
                company, target_backend=workflow.target_challenger
            )

            # Persist or update DepositionDossier
            dossier_res = await db.execute(select(DepositionDossier).where(DepositionDossier.company_id == company.id))
            dossier = dossier_res.scalar_one_or_none()

            # Ensure we have fin_report
            if not fin_report:
                fin_report = await FinOpsAgent.generate_financial_analysis(company, signal)
            base_scenario = fin_report.scenarios.get("BASE")

            delta_dict = {
                "datadog_monthly": base_scenario.current_datadog_monthly if base_scenario else 0.0,
                "datadog_annual": base_scenario.current_datadog_annual if base_scenario else 0.0,
                "signoz_monthly": base_scenario.signoz_cloud_monthly if base_scenario else 0.0,
                "signoz_annual": base_scenario.signoz_cloud_annual if base_scenario else 0.0,
                "estimated_annual_savings": base_scenario.signoz_cloud_annual_savings if base_scenario else 0.0,
                "payback_period_months": base_scenario.payback_period_months if base_scenario else 0.0,
                "report": fin_report.model_dump(mode="json"),
            }
            blueprint_dict = arch_blueprint.model_dump(mode="json")

            if dossier:
                dossier.financial_delta = delta_dict
                dossier.migration_blueprint = blueprint_dict
            else:
                dossier = DepositionDossier(
                    company_id=company.id,
                    signal_id=company.signal_id,
                    financial_delta=delta_dict,
                    migration_blueprint=blueprint_dict,
                    status="DRAFT_PENDING_APPROVAL",
                    is_synthetic=company.is_synthetic,
                )
                db.add(dossier)
            await db.flush()
            workflow.dossier_id = dossier.id

            cls._record_step(
                workflow=workflow,
                step_name=WorkflowStep.ARCHITECT.value,
                status="SUCCESS",
                duration_ms=int((time.time() - step_start) * 1000),
                details={"phases_planned": len(arch_blueprint.phases), "dossier_id": dossier.id},
            )
            await db.commit()

        # -------------------------------------------------------------
        # STEP 6: Copywriter Agent (Collateral Generation & Evidence Guard)
        # -------------------------------------------------------------
        if WorkflowStep.COPYWRITER.value not in completed_steps:
            step_start = time.time()
            workflow.status = WorkflowState.COPYWRITER_RUNNING.value
            workflow.current_step = WorkflowStep.COPYWRITER.value
            await db.commit()

            copywriter_res = await CopywriterAgent.run_and_persist(
                company_id=company.id,
                target_challenger=workflow.target_challenger,
                db=db,
            )

            cls._record_step(
                workflow=workflow,
                step_name=WorkflowStep.COPYWRITER.value,
                status="SUCCESS",
                duration_ms=int((time.time() - step_start) * 1000),
                details={
                    "dossier_id": copywriter_res["dossier_id"],
                    "governance_status": "DRAFT_PENDING_APPROVAL",
                    "audit_passed": copywriter_res["outreach_package"]["evidence_audit"]["passed"],
                },
            )
            await db.commit()

        # -------------------------------------------------------------
        # STEP 7: Human Approval Gate (Never automatically bypassed)
        # -------------------------------------------------------------
        # Strictly verify that all required stages completed and communication drafts were persisted
        dossier_res = await db.execute(select(DepositionDossier).where(DepositionDossier.id == workflow.dossier_id))
        dossier = dossier_res.scalar_one_or_none()
        if not dossier or not dossier.outreach_drafts:
            raise ValueError("Workflow cannot reach DRAFT_PENDING_APPROVAL: communication drafts were not persisted.")

        drafts_payload = dossier.outreach_drafts
        if not drafts_payload.get("executive_emails") or not drafts_payload.get("linkedin_sequence"):
            raise ValueError("Workflow cannot reach DRAFT_PENDING_APPROVAL: executive emails or LinkedIn drafts missing.")

        workflow.status = WorkflowState.DRAFT_PENDING_APPROVAL.value
        workflow.current_step = WorkflowStep.APPROVAL_GATE.value
        workflow.completed_at = datetime.now(timezone.utc)
        
        # Populate comprehensive output payload summary preserving all stages
        out_p = dict(workflow.output_payload or {})
        out_p.update({
            "company_id": company.id,
            "company_name": company.name,
            "domain": company.domain,
            "signal_id": signal.id if signal else None,
            "dossier_id": workflow.dossier_id,
            "qualification_status": company.qualification_status,
            "icp_score": company.icp_score,
            "financial_estimates": dossier.financial_delta,
            "migration_blueprint_summary": {
                "phases_count": len(dossier.migration_blueprint.get("phases", [])),
                "collector_yaml_ready": bool(dossier.migration_blueprint.get("collector_yaml")),
            },
            "outreach_drafts": {
                "emails_count": len(drafts_payload.get("executive_emails", [])),
                "linkedin_steps_count": len(drafts_payload.get("linkedin_sequence", {}).get("steps", [])),
            },
            "governance_status": "DRAFT_PENDING_APPROVAL",
            "message": "Pipeline completed successfully. Outreach collateral is awaiting human review.",
        })
        workflow.output_payload = out_p

        # Formally record Step 7 in step_history
        cls._record_step(
            workflow=workflow,
            step_name=WorkflowStep.APPROVAL_GATE.value,
            status="PENDING_APPROVAL",
            duration_ms=0,
            details={
                "governance_status": "DRAFT_PENDING_APPROVAL",
                "dossier_id": workflow.dossier_id,
                "company_name": company.name,
                "executive_emails_count": len(drafts_payload.get("executive_emails", [])),
                "has_linkedin_sequence": bool(drafts_payload.get("linkedin_sequence")),
                "message": "All pipeline stages successfully completed. Collateral pending human review before export.",
            },
        )
        await db.commit()
        logger.info(f"Workflow {workflow.id} completed: Deposition dossier ready in DRAFT_PENDING_APPROVAL.")

    @classmethod
    def _record_step(
        cls,
        workflow: WorkflowExecution,
        step_name: str,
        status: str,
        duration_ms: int,
        details: Dict[str, Any],
        error_message: Optional[str] = None,
    ) -> None:
        """Appends a structured step record to workflow.step_history."""
        step_rec = {
            "step_name": step_name,
            "status": status,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "details": details,
            "error_message": error_message,
        }
        # Create a new list copy to ensure SQLAlchemy detects JSON mutation
        history = list(workflow.step_history or [])
        history.append(step_rec)
        workflow.step_history = history

    @classmethod
    def _record_failure(
        cls,
        workflow: WorkflowExecution,
        step_name: str,
        error_message: str,
    ) -> None:
        """Updates workflow state to FAILED and logs step failure details."""
        workflow.status = WorkflowState.FAILED.value
        workflow.current_step = step_name
        workflow.error_details = error_message
        workflow.retry_count += 1
        cls._record_step(
            workflow=workflow,
            step_name=step_name,
            status="FAILED",
            duration_ms=0,
            details={"retry_count": workflow.retry_count},
            error_message=error_message,
        )
