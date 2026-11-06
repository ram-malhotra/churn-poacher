"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Radio,
  Building2,
  TrendingUp,
  DollarSign,
  FileCheck2,
  ArrowUpRight,
  Sparkles,
  Search,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Layers,
  Cpu,
  Globe2,
  ShieldAlert,
  Server,
  Compass,
  Clock,
  ExternalLink,
  ChevronRight,
  Filter,
} from "lucide-react";
import { api } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { MetricCard } from "@/components/ui/MetricCard";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { StatusBadge, Badge } from "@/components/ui/Badge";
import { formatCurrency, formatDate, cleanSignalText } from "@/lib/utils";
import { ObjectiveCriteria, SourceExecutionSummary } from "@/types";

const SAMPLE_PROMPTS = [
  {
    label: "Datadog → SigNoz / Grafana",
    text: "Find companies in the US and India experiencing high Datadog observability costs, unexpected billing increases, performance issues, or outages. Prioritize companies discussing migration to OpenTelemetry, Grafana, or SigNoz. Focus on companies with 200–5000 employees.",
  },
  {
    label: "Splunk → Elastic / OpenSearch",
    text: "Find enterprise companies suffering from massive Splunk license cost overruns and indexing fees. Prioritize teams evaluating migrations to Elastic or OpenSearch.",
  },
  {
    label: "New Relic → Grafana / OpenTelemetry",
    text: "Find engineering teams frustrated with New Relic full-platform user billing and considering migrations to Grafana Cloud and OpenTelemetry.",
  },
  {
    label: "Dynatrace → Grafana / OpenTelemetry",
    text: "Find enterprise organizations looking to replace Dynatrace host-unit pricing with OpenTelemetry-native monitoring.",
  },
];

export default function OverviewPage() {
  const queryClient = useQueryClient();

  // Natural Language Objective State
  const [objectiveInput, setObjectiveInput] = useState(
    "Find companies discussing Datadog pricing concerns or migration to OpenTelemetry."
  );
  const [monitoringMode, setMonitoringMode] = useState<"ON_DEMAND" | "SCHEDULED">("ON_DEMAND");
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | null>(null);

  // Queries
  const { data: stats } = useQuery({
    queryKey: ["statsSummary"],
    queryFn: () => api.getStatsSummary(),
  });

  const { data: signals, isLoading: loadingSignals } = useQuery({
    queryKey: ["recentSignals"],
    queryFn: () => api.getSignals({ limit: 8 }),
  });

  const { data: companies, isLoading: loadingCompanies } = useQuery({
    queryKey: ["topCompanies"],
    queryFn: () => api.getCompanies({ limit: 5, qualification_status: "ACCEPTED" }),
  });

  const { data: workflows, isLoading: loadingWorkflows } = useQuery({
    queryKey: ["recentWorkflows"],
    queryFn: () => api.listWorkflows({ limit: 5 }),
    refetchInterval: activeWorkflowId ? 2000 : false,
  });

  const { data: finopsMetrics } = useQuery({
    queryKey: ["finopsMetrics"],
    queryFn: () => api.getFinOpsMetrics(),
  });

  const { data: sources, isLoading: loadingSources, refetch: refetchSources } = useQuery<SourceExecutionSummary[]>({
    queryKey: ["listenerSources"],
    queryFn: () => api.getListenerSources(),
  });

  // Objective Interpretation Query
  const {
    data: parsedCriteria,
    isLoading: interpretingObjective,
    refetch: reInterpret,
  } = useQuery<ObjectiveCriteria>({
    queryKey: ["interpretObjective", objectiveInput],
    queryFn: () => api.interpretObjective(objectiveInput),
    enabled: Boolean(objectiveInput.trim()),
    staleTime: 5000,
  });

  // Active Workflow Query
  const { data: currentWorkflow } = useQuery({
    queryKey: ["workflowStatus", activeWorkflowId],
    queryFn: () => api.getWorkflowStatus(activeWorkflowId!),
    enabled: Boolean(activeWorkflowId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "DRAFT_PENDING_APPROVAL" || status === "COMPLETED" || status === "FAILED" || status === "REJECTED") {
        return false;
      }
      return 1500;
    },
  });

  // Run Pipeline Mutation
  const runMutation = useMutation({
    mutationFn: async () => {
      const res = await api.runWorkflow({
        objective: objectiveInput,
        monitoring_mode: monitoringMode,
        include_synthetic: false, // Live objective mode: do NOT invent synthetic data
        target_challenger: "SigNoz Cloud",
      });
      return res;
    },
    onSuccess: (data) => {
      setActiveWorkflowId(data.workflow_id);
      queryClient.invalidateQueries({ queryKey: ["recentSignals"] });
      queryClient.invalidateQueries({ queryKey: ["recentWorkflows"] });
      queryClient.invalidateQueries({ queryKey: ["listenerSources"] });
      queryClient.invalidateQueries({ queryKey: ["statsSummary"] });
      queryClient.invalidateQueries({ queryKey: ["activeCampaign"] });
    },
  });

  const handleRunPipeline = () => {
    if (!objectiveInput.trim()) return;
    runMutation.mutate();
  };

  const handleSelectPreset = (text: string) => {
    setObjectiveInput(text);
  };

  return (
    <div className="flex-1 flex flex-col min-w-0">
      <Header
        title="Intelligence Overview"
        description="Discover competitor weaknesses, identify high-intent prospects, and automate evidence-backed customer acquisition."
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* KPI Metric Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <MetricCard
            title="Total Signals"
            value={stats?.signals_count ?? "..."}
            subtitle="Public vendor complaints"
            icon={Radio}
            trend="+12% this week"
            trendPositive
          />
          <MetricCard
            title="Companies Identified"
            value={stats?.companies_count ?? "..."}
            subtitle="Verified employer profiles"
            icon={Building2}
          />
          <MetricCard
            title="Qualified Prospects"
            value={stats?.qualified_prospects_count ?? "..."}
            subtitle="ICP fit score >= 0.75"
            icon={TrendingUp}
            trend="High conviction"
            trendPositive
          />
          <MetricCard
            title="Dossiers Generated"
            value={stats?.dossiers_count ?? "..."}
            subtitle="Takeout blueprints ready"
            icon={FileCheck2}
          />
          <MetricCard
            title="Potential Savings"
            value={formatCurrency(
              finopsMetrics?.total_potential_annual_savings_usd ?? stats?.potential_annual_savings_usd ?? 0
            )}
            subtitle="Annual modeled delta"
            icon={DollarSign}
            className="border-emerald-500/20 bg-gradient-to-br from-surface-100 to-emerald-950/15"
          />
        </div>

        {/* ========================================================= */}
        {/* SECTION 1: "What opportunities are you looking for?"      */}
        {/* ========================================================= */}
        <Card className="border-brand-500/30 bg-gradient-to-b from-surface-100 to-surface-50/50 shadow-xl">
          <CardHeader className="pb-3 border-b border-border/60">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-brand-500/20 border border-brand-500/40 flex items-center justify-center text-brand-400">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <CardTitle className="text-base text-white">What opportunities are you looking for?</CardTitle>
                  <p className="text-xs text-gray-400">
                    Describe your target prospects, pains, technologies, and geography in natural language.
                  </p>
                </div>
              </div>

              {/* Mode Selector */}
              <div className="flex items-center gap-2 bg-surface-200/80 p-1 rounded-lg border border-border text-xs">
                <button
                  type="button"
                  onClick={() => setMonitoringMode("ON_DEMAND")}
                  className={`px-3 py-1 rounded-md transition font-medium ${
                    monitoringMode === "ON_DEMAND"
                      ? "bg-brand-500 text-white shadow-sm"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  On-Demand Search
                </button>
                <button
                  type="button"
                  onClick={() => setMonitoringMode("SCHEDULED")}
                  className={`px-3 py-1 rounded-md transition font-medium ${
                    monitoringMode === "SCHEDULED"
                      ? "bg-amber-500 text-black shadow-sm font-semibold"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  Scheduled Monitoring
                </button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="pt-4 space-y-4">
            {/* Input Box */}
            <div className="space-y-2">
              <div className="relative">
                <textarea
                  value={objectiveInput}
                  onChange={(e) => setObjectiveInput(e.target.value)}
                  placeholder="e.g. Find companies in the US and India experiencing high Datadog observability costs, unexpected billing increases, or outages. Prioritize companies discussing migration to OpenTelemetry, Grafana, or SigNoz. Focus on companies with 200–5000 employees."
                  rows={3}
                  className="w-full bg-surface-200/90 border border-border/80 focus:border-brand-500/70 rounded-lg p-3 text-sm text-gray-100 placeholder:text-gray-500 outline-none transition focus:ring-1 focus:ring-brand-500/50 resize-y font-sans"
                />
              </div>

              {/* Preset Chips */}
              <div className="flex flex-wrap items-center gap-1.5 text-xs">
                <span className="text-[11px] uppercase tracking-wider text-gray-500 font-mono mr-1">Examples:</span>
                {SAMPLE_PROMPTS.map((prompt) => (
                  <button
                    key={prompt.label}
                    type="button"
                    onClick={() => handleSelectPreset(prompt.text)}
                    className="px-2.5 py-1 rounded bg-surface-200 hover:bg-surface-300 border border-border/70 text-gray-300 hover:text-white transition text-xs"
                  >
                    {prompt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Mode Banner */}
            {monitoringMode === "SCHEDULED" && (
              <div className="p-2.5 rounded-md bg-amber-950/20 border border-amber-600/30 flex items-start gap-2 text-xs text-amber-300">
                <AlertCircle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
                <div>
                  <span className="font-semibold">Scheduled Monitoring:</span> Periodic background polling requires a
                  running background worker daemon (Redis/Celery). Clicking &quot;Run Pipeline&quot; will initiate an immediate
                  on-demand run while registering this objective for the active schedule.
                </div>
              </div>
            )}

            {/* Interpreted Search Criteria Box */}
            {parsedCriteria && (
              <div className="p-3.5 rounded-lg bg-surface-200/60 border border-border/80 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Filter className="w-3.5 h-3.5 text-brand-400" />
                    <span className="text-xs font-semibold text-gray-200 uppercase font-mono tracking-wider">
                      Interpreted Search Criteria
                    </span>
                    {interpretingObjective && <span className="text-[10px] text-gray-400 animate-pulse">Parsing...</span>}
                  </div>
                  <span className="text-[11px] text-gray-400 font-mono">
                    Target Incumbent: <strong className="text-brand-400">{parsedCriteria.target_vendor}</strong>
                  </span>
                </div>

                <div className="flex flex-wrap gap-1.5 text-xs">
                  {/* Geography */}
                  {parsedCriteria.target_geography.length > 0 ? (
                    parsedCriteria.target_geography.map((geo) => (
                      <span key={geo} className="px-2 py-0.5 rounded bg-blue-950/40 border border-blue-500/30 text-blue-300 text-[11px] flex items-center gap-1 font-mono">
                        <Globe2 className="w-3 h-3" /> Geo: {geo}
                      </span>
                    ))
                  ) : (
                    <span className="px-2 py-0.5 rounded bg-surface-300/40 border border-border text-gray-400 text-[11px] font-mono">
                      Geo: Any (unrestricted)
                    </span>
                  )}

                  {/* Size */}
                  {parsedCriteria.target_company_size ? (
                    <span className="px-2 py-0.5 rounded bg-purple-950/40 border border-purple-500/30 text-purple-300 text-[11px] flex items-center gap-1 font-mono">
                      <Building2 className="w-3 h-3" />
                      Size:{" "}
                      {parsedCriteria.target_company_size.min && parsedCriteria.target_company_size.max
                        ? `${parsedCriteria.target_company_size.min}–${parsedCriteria.target_company_size.max} emp`
                        : parsedCriteria.target_company_size.min
                        ? `>${parsedCriteria.target_company_size.min} emp`
                        : `<${parsedCriteria.target_company_size.max} emp`}
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded bg-surface-300/40 border border-border text-gray-400 text-[11px] font-mono">
                      Size: Any
                    </span>
                  )}

                  {/* Industry */}
                  {parsedCriteria.target_industry ? (
                    <span className="px-2 py-0.5 rounded bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-[11px] font-mono">
                      Industry: {parsedCriteria.target_industry}
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded bg-surface-300/40 border border-border text-gray-400 text-[11px] font-mono">
                      Industry: Any
                    </span>
                  )}

                  {/* Migration Intent */}
                  {parsedCriteria.migration_intent && (
                    <span className="px-2 py-0.5 rounded bg-emerald-950/50 border border-emerald-500/40 text-emerald-300 text-[11px] flex items-center gap-1 font-mono font-semibold">
                      <TrendingUp className="w-3 h-3" /> Migration Intent: Active
                    </span>
                  )}

                  {/* Alternative Technologies */}
                  {parsedCriteria.alternative_technologies.map((alt) => (
                    <span key={alt} className="px-2 py-0.5 rounded bg-cyan-950/40 border border-cyan-500/30 text-cyan-300 text-[11px] font-mono">
                      Challenger: {alt}
                    </span>
                  ))}

                  {/* Pain Points */}
                  {parsedCriteria.pain_points.map((pp) => (
                    <span key={pp} className="px-2 py-0.5 rounded bg-red-950/40 border border-red-500/30 text-red-300 text-[11px] font-mono">
                      Pain: {pp.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>

                {/* Tailored Search Queries */}
                <div className="pt-2 border-t border-border/40 flex items-center gap-2 text-[11px] text-gray-400 font-mono flex-wrap">
                  <span className="text-gray-500">Tailored Listener Queries:</span>
                  {parsedCriteria.search_queries.map((q) => (
                    <code key={q} className="bg-surface-300/80 px-2 py-0.5 rounded text-gray-200 border border-border/60">
                      &quot;{q}&quot;
                    </code>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                Anti-hallucination active: Live signals & verified profiles only.
              </span>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => reInterpret()}
                  disabled={interpretingObjective}
                  className="px-3.5 py-2 rounded-lg border border-border bg-surface-200 hover:bg-surface-300 text-xs text-gray-300 font-medium transition"
                >
                  {interpretingObjective ? "Interpreting..." : "Re-interpret Criteria"}
                </button>

                <button
                  type="button"
                  onClick={handleRunPipeline}
                  disabled={runMutation.isPending || !objectiveInput.trim()}
                  className="px-5 py-2 rounded-lg bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-brand-500/20 transition"
                >
                  {runMutation.isPending ? (
                    <>
                      <RotateCcw className="w-4 h-4 animate-spin" /> Running Pipeline...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-white" /> Run Pipeline
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Active Execution Banner */}
            {currentWorkflow && (
              <div className="p-3.5 rounded-lg bg-surface-200/90 border border-brand-500/40 space-y-2 mt-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-brand-500"></span>
                    </span>
                    <span className="text-xs font-mono font-semibold text-white">
                      Active Execution: {currentWorkflow.workflow_id.slice(0, 8)}...
                    </span>
                  </div>
                  <StatusBadge status={currentWorkflow.status} />
                </div>

                {/* 7-Stage Milestone Tracker */}
                <div className="grid grid-cols-7 gap-1 pt-1 text-[10px] font-mono text-center">
                  {[
                    "LISTENER",
                    "PROFILER",
                    "QUALIFICATION",
                    "FINOPS",
                    "ARCHITECT",
                    "COPYWRITER",
                    "APPROVAL_GATE",
                  ].map((step, idx) => {
                    const isCompleted = currentWorkflow.step_history?.some(
                      (s: any) => s.step_name === step && (s.status === "SUCCESS" || s.status === "PENDING_APPROVAL")
                    );
                    const isCurrent = currentWorkflow.current_step === step;

                    return (
                      <div
                        key={step}
                        className={`p-1.5 rounded border ${
                          isCompleted
                            ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300 font-semibold"
                            : isCurrent
                            ? "bg-brand-950/40 border-brand-500 text-brand-300 animate-pulse font-semibold"
                            : "bg-surface-300/30 border-border/50 text-gray-500"
                        }`}
                      >
                        <div className="text-[9px] text-gray-400">{idx + 1}</div>
                        <div className="truncate">{step}</div>
                      </div>
                    );
                  })}
                </div>

                {/* Human Review Reminder if at APPROVAL_GATE */}
                {currentWorkflow.status === "DRAFT_PENDING_APPROVAL" && (
                  <div className="p-2 rounded bg-amber-950/30 border border-amber-600/40 flex items-center justify-between text-xs text-amber-200">
                    <span className="flex items-center gap-1.5">
                      <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                      Pipeline completed all 7 stages. Deposition dossier held for human approval.
                    </span>
                    <Link
                      href="/outreach"
                      className="px-2.5 py-1 bg-amber-500 hover:bg-amber-400 text-black font-semibold rounded text-xs transition"
                    >
                      Review & Approve Drafts &rarr;
                    </Link>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* ========================================================= */}
        {/* SECTION 2: Listener Results Dashboard (Operational Sources) */}
        {/* ========================================================= */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-base text-white">Listener Sources & Feeds</CardTitle>
              <p className="text-xs text-gray-400">
                Operational status across all configured public intelligence feeds.
              </p>
            </div>
            <button
              onClick={() => refetchSources()}
              className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Refresh status
            </button>
          </CardHeader>
          <CardContent>
            {loadingSources ? (
              <div className="py-6 text-center text-xs text-gray-500">Checking public source feeds...</div>
            ) : sources && sources.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                {sources.map((src) => {
                  const isConfigured = src.connection_status === "CONNECTED";
                  return (
                    <div
                      key={src.source_name}
                      className={`p-3 rounded-lg border flex flex-col justify-between ${
                        isConfigured
                          ? "bg-surface-100 border-border/80"
                          : "bg-surface-100/50 border-border/40 opacity-80"
                      }`}
                    >
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-xs text-white">{src.source_name}</span>
                          <span
                            className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                              isConfigured
                                ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800"
                                : "bg-zinc-800 text-zinc-400 border border-zinc-700"
                            }`}
                          >
                            {src.connection_status}
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-400 leading-snug">{src.notes}</p>
                      </div>

                      <div className="pt-2 mt-2 border-t border-border/50 text-[10px] font-mono text-gray-400 space-y-1">
                        <div className="flex justify-between">
                          <span>Status:</span>
                          <span className={src.monitoring_status === "COMPLETED" ? "text-emerald-400" : "text-gray-300"}>
                            {src.monitoring_status}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Records Retrieved:</span>
                          <span className="text-white font-semibold">{src.records_retrieved}</span>
                        </div>
                        {src.errors && src.errors.length > 0 && (
                          <div className="text-amber-400/90 truncate" title={src.errors[0]}>
                            Note: {src.errors[0]}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-gray-500">No listener sources found.</div>
            )}
          </CardContent>
        </Card>

        {/* ========================================================= */}
        {/* SECTION 3: Main Grid (Top Opportunities & Distress Signals) */}
        {/* ========================================================= */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Opportunities */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div>
                <CardTitle>Top Migration Opportunities</CardTitle>
                <p className="text-xs text-gray-400">Accepted companies with verified Datadog usage and high ICP fit.</p>
              </div>
              <Link
                href="/companies"
                className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 font-medium"
              >
                View all <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </CardHeader>
            <CardContent>
              {loadingCompanies ? (
                <div className="py-8 text-center text-xs text-gray-500">Loading company profiles...</div>
              ) : companies && companies.length > 0 ? (
                <div className="divide-y divide-border/60">
                  {companies.map((c) => (
                    <div key={c.id} className="py-3 flex items-center justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <Link
                            href={`/companies/${c.id}`}
                            className="font-medium text-xs text-white hover:text-brand-400 transition"
                          >
                            {c.name}
                          </Link>
                          {c.is_synthetic ? (
                            <Badge variant="synthetic">SYNTHETIC</Badge>
                          ) : (
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800">
                              VERIFIED
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-gray-400 mt-0.5">
                          {c.industry || "Technology"} &bull; {c.estimated_size}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <span className="text-xs font-mono font-semibold text-emerald-400">
                            ICP: {(c.icp_score * 100).toFixed(0)}%
                          </span>
                          <span className="block text-[10px] text-gray-500">
                            ID Conf: {(c.identity_confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <StatusBadge status={c.qualification_status} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-gray-500">
                  No accepted companies found yet. Click &quot;Run Pipeline&quot; to discover targets.
                </div>
              )}
            </CardContent>
          </Card>

          {/* Incoming Distress Signals with Provenance */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div>
                <CardTitle>Public Distress Signals</CardTitle>
                <p className="text-xs text-gray-400">Live vents, billing shocks, and migration discussions.</p>
              </div>
              <Link
                href="/signals"
                className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 font-medium"
              >
                View monitor <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </CardHeader>
            <CardContent>
              {loadingSignals ? (
                <div className="py-8 text-center text-xs text-gray-500">Loading incoming signals...</div>
              ) : signals && signals.length > 0 ? (
                <div className="divide-y divide-border/60">
                  {signals.map((s) => (
                    <div key={s.id} className="py-3 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <Badge variant="purple">{s.source}</Badge>
                          <Badge variant="danger">{s.complaint_category}</Badge>
                          {/* Explicit Data Provenance */}
                          {s.is_synthetic ? (
                            <Badge variant="synthetic">SYNTHETIC</Badge>
                          ) : (
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800">
                              LIVE
                            </span>
                          )}
                        </div>
                        <span className="text-[11px] font-mono text-gray-500">{formatDate(s.created_at)}</span>
                      </div>
                      <p className="text-xs text-gray-300 line-clamp-2 leading-relaxed">
                        &ldquo;{cleanSignalText(s.raw_content)}&rdquo;
                      </p>
                      <div className="flex items-center justify-between text-[11px] text-gray-500">
                        <div className="flex items-center gap-3">
                          <span>Urgency: {(s.urgency_score * 10).toFixed(1)}/10</span>
                          {s.author_handle && <span>Author: @{s.author_handle}</span>}
                        </div>
                        <a
                          href={s.original_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-brand-400 hover:underline flex items-center gap-1"
                        >
                          Source <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-gray-500">
                  No signals detected. Click &quot;Run Pipeline&quot; to fetch public feeds.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ========================================================= */}
        {/* SECTION 4: Orchestrator Workflows History                 */}
        {/* ========================================================= */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle>Recent Orchestrator Workflows</CardTitle>
              <p className="text-xs text-gray-400">
                Autonomous execution tracking through the 7-phase state machine.
              </p>
            </div>
            <Link
              href="/history"
              className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 font-medium"
            >
              Full history <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </CardHeader>
          <CardContent>
            {loadingWorkflows ? (
              <div className="py-8 text-center text-xs text-gray-500">Loading workflows...</div>
            ) : workflows && workflows.workflows.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-border/80 text-[10px] font-mono text-gray-400 uppercase">
                      <th className="py-2">Workflow ID</th>
                      <th className="py-2">Current Step</th>
                      <th className="py-2">Status</th>
                      <th className="py-2">Duration</th>
                      <th className="py-2">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {workflows.workflows.map((wf) => (
                      <tr key={wf.workflow_id} className="hover:bg-surface-50/50 transition">
                        <td className="py-2.5 font-mono text-white">
                          <Link href={`/history`} className="hover:text-brand-400">
                            {wf.workflow_id.slice(0, 8)}...
                          </Link>
                        </td>
                        <td className="py-2.5 font-mono text-gray-300">{wf.current_step}</td>
                        <td className="py-2.5">
                          <StatusBadge status={wf.status} />
                        </td>
                        <td className="py-2.5 font-mono text-gray-400">
                          {wf.execution_duration_ms > 0 ? `${(wf.execution_duration_ms / 1000).toFixed(1)}s` : "-"}
                        </td>
                        <td className="py-2.5 font-mono text-gray-500">{formatDate(wf.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-8 text-center text-xs text-gray-500">No recent workflow executions found.</div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
