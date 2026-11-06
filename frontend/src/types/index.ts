export type SignalSource = "REDDIT" | "HACKER_NEWS" | "TWITTER" | "DATADOG_STATUS" | "SYNTHETIC";
export type ComplaintCategory = "PRICING_SHOCK" | "OUTAGE" | "DEPRECATION" | "RELIABILITY" | "GENERAL_DISCUSSION";
export type SentimentType = "POSITIVE" | "NEUTRAL" | "NEGATIVE" | "EXTREMELY_NEGATIVE";
export type SignalStatus = "NEW" | "PROFILED" | "QUALIFIED" | "REJECTED" | "ARCHIVED";

export interface Signal {
  id: string;
  signal_id: string;
  source: SignalSource;
  original_url: string;
  author_handle?: string | null;
  vendor: string;
  complaint_category: ComplaintCategory;
  raw_content: string;
  sentiment: SentimentType;
  urgency_score: number;
  extracted_evidence: Record<string, any>;
  is_synthetic: boolean;
  status: SignalStatus;
  created_at: string;
  updated_at: string;
}

export type QualificationStatus = "ACCEPTED" | "REVIEW_REQUIRED" | "REJECTED";
export type EvidenceClassification = "VERIFIED" | "INFERRED" | "UNKNOWN";

export interface EvidenceRecord {
  claim: string;
  classification: EvidenceClassification;
  source: string;
  confidence: number;
  description: string;
  url?: string | null;
  verified_at?: string;
}

export interface DecisionMakerObject {
  role?: string | null;
  department?: string | null;
  name?: string | null;
  title?: string | null;
  email?: string | null;
  linkedin_url?: string | null;
  [key: string]: string | number | boolean | null | undefined;
}

export type DecisionMaker = string | DecisionMakerObject;

export interface Company {
  id: string;
  signal_id: string;
  name: string;
  domain?: string | null;
  company_description?: string | null;
  estimated_size: string;
  industry?: string | null;
  tech_stack: Record<string, any>;
  infrastructure_indicators: Record<string, any>;
  icp_score: number;
  identity_confidence: number;
  technology_confidence: number;
  qualification_status: QualificationStatus;
  decision_makers: DecisionMaker[];
  evidence_sources: string[];
  evidence_records: EvidenceRecord[];
  is_synthetic: boolean;
  last_enriched_at?: string | null;
  created_at: string;
  updated_at: string;
}

export type DossierStatus = "DRAFT_PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "SENT" | "EXPORTED";

export interface DepositionDossier {
  id: string;
  company_id: string;
  signal_id: string;
  financial_delta: Record<string, any>;
  migration_blueprint: Record<string, any>;
  outreach_drafts: Record<string, any>;
  status: DossierStatus;
  is_synthetic: boolean;
  created_at: string;
  updated_at: string;
}

export interface PricingEntry {
  vendor: string;
  product: string;
  billing_unit: string;
  unit_price: number;
  currency: string;
  billing_period: string;
  pricing_source_url: string;
  last_verified_date: string;
  pricing_classification: string;
}

export interface FinancialScenario {
  scenario_name: string;
  assumptions_description: string;
  current_datadog_monthly: number;
  current_datadog_annual: number;
  signoz_cloud_monthly: number;
  signoz_cloud_annual: number;
  signoz_cloud_annual_savings: number;
  signoz_cloud_savings_pct: number;
  signoz_self_hosted_monthly: number;
  signoz_self_hosted_annual: number;
  signoz_self_hosted_annual_savings: number;
  grafana_cloud_monthly: number;
  grafana_cloud_annual: number;
  grafana_cloud_annual_savings: number;
  grafana_oss_monthly: number;
  grafana_oss_annual: number;
  grafana_oss_annual_savings: number;
  estimated_migration_cost: number;
  payback_period_months: number;
  three_year_tco_datadog: number;
  three_year_tco_signoz_cloud: number;
  three_year_tco_grafana_cloud: number;
}

export interface FinancialDeltaReport {
  company_id: string;
  company_name: string;
  target_challenger: string;
  scenarios: Record<string, FinancialScenario>;
  sensitivity_analysis: Array<{
    variable_name: string;
    baseline_value: number;
    tested_range: string;
    monthly_impact_usd: number;
    sensitivity_rank: number;
  }>;
}

export interface MigrationPhase {
  phase_number: number;
  name: string;
  duration_days: number;
  tasks: string[];
  dependencies: string[];
  success_criteria: string[];
  potential_risks: string[];
  rollback_triggers: string[];
}

export interface ArchitectureMigrationBlueprint {
  company_id: string;
  company_name: string;
  target_backend: string;
  current_architecture: {
    application_services: any[];
    kubernetes_environments: string[];
    datadog_agents_detected: boolean;
    apm_instrumentation: string;
    log_collection_method: string;
    metrics_collection_method: string;
    trace_collection_method: string;
  };
  proposed_target_architecture: string;
  opentelemetry_strategy: string;
  collector_config_yaml: string;
  dual_shipping_strategy: string;
  data_compatibility_matrix: Record<string, string>;
  phases: MigrationPhase[];
  rollback_plan: {
    revert_steps: string[];
    data_preservation_strategy: string;
    monitoring_and_parity_checks: string[];
    irreversible_actions_warning: string[];
  };
  downtime_mitigation_and_risks: Array<Record<string, string>>;
}

export interface EmailVariant {
  variant_type: string;
  target_role: string;
  subject_lines: string[];
  preheader: string;
  body_markdown: string;
  call_to_action: string;
  referenced_attachments: string[];
}

export interface LinkedInSequence {
  step_1_connection_request: string;
  step_2_value_add: string;
  step_3_technical_commercial: string;
}

export interface OutreachPackage {
  company_name: string;
  company_id: string;
  target_challenger: string;
  distress_category: string;
  executive_emails: EmailVariant[];
  linkedin_sequence: LinkedInSequence;
  technical_pitch: {
    title: string;
    target_audience: string;
    architecture_comparison: Record<string, string>;
    zero_code_migration_path: string;
    dual_shipping_poc: string;
    alert_and_dashboard_parity: string;
    timeline_and_effort: string;
    full_pitch_markdown: string;
  };
  value_proposition: {
    executive_summary: string;
    current_estimated_runrate_annual: number;
    target_alternative_runrate_annual: number;
    annual_savings_usd: number;
    savings_percentage: number;
    datadog_tax_breakdown: Record<string, string>;
    tco_payback_period_months: number;
    three_year_net_savings_usd: number;
    risk_vs_reward: Array<Record<string, string>>;
    full_value_prop_markdown: string;
  };
  objection_matrix: {
    items: Array<{
      objection_id: string;
      objection: string;
      talking_points: string[];
      recommended_response: string;
      technical_proof_point: string;
    }>;
  };
  evidence_audit: {
    passed: boolean;
    claims_checked: number;
    verified_claims: number;
    inferred_or_estimated_claims: number;
    unsupported_claims_flagged: string[];
    buzzwords_detected: string[];
    hallucination_risk_score: number;
    audit_summary: string;
  };
  generated_at: string;
  governance_status: string;
}

export type WorkflowStatusType =
  | "PENDING"
  | "LISTENER_RUNNING"
  | "PROFILER_RUNNING"
  | "QUALIFICATION_REVIEW"
  | "FINOPS_RUNNING"
  | "ARCHITECT_RUNNING"
  | "COPYWRITER_RUNNING"
  | "DRAFT_PENDING_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "COMPLETED"
  | "FAILED";

export interface WorkflowResponse {
  workflow_id: string;
  workflow_type: string;
  status: WorkflowStatusType;
  current_step: string;
  signal_id?: string | null;
  company_id?: string | null;
  dossier_id?: string | null;
  target_challenger: string;
  retry_count: number;
  max_retries: number;
  execution_duration_ms: number;
  step_history: Array<{
    step_name: string;
    status: string;
    started_at: string;
    completed_at?: string | null;
    duration_ms: number;
    details: Record<string, any>;
    error_message?: string | null;
  }>;
  input_payload: Record<string, any>;
  output_payload: Record<string, any>;
  error_details?: string | null;
  is_synthetic: boolean;
  created_at: string;
  completed_at?: string | null;
}

export interface WorkflowMetricsResponse {
  total_workflows: number;
  by_status: Record<string, number>;
  completed_count: number;
  failed_count: number;
  disqualified_count: number;
  pending_approval_count: number;
  approved_count: number;
  average_duration_ms: number;
  active_running_workflows: number;
}

export interface SystemStatsSummary {
  signals_count: number;
  companies_count: number;
  qualified_prospects_count: number;
  dossiers_count: number;
  approved_count: number;
  potential_annual_savings_usd: number;
  agent_status?: Record<string, string>;
}

// ============================================================================
// CRUSTDATA INTELLIGENCE EXTRACTION TYPES
// ============================================================================

export type CrustdataEntityType = "COMPANY" | "PERSON" | "UNKNOWN";
export type CrustdataEnrichmentLevel = "LEVEL_1_SEARCH" | "LEVEL_2_STANDARD" | "LEVEL_3_DEEP";
export type VerificationClassification = "VERIFIED" | "INFERRED" | "UNKNOWN";

export interface CrustdataCreditsInfo {
  total_credits: number;
  remaining_credits: number;
  used_credits: number;
  renewal_date?: string | null;
  enabled_endpoints: string[];
  is_mock: boolean;
  data_origin?: "LIVE" | "CACHED" | "DEMO";
  source?: string;
  retrieved_at?: string;
  verification_status?: string;
  buying_intent_status?: string;
  buying_intent_note?: string | null;
  provenance?: Record<string, string>;
  checked_at: string;
}

export interface CriterionMatch {
  criterion: string;
  requested_value: string;
  actual_value?: string | null;
  status: "VERIFIED" | "INFERRED" | "UNAVAILABLE";
  evidence?: string | null;
}

export interface EntityCandidate {
  candidate_id: string;
  entity_type: CrustdataEntityType;
  name: string;
  primary_domain?: string | null;
  profile_url?: string | null;
  current_title?: string | null;
  company_name?: string | null;
  headline?: string | null;
  location?: string | null;
  logo_url?: string | null;
  confidence_score: number;
  is_ambiguous: boolean;
  is_mock: boolean;
  data_origin?: "LIVE" | "CACHED" | "DEMO";
  source?: string;
  retrieved_at?: string;
  verification_status?: string;
  buying_intent_status?: string;
  buying_intent_note?: string | null;
  provenance?: Record<string, string>;
  field_verification?: Record<string, string>;
  matched_criteria?: CriterionMatch[];
  raw_data?: Record<string, any> | null;
}

export interface EntitySearchResponse {
  query: string;
  detected_type: CrustdataEntityType;
  candidates: EntityCandidate[];
  is_ambiguous: boolean;
  credits_consumed: number;
  is_mock: boolean;
  data_origin?: "LIVE" | "CACHED" | "DEMO";
  interpretation?: any;
  buying_intent_distinction?: string | null;
  next_cursor?: string | null;
  total_results?: number | null;
  page_size?: number;
  current_page?: number;
}

export interface TechnographicItem {
  name: string;
  category: string;
  classification: VerificationClassification;
  source_url?: string | null;
  first_detected_at?: string | null;
  updated_at?: string | null;
}

export interface FundingRoundItem {
  round_name: string;
  amount_usd?: number | null;
  round_date?: string | null;
  investors: string[];
  lead_investor?: string | null;
}

export interface JobListingItem {
  job_id?: string | null;
  title: string;
  department?: string | null;
  location?: string | null;
  posted_at?: string | null;
  url?: string | null;
  required_technologies: string[];
}

export interface WorkHistoryItem {
  company_name: string;
  title: string;
  start_date?: string | null;
  end_date?: string | null;
  is_current: boolean;
  description?: string | null;
}

export interface IntelligenceEvidenceItem {
  data_category: string;
  claim: string;
  source_url?: string | null;
  retrieval_timestamp: string;
  confidence: number;
  verification_classification: VerificationClassification;
  metadata: Record<string, any>;
}

export interface CompanyIntelligenceProfile {
  entity_id: string;
  name: string;
  primary_domain: string;
  alternate_domains: string[];
  website?: string | null;
  linkedin_url?: string | null;
  twitter_url?: string | null;
  github_url?: string | null;
  description?: string | null;
  industry?: string | null;
  headcount?: string | null;
  headcount_timeseries: Array<Record<string, any>>;
  headcount_by_department: Record<string, number>;
  annual_revenue_range?: string | null;
  headquarters?: string | null;
  founding_year?: number | null;
  technographics: TechnographicItem[];
  funding_rounds: FundingRoundItem[];
  total_funding_usd?: number | null;
  leadership: Array<Record<string, any>>;
  active_jobs: JobListingItem[];
  competitors: Array<Record<string, any>>;
  social_posts: Array<Record<string, any>>;
  news_articles: Array<Record<string, any>>;
  evidence: IntelligenceEvidenceItem[];
  enrichment_level: CrustdataEnrichmentLevel;
  credits_consumed: number;
  data_freshness: string;
  retrieved_at: string;
  is_mock: boolean;
  data_origin?: "LIVE" | "CACHED" | "DEMO";
  source?: string;
  verification_status?: string;
  buying_intent_status?: string;
  buying_intent_note?: string | null;
  provenance?: Record<string, string>;
}

export interface PersonIntelligenceProfile {
  entity_id: string;
  full_name: string;
  current_title?: string | null;
  current_company?: string | null;
  headline?: string | null;
  location?: string | null;
  linkedin_url?: string | null;
  twitter_url?: string | null;
  github_url?: string | null;
  verified_work_email?: string | null;
  summary_bio?: string | null;
  is_decision_maker: boolean;
  decision_maker_score: number;
  work_history: WorkHistoryItem[];
  education: Array<Record<string, any>>;
  skills: string[];
  social_activity: Array<Record<string, any>>;
  evidence: IntelligenceEvidenceItem[];
  enrichment_level: CrustdataEnrichmentLevel;
  credits_consumed: number;
  data_freshness: string;
  retrieved_at: string;
  is_mock: boolean;
  data_origin?: "LIVE" | "CACHED" | "DEMO";
  source?: string;
  verification_status?: string;
  buying_intent_status?: string;
  buying_intent_note?: string | null;
  provenance?: Record<string, string>;
}

export interface DeepEnrichmentCostEstimate {
  entity_name: string;
  entity_type: CrustdataEntityType;
  target_identifier: string;
  estimated_credits: number;
  account_credits_available: number;
  safety_threshold: number;
  can_proceed: boolean;
  warning_message?: string | null;
}



export type CrustdataBudgetStatusType = "Active" | "Near Limit" | "Exhausted";

export interface CrustdataBudgetStatus {
  total_budget: number;
  used_credits: number;
  remaining_credits: number;
  usage_percentage: number;
  status: CrustdataBudgetStatusType;
  mock_used_credits: number;
  account_credits?: CrustdataCreditsInfo | null;
  is_exhausted: boolean;
}

export interface BudgetIncreaseRequest {
  amount: number;
  reason?: string;
  approved_by?: string;
}

export interface BudgetHistoryItem {
  id: string;
  action: string;
  amount: number;
  budget_before: number;
  budget_after: number;
  used_before: number;
  used_after: number;
  notes: string;
  is_mock: boolean;
  data_origin?: "LIVE" | "CACHED" | "DEMO";
  source?: string;
  retrieved_at?: string;
  verification_status?: string;
  buying_intent_status?: string;
  buying_intent_note?: string | null;
  provenance?: Record<string, string>;
  approved_by?: string | null;
  created_at: string;
}
