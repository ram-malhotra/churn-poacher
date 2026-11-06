import {
  Signal,
  Company,
  DepositionDossier,
  PricingEntry,
  FinancialDeltaReport,
  ArchitectureMigrationBlueprint,
  WorkflowResponse,
  WorkflowMetricsResponse,
  SystemStatsSummary,
  CrustdataCreditsInfo,
  EntitySearchResponse,
  CrustdataEntityType,
  CrustdataEnrichmentLevel,
  CrustdataBudgetStatus,
  BudgetIncreaseRequest,
  BudgetHistoryItem,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}/api/v1${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let errorDetail: any = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      // ignore
    }
    const message =
      typeof errorDetail === "string"
        ? errorDetail
        : errorDetail?.message || JSON.stringify(errorDetail);
    const err: any = new Error(message);
    err.status = response.status;
    err.detail = errorDetail;
    throw err;
  }

  return response.json();
}

function buildQueryString(params: Record<string, any> = {}): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (
      value !== undefined &&
      value !== null &&
      value !== "" &&
      value !== "undefined" &&
      value !== "null"
    ) {
      searchParams.append(key, String(value));
    }
  }
  const str = searchParams.toString();
  return str ? `?${str}` : "";
}

export const api = {
  // Signals
  async getSignals(params: Record<string, any> = {}): Promise<Signal[]> {
    return request<Signal[]>(`/signals${buildQueryString(params)}`);
  },

  async getSignal(id: string): Promise<Signal> {
    return request<Signal>(`/signals/${id}`);
  },

  // Companies
  async getCompanies(params: Record<string, any> = {}): Promise<Company[]> {
    return request<Company[]>(`/companies${buildQueryString(params)}`);
  },

  async getCompany(id: string): Promise<Company> {
    return request<Company>(`/companies/${id}`);
  },

  // Dossiers
  async getDossiers(params: Record<string, any> = {}): Promise<DepositionDossier[]> {
    return request<DepositionDossier[]>(`/dossiers${buildQueryString(params)}`);
  },

  async getDossier(id: string): Promise<DepositionDossier> {
    return request<DepositionDossier>(`/dossiers/${id}`);
  },

  // FinOps & Architecture
  async getFinOpsPricing(): Promise<PricingEntry[]> {
    return request<PricingEntry[]>("/finops/pricing");
  },

  async getFinOpsMetrics(): Promise<{
    dossiers_generated: number;
    total_potential_annual_savings_usd: number;
    average_payback_period_months: number;
    platforms_supported: string[];
  }> {
    return request("/finops/metrics");
  },

  async getFinOpsAnalysis(companyId: string): Promise<FinancialDeltaReport> {
    return request<FinancialDeltaReport>(`/finops/${companyId}`);
  },

  async getArchitectureBlueprint(companyId: string): Promise<ArchitectureMigrationBlueprint> {
    return request<ArchitectureMigrationBlueprint>(`/architecture/${companyId}`);
  },

  // Copywriter
  async getCopywriterMetrics(): Promise<{
    total_dossiers_with_drafts: number;
    pending_human_approval: number;
    approved: number;
    rejected: number;
    governance_rule: string;
  }> {
    return request("/copywriter/metrics");
  },

  async getCopywriterDrafts(companyId: string): Promise<{
    dossier_id: string;
    company_id: string;
    status: string;
    outreach_package: any;
  }> {
    return request(`/copywriter/${companyId}`);
  },

  async runCopywriter(companyId: string, challenger = "SigNoz Cloud"): Promise<any> {
    return request(`/copywriter/run/${companyId}?target_challenger=${encodeURIComponent(challenger)}`, {
      method: "POST",
    });
  },

  async approveDraft(dossierId: string): Promise<{ dossier_id: string; status: string; message: string }> {
    return request(`/copywriter/${dossierId}/approve`, { method: "PATCH" });
  },

  async rejectDraft(dossierId: string, reason: string): Promise<{ dossier_id: string; status: string; message: string }> {
    return request(`/copywriter/${dossierId}/reject`, {
      method: "PATCH",
      body: JSON.stringify({ reason }),
    });
  },

  async exportDossier(dossierId: string): Promise<{
    dossier_id: string;
    company_name: string;
    status: string;
    exported_at: string;
    outreach_package: any;
    markdown_bundle: string;
  }> {
    return request(`/copywriter/${dossierId}/export`, { method: "POST" });
  },

  // Orchestrator
  async runWorkflow(payload: {
    signal_id?: string;
    company_id?: string;
    target_challenger?: string;
    include_synthetic?: boolean;
    timeout_seconds?: number;
  }): Promise<WorkflowResponse> {
    return request<WorkflowResponse>("/orchestrator/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getWorkflowStatus(workflowId: string): Promise<WorkflowResponse> {
    return request<WorkflowResponse>(`/orchestrator/status/${workflowId}`);
  },

  async listWorkflows(params: Record<string, any> = {}): Promise<{ total: number; workflows: WorkflowResponse[] }> {
    return request<{ total: number; workflows: WorkflowResponse[] }>(`/orchestrator/workflows${buildQueryString(params)}`);
  },

  async getOrchestratorMetrics(): Promise<WorkflowMetricsResponse> {
    return request<WorkflowMetricsResponse>("/orchestrator/metrics");
  },

  async retryWorkflow(workflowId: string): Promise<WorkflowResponse> {
    return request<WorkflowResponse>(`/orchestrator/retry/${workflowId}`, {
      method: "POST",
    });
  },

  // Overview Stats
  async getStatsSummary(): Promise<SystemStatsSummary> {
    try {
      const overview = await request<any>("/stats/overview");
      return {
        signals_count: overview.signals_detected ?? 0,
        companies_count: overview.companies_identified ?? 0,
        qualified_prospects_count: overview.qualified_prospects ?? 0,
        dossiers_count: overview.dossiers_count ?? 0,
        approved_count: 0,
        potential_annual_savings_usd: overview.total_potential_annual_savings ?? 0,
        ...overview,
      };
    } catch {
      return {
        signals_count: 0,
        companies_count: 0,
        qualified_prospects_count: 0,
        dossiers_count: 0,
        approved_count: 0,
        potential_annual_savings_usd: 0,
      };
    }
  },

  async runListener(params: { include_synthetic?: boolean; max_items_per_source?: number } = {}): Promise<any> {
    return request("/listener/run", {
      method: "POST",
      body: JSON.stringify(params),
    });
  },

  async getLLMStatus(): Promise<{
    active_provider: string;
    configured_default: string;
    providers: Record<string, { name: string; available: boolean }>;
  }> {
    return request("/llm/status");
  },

  // Crustdata Intelligence Extraction
  async getCrustdataCredits(): Promise<CrustdataCreditsInfo> {
    return request<CrustdataCreditsInfo>("/crustdata/credits");
  },

  async getCrustdataBudget(): Promise<CrustdataBudgetStatus> {
    return request<CrustdataBudgetStatus>("/crustdata/budget");
  },

  async increaseCrustdataBudget(payload: BudgetIncreaseRequest): Promise<CrustdataBudgetStatus> {
    return request<CrustdataBudgetStatus>("/crustdata/budget/increase", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getCrustdataBudgetHistory(limit = 50): Promise<BudgetHistoryItem[]> {
    return request<BudgetHistoryItem[]>(`/crustdata/budget/history?limit=${limit}`);
  },

  async searchCrustdata(params: {
    query: string;
    entity_type?: CrustdataEntityType;
    limit?: number;
    cursor?: string | null;
    page?: number;
    mode?: "LIVE" | "DEMO";
  }): Promise<EntitySearchResponse> {
    return request<EntitySearchResponse>("/crustdata/search", {
      method: "POST",
      body: JSON.stringify(params),
    });
  },

  async interpretCrustdataQuery(query: string): Promise<any> {
    return request("/crustdata/interpret-query", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
  },

  async enrichCrustdata(params: {
    identifier: string;
    entity_type: CrustdataEntityType;
    level?: CrustdataEnrichmentLevel;
    force_refresh?: boolean;
    confirmation_confirmed?: boolean;
    mode?: "LIVE" | "DEMO";
  }): Promise<any> {
    return request("/crustdata/enrich", {
      method: "POST",
      body: JSON.stringify(params),
    });
  },

  async exportCrustdataReport(entity_id: string, export_format: "markdown" | "json" = "markdown"): Promise<any> {
    return request("/crustdata/export", {
      method: "POST",
      body: JSON.stringify({ entity_id, export_format }),
    });
  },

  async getCrustdataSearchHistory(limit = 20): Promise<any[]> {
    return request(`/crustdata/searches/history?limit=${limit}`);
  },
};

// Convenience helpers
export const fetchWorkflows = async (limit = 100): Promise<WorkflowResponse[]> => {
  const res = await api.listWorkflows({ limit });
  return res.workflows || [];
};

export const fetchWorkflowMetrics = async (): Promise<WorkflowMetricsResponse> => {
  return api.getOrchestratorMetrics();
};

export const fetchSystemStats = async (): Promise<SystemStatsSummary> => {
  return api.getStatsSummary();
};

export const triggerSyntheticSignal = async (): Promise<any> => {
  return api.runListener({ include_synthetic: true, max_items_per_source: 1 });
};

