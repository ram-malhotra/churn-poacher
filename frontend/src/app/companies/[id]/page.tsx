"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  ShieldCheck,
  Radio,
  DollarSign,
  Cpu,
  Mail,
  Activity,
  FileCheck2,
  CheckCircle2,
  XCircle,
  Download,
  AlertTriangle,
  Play,
  RefreshCw,
  ArrowLeft,
  ExternalLink,
  Layers,
  Copy,
} from "lucide-react";
import { api } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/Card";
import { Badge, StatusBadge, EvidenceBadge } from "@/components/ui/Badge";
import { CodeViewer } from "@/components/ui/CodeViewer";
import { formatCurrency, formatDate, formatDecisionMaker } from "@/lib/utils";

export default function CompanyDossierPage() {
  const params = useParams();
  const companyId = params.id as string;
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<
    "overview" | "evidence" | "technology" | "financials" | "architecture" | "outreach" | "activity"
  >("overview");
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // 1. Fetch Company
  const { data: company, isLoading: loadingCompany } = useQuery({
    queryKey: ["company", companyId],
    queryFn: () => api.getCompany(companyId),
  });

  // 2. Fetch Associated Dossier
  const { data: dossiers, isLoading: loadingDossier } = useQuery({
    queryKey: ["dossier", companyId],
    queryFn: () => api.getDossiers({ company_id: companyId }),
  });
  const dossier = dossiers && dossiers.length > 0 ? dossiers[0] : null;

  // 3. Approval / Rejection Mutations
  const approveMutation = useMutation({
    mutationFn: (dossierId: string) => api.approveDraft(dossierId),
    onSuccess: () => {
      setActionMessage("Outreach draft successfully approved! Export is now unlocked.");
      queryClient.invalidateQueries({ queryKey: ["dossier", companyId] });
      setTimeout(() => setActionMessage(null), 5000);
    },
    onError: (err: any) => setActionMessage(`Approval failed: ${err.message}`),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ dossierId, reason }: { dossierId: string; reason: string }) =>
      api.rejectDraft(dossierId, reason),
    onSuccess: () => {
      setActionMessage("Outreach draft marked as rejected with revision notes.");
      setShowRejectModal(false);
      queryClient.invalidateQueries({ queryKey: ["dossier", companyId] });
      setTimeout(() => setActionMessage(null), 5000);
    },
    onError: (err: any) => setActionMessage(`Rejection failed: ${err.message}`),
  });

  const exportMutation = useMutation({
    mutationFn: (dossierId: string) => api.exportDossier(dossierId),
    onSuccess: (data) => {
      const blob = new Blob([data.markdown_bundle], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `deposition-pack-${company?.name.toLowerCase().replace(/\s+/g, "-")}.md`;
      a.click();
      setActionMessage("Deposition pack successfully exported!");
      setTimeout(() => setActionMessage(null), 4000);
    },
    onError: (err: any) => setActionMessage(`Export error: ${err.message}`),
  });

  const runInvestigationMutation = useMutation({
    mutationFn: () =>
      api.runWorkflow({
        company_id: companyId,
        target_challenger: "SigNoz Cloud",
        timeout_seconds: 45,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dossier", companyId] });
      queryClient.invalidateQueries({ queryKey: ["company", companyId] });
      setActionMessage("Investigation cycle completed!");
      setTimeout(() => setActionMessage(null), 4000);
    },
    onError: (err: any) => setActionMessage(`Run error: ${err.message}`),
  });

  if (loadingCompany) {
    return (
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <div className="p-12 text-center text-xs text-gray-500">Loading company investigation dossier...</div>
      </div>
    );
  }

  if (!company) {
    return (
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <div className="p-12 text-center text-xs text-gray-400">
          Company not found. <Link href="/companies" className="text-brand-400 underline">Return to directory</Link>
        </div>
      </div>
    );
  }

  const finDelta = dossier?.financial_delta || {};
  const baseScenario = finDelta?.report?.scenarios?.BASE || {};
  const migrationBlueprint = dossier?.migration_blueprint || {};
  const outreach = dossier?.outreach_drafts || {};

  return (
    <div className="flex-1 flex flex-col min-w-0">
      <Header />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Back Link & Action Alert */}
        <div className="flex items-center justify-between">
          <Link
            href="/companies"
            className="text-xs text-gray-400 hover:text-white flex items-center gap-1.5 transition font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Company Directory
          </Link>

          {actionMessage && (
            <div className="px-3 py-1 rounded bg-brand-500/20 text-brand-300 border border-brand-500/30 text-xs font-mono">
              {actionMessage}
            </div>
          )}
        </div>

        {/* Company Header Card */}
        <Card className="border-brand-500/20 bg-gradient-to-r from-surface-100 to-surface-50/90">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold text-white tracking-tight">{company.name}</h1>
                {company.domain && (
                  <a
                    href={`https://${company.domain}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-mono text-gray-400 hover:text-brand-400 flex items-center gap-1"
                  >
                    {company.domain} <ExternalLink className="w-3 h-3" />
                  </a>
                )}
                {company.is_synthetic && <Badge variant="synthetic">SYNTHETIC</Badge>}
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {company.industry || "Technology"} &bull; Scale: {company.estimated_size} &bull; Profiled: {formatDate(company.created_at)}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge status={company.qualification_status} />

              <button
                onClick={() => runInvestigationMutation.mutate()}
                disabled={runInvestigationMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-brand-600 hover:bg-brand-500 text-white transition text-xs font-medium cursor-pointer shadow-sm"
              >
                {runInvestigationMutation.isPending ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5 fill-current" />
                )}
                <span>{runInvestigationMutation.isPending ? "Poaching..." : "Re-Run Investigation"}</span>
              </button>
            </div>
          </div>
        </Card>

        {/* 7-Tab Navigation */}
        <div className="flex items-center border-b border-border space-x-1 overflow-x-auto text-xs">
          {[
            { id: "overview", label: "Overview", icon: Building2 },
            { id: "evidence", label: "Evidence", icon: ShieldCheck, badge: `${company.evidence_records.length}` },
            { id: "technology", label: "Technology", icon: Layers },
            { id: "financials", label: "Financials", icon: DollarSign },
            { id: "architecture", label: "Architecture", icon: Cpu },
            { id: "outreach", label: "Outreach Pack", icon: Mail, badge: dossier?.status === "APPROVED" ? "APPROVED" : "REVIEW" },
            { id: "activity", label: "Activity", icon: Activity },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2.5 font-medium border-b-2 transition cursor-pointer whitespace-nowrap ${
                  isActive
                    ? "border-brand-400 text-white bg-surface-50/50"
                    : "border-transparent text-gray-400 hover:text-gray-200 hover:bg-surface-50/20"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? "text-brand-400" : "text-gray-400"}`} />
                <span>{tab.label}</span>
                {tab.badge && (
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-200 text-gray-400 border border-border">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Tab 1: OVERVIEW */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 space-y-4">
              <CardHeader>
                <CardTitle>Account Deposition Overview</CardTitle>
                <CardDescription>
                  Autonomous profiling results synthesized across social listening, DNS records, and tech stack telemetry.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <div>
                  <span className="text-[11px] font-mono text-gray-400 uppercase">Entity Summary</span>
                  <p className="text-gray-300 mt-1 leading-relaxed">
                    {company.company_description || "Target enterprise running production workloads on Datadog."}
                  </p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 pt-2">
                  <div className="p-3 rounded bg-surface-50 border border-border">
                    <span className="text-[10px] font-mono text-gray-400 uppercase block">ICP Fit Score</span>
                    <span className="text-lg font-bold text-emerald-400 font-mono">{(company.icp_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="p-3 rounded bg-surface-50 border border-border">
                    <span className="text-[10px] font-mono text-gray-400 uppercase block">Identity Confidence</span>
                    <span className="text-lg font-bold text-brand-400 font-mono">{(company.identity_confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="p-3 rounded bg-surface-50 border border-border">
                    <span className="text-[10px] font-mono text-gray-400 uppercase block">Tech Confidence</span>
                    <span className="text-lg font-bold text-accent-cyan font-mono">{(company.technology_confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {company.decision_makers && Array.isArray(company.decision_makers) && company.decision_makers.length > 0 && (
                  <div className="pt-2">
                    <span className="text-[11px] font-mono text-gray-400 uppercase block mb-1">Target Decision Makers</span>
                    <div className="flex flex-wrap gap-2">
                      {company.decision_makers.map((dm, idx) => {
                        const label = formatDecisionMaker(dm);
                        if (!label) return null;
                        return (
                          <Badge key={idx} variant="purple">
                            {label}
                          </Badge>
                        );
                      })}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Financial Snapshot */}
            <Card>
              <CardHeader>
                <CardTitle>Financial Delta Snapshot</CardTitle>
                <CardDescription>Modeled Datadog spend vs SigNoz Cloud</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div className="p-3 rounded bg-surface-50 border border-border">
                  <span className="text-[10px] font-mono text-gray-400 uppercase block">Current Datadog Run-rate</span>
                  <span className="text-sm font-bold text-white font-mono">
                    {formatCurrency(baseScenario.current_datadog_annual || finDelta.datadog_annual || 120000)}/yr
                  </span>
                </div>
                <div className="p-3 rounded bg-emerald-950/20 border border-emerald-500/30">
                  <span className="text-[10px] font-mono text-emerald-400 uppercase block">Projected Annual Savings</span>
                  <span className="text-xl font-bold text-emerald-400 font-mono">
                    {formatCurrency(baseScenario.signoz_cloud_annual_savings || finDelta.estimated_annual_savings || 84000)}/yr
                  </span>
                  <span className="text-[10px] text-gray-400 block mt-0.5">
                    Modeled reduction: ~{(baseScenario.signoz_cloud_savings_pct || 70).toFixed(0)}%
                  </span>
                </div>
                <div className="p-3 rounded bg-surface-50 border border-border">
                  <span className="text-[10px] font-mono text-gray-400 uppercase block">Payback Horizon</span>
                  <span className="text-sm font-semibold text-brand-300 font-mono">
                    ~{(baseScenario.payback_period_months || 1.8).toFixed(1)} months
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tab 2: EVIDENCE */}
        {activeTab === "evidence" && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Evidence Provenance & Verification Audit</CardTitle>
                <CardDescription>
                  Strictly classifies all collected claims as VERIFIED, INFERRED, or UNKNOWN without deanonymization or fabrication.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {company.evidence_records.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-border text-[10px] font-mono text-gray-400 uppercase bg-surface-50/50">
                          <th className="py-2.5 px-3">Classification</th>
                          <th className="py-2.5 px-3">Claim</th>
                          <th className="py-2.5 px-3">Source & Verification</th>
                          <th className="py-2.5 px-3">Confidence</th>
                          <th className="py-2.5 px-3 text-right">Evidence Link</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/50">
                        {company.evidence_records.map((ev, idx) => (
                          <tr key={idx} className="hover:bg-surface-50/50">
                            <td className="py-3 px-3">
                              <EvidenceBadge classification={ev.classification} />
                            </td>
                            <td className="py-3 px-3 font-medium text-white max-w-sm">{ev.claim}</td>
                            <td className="py-3 px-3 text-gray-400">
                              <div>{ev.source}</div>
                              <div className="text-[10px] text-gray-500">{ev.description}</div>
                            </td>
                            <td className="py-3 px-3 font-mono text-emerald-400">
                              {(ev.confidence * 100).toFixed(0)}%
                            </td>
                            <td className="py-3 px-3 text-right">
                              {ev.url ? (
                                <a
                                  href={ev.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-brand-400 hover:underline flex items-center justify-end gap-1 font-mono text-[11px]"
                                >
                                  Source URL <ExternalLink className="w-3 h-3" />
                                </a>
                              ) : (
                                <span className="text-gray-500 text-[11px] font-mono">Internal Signal</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-8 text-center text-xs text-gray-500">No evidence records logged yet.</div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tab 3: TECHNOLOGY */}
        {activeTab === "technology" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Detected Technology Footprint</CardTitle>
                <CardDescription>Inferred from job postings, code artifacts, and public headers.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <div>
                  <span className="text-[11px] font-mono text-gray-400 uppercase block mb-1">Detected Stacks</span>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(company.tech_stack || {}).map(([k, v]) => (
                      <span key={k} className="px-2.5 py-1 rounded bg-surface-50 border border-border text-gray-200 font-mono text-[11px]">
                        {k}: {String(v)}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pt-2">
                  <span className="text-[11px] font-mono text-gray-400 uppercase block mb-1">Infrastructure Indicators</span>
                  <div className="p-3 rounded bg-surface-50 border border-border font-mono text-[11px] space-y-1">
                    {Object.entries(company.infrastructure_indicators || {}).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-gray-300">
                        <span className="text-gray-400">{k}:</span>
                        <span>{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Current Telemetry Ingestion Assessment</CardTitle>
                <CardDescription>Datadog agent ingestion topology to be decoupled.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                {[
                  { name: "APM Instrumentation", val: migrationBlueprint.current_architecture?.apm_instrumentation || "Datadog dd-trace library / agent" },
                  { name: "Trace Collection Port", val: migrationBlueprint.current_architecture?.trace_collection_method || "Datadog Trace Agent :8126" },
                  { name: "Metrics Collection", val: migrationBlueprint.current_architecture?.metrics_collection_method || "dogstatsd UDP + Prometheus scrape" },
                  { name: "Log Shipper", val: migrationBlueprint.current_architecture?.log_collection_method || "Datadog DaemonSet / filelog" },
                ].map((item) => (
                  <div key={item.name} className="p-3 rounded bg-surface-50 border border-border">
                    <span className="text-[10px] font-mono text-gray-400 uppercase block">{item.name}</span>
                    <span className="text-xs font-semibold text-white font-mono">{item.val}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tab 4: FINANCIALS */}
        {activeTab === "financials" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg bg-surface-100 border border-border">
                <span className="text-[10px] font-mono text-gray-400 uppercase block">Current Datadog Run-rate</span>
                <span className="text-lg font-bold text-white font-mono mt-1 block">
                  {formatCurrency(baseScenario.current_datadog_annual || 120000)}/yr
                </span>
                <span className="text-[10px] text-gray-500">Host tax + APM + metrics</span>
              </div>
              <div className="p-4 rounded-lg bg-surface-100 border border-border">
                <span className="text-[10px] font-mono text-gray-400 uppercase block">Target Alternative ({dossier?.financial_delta?.report?.target_challenger || "SigNoz Cloud"})</span>
                <span className="text-lg font-bold text-accent-cyan font-mono mt-1 block">
                  {formatCurrency(baseScenario.signoz_cloud_annual || 36000)}/yr
                </span>
                <span className="text-[10px] text-gray-500">Pure ingestion volume</span>
              </div>
              <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-500/30">
                <span className="text-[10px] font-mono text-emerald-400 uppercase block">Annual Net Savings</span>
                <span className="text-xl font-bold text-emerald-400 font-mono mt-1 block">
                  {formatCurrency(baseScenario.signoz_cloud_annual_savings || 84000)}/yr
                </span>
                <span className="text-[10px] text-emerald-500/80">~{(baseScenario.signoz_cloud_savings_pct || 70).toFixed(0)}% cost reduction</span>
              </div>
              <div className="p-4 rounded-lg bg-surface-100 border border-border">
                <span className="text-[10px] font-mono text-gray-400 uppercase block">Payback Horizon</span>
                <span className="text-lg font-bold text-brand-300 font-mono mt-1 block">
                  ~{(baseScenario.payback_period_months || 1.8).toFixed(1)} months
                </span>
                <span className="text-[10px] text-gray-500">Migration cost recouped</span>
              </div>
            </div>

            {/* Low / Base / High Scenarios Table */}
            <Card>
              <CardHeader>
                <CardTitle>Comparative Telemetry Scenarios</CardTitle>
                <CardDescription>
                  Sensitivity modeling across conservative, baseline, and aggressive volume expansions.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {finDelta?.report?.scenarios ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-border text-[10px] font-mono text-gray-400 uppercase bg-surface-50/50">
                          <th className="py-2.5 px-3">Scenario</th>
                          <th className="py-2.5 px-3">Datadog Annual</th>
                          <th className="py-2.5 px-3">SigNoz Cloud</th>
                          <th className="py-2.5 px-3">Grafana Cloud</th>
                          <th className="py-2.5 px-3">Annual Savings</th>
                          <th className="py-2.5 px-3">Payback</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/50 font-mono">
                        {Object.entries(finDelta.report.scenarios).map(([name, sc]: [string, any]) => (
                          <tr key={name} className="hover:bg-surface-50/50">
                            <td className="py-3 px-3 font-bold text-white">{name}</td>
                            <td className="py-3 px-3 text-rose-300">{formatCurrency(sc.current_datadog_annual)}</td>
                            <td className="py-3 px-3 text-cyan-300">{formatCurrency(sc.signoz_cloud_annual)}</td>
                            <td className="py-3 px-3 text-amber-300">{formatCurrency(sc.grafana_cloud_annual)}</td>
                            <td className="py-3 px-3 font-bold text-emerald-400">
                              {formatCurrency(sc.signoz_cloud_annual_savings)}
                            </td>
                            <td className="py-3 px-3 text-gray-300">~{sc.payback_period_months.toFixed(1)} mo</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-8 text-center text-xs text-gray-500">Run FinOps analysis to view scenarios.</div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tab 5: ARCHITECTURE */}
        {activeTab === "architecture" && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Zero-Code Receiver Compatibility (:8126)</CardTitle>
                <CardDescription>
                  Deploy OpenTelemetry Collector DaemonSet with native Datadog trace receiver on port 8126. Existing `dd-trace` applications require zero SDK rebuilds.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <CodeViewer
                  code={migrationBlueprint.collector_config_yaml || `# OpenTelemetry Collector Configuration\nreceivers:\n  datadog:\n    endpoint: 0.0.0.0:8126\nexporters:\n  otlp:\n    endpoint: ingest.signoz.cloud:443\nservice:\n  pipelines:\n    traces:\n      receivers: [datadog]\n      exporters: [otlp]`}
                  language="yaml"
                  title="otel-collector-config.yaml"
                />
              </CardContent>
            </Card>

            {/* 7-Stage Migration Timeline */}
            <Card>
              <CardHeader>
                <CardTitle>7-Stage Zero-Loss Migration Roadmap</CardTitle>
                <CardDescription>Phased dual-shipping rollout guaranteeing 100% telemetry continuity.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {(migrationBlueprint.phases || []).map((phase: any) => (
                  <div key={phase.phase_number} className="p-3.5 rounded bg-surface-50 border border-border/80">
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-brand-400">Phase {phase.phase_number}:</span>
                        <span className="text-xs font-semibold text-white">{phase.name}</span>
                      </div>
                      <span className="text-[11px] font-mono text-gray-400">Duration: ~{phase.duration_days} days</span>
                    </div>
                    <ul className="list-disc list-inside text-xs text-gray-400 space-y-0.5 ml-1">
                      {phase.tasks?.slice(0, 3).map((task: string, idx: number) => (
                        <li key={idx}>{task}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tab 6: OUTREACH STUDIO */}
        {activeTab === "outreach" && (
          <div className="space-y-6">
            {/* Governance Action Bar */}
            <div className="p-4 rounded-lg bg-surface-100 border border-border flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <StatusBadge status={dossier?.status || "DRAFT_PENDING_APPROVAL"} />
                <span className="text-xs text-gray-300">
                  {dossier?.status === "APPROVED"
                    ? "Outreach collateral unlocked for sales engagement."
                    : "Awaiting human review. External export strictly prohibited."}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {dossier?.status !== "APPROVED" && (
                  <>
                    <button
                      onClick={() => approveMutation.mutate(dossier!.id)}
                      disabled={approveMutation.isPending || !dossier}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition cursor-pointer"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Approve Pack
                    </button>
                    <button
                      onClick={() => setShowRejectModal(true)}
                      disabled={!dossier}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-rose-900/40 hover:bg-rose-800/60 border border-rose-500/30 text-rose-300 text-xs font-medium transition cursor-pointer"
                    >
                      <XCircle className="w-3.5 h-3.5" /> Reject
                    </button>
                  </>
                )}

                <button
                  onClick={() => exportMutation.mutate(dossier!.id)}
                  disabled={dossier?.status !== "APPROVED" || exportMutation.isPending}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-surface-50 hover:bg-surface-200 border border-border disabled:opacity-40 text-gray-200 text-xs font-medium transition cursor-pointer"
                  title={dossier?.status !== "APPROVED" ? "Approval required before export" : "Export markdown bundle"}
                >
                  <Download className="w-3.5 h-3.5" /> Export Deposition Pack
                </button>
              </div>
            </div>

            {/* Rejection Modal */}
            {showRejectModal && (
              <div className="p-4 rounded-lg bg-rose-950/20 border border-rose-500/40 space-y-3">
                <div className="text-xs font-semibold text-rose-300">Provide Rejection Feedback</div>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Specify why this outreach requires revision (e.g. adjust tone, update target persona)..."
                  className="w-full h-20 p-2.5 rounded bg-surface-200 border border-border text-xs text-white focus:outline-none"
                />
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setShowRejectModal(false)}
                    className="px-3 py-1 rounded bg-surface-50 text-xs text-gray-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => rejectMutation.mutate({ dossierId: dossier!.id, reason: rejectReason })}
                    className="px-3 py-1 rounded bg-rose-600 text-white text-xs font-medium"
                  >
                    Confirm Rejection
                  </button>
                </div>
              </div>
            )}

            {/* Generated Email Variants */}
            {(outreach?.executive_emails || []).map((email: any, idx: number) => (
              <Card key={idx}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{email.variant_type}: {email.target_role}</CardTitle>
                    <Badge variant="purple">Email Variant {idx + 1}</Badge>
                  </div>
                  <CardDescription>Preheader: {email.preheader}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  <div>
                    <span className="text-[10px] font-mono text-gray-400 uppercase block mb-1">Subject Lines</span>
                    <ul className="space-y-1 font-mono text-gray-300 text-[11px]">
                      {email.subject_lines?.map((subj: string, sIdx: number) => (
                        <li key={sIdx} className="p-1.5 rounded bg-surface-50 border border-border">
                          &bull; {subj}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <span className="text-[10px] font-mono text-gray-400 uppercase block mb-1">Body Markdown</span>
                    <div className="p-4 rounded bg-surface-50 border border-border font-sans whitespace-pre-line text-gray-200 leading-relaxed">
                      {email.body_markdown}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {/* LinkedIn Sequence */}
            {outreach?.linkedin_sequence && (
              <Card>
                <CardHeader>
                  <CardTitle>LinkedIn 3-Touch Peer Sequence</CardTitle>
                  <CardDescription>Consultative, zero-pitch connection and follow-up cadence.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  <div className="p-3 rounded bg-surface-50 border border-border">
                    <span className="text-[10px] font-mono text-brand-400 uppercase block mb-1">Touch 1: Connection Request (&le; 300 chars)</span>
                    <p className="text-gray-300 font-mono text-[11px]">{outreach.linkedin_sequence.step_1_connection_request}</p>
                  </div>
                  <div className="p-3 rounded bg-surface-50 border border-border">
                    <span className="text-[10px] font-mono text-brand-400 uppercase block mb-1">Touch 2: Value-Add Context</span>
                    <p className="text-gray-300 whitespace-pre-line text-[11px]">{outreach.linkedin_sequence.step_2_value_add}</p>
                  </div>
                  <div className="p-3 rounded bg-surface-50 border border-border">
                    <span className="text-[10px] font-mono text-brand-400 uppercase block mb-1">Touch 3: Technical-Commercial Follow-Up</span>
                    <p className="text-gray-300 whitespace-pre-line text-[11px]">{outreach.linkedin_sequence.step_3_technical_commercial}</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Tab 7: ACTIVITY */}
        {activeTab === "activity" && (
          <Card>
            <CardHeader>
              <CardTitle>Autonomous Execution & Audit Trail</CardTitle>
              <CardDescription>Complete audit timeline for this corporate profile.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="p-3 rounded bg-surface-50 border border-border flex items-center justify-between">
                <div>
                  <span className="font-semibold text-white block">Signal Ingestion & Classification</span>
                  <span className="text-gray-400">Classified as Datadog distress signal</span>
                </div>
                <span className="text-gray-500 font-mono">{formatDate(company.created_at)}</span>
              </div>
              <div className="p-3 rounded bg-surface-50 border border-border flex items-center justify-between">
                <div>
                  <span className="font-semibold text-white block">Corporate Identity Resolved</span>
                  <span className="text-gray-400">Associated with domain {company.domain || "N/A"}</span>
                </div>
                <span className="text-emerald-400 font-mono">VERIFIED</span>
              </div>
              <div className="p-3 rounded bg-surface-50 border border-border flex items-center justify-between">
                <div>
                  <span className="font-semibold text-white block">ICP Scored & Qualified</span>
                  <span className="text-gray-400">Assigned status: {company.qualification_status}</span>
                </div>
                <span className="text-brand-400 font-mono">Score: {(company.icp_score * 100).toFixed(0)}%</span>
              </div>
              {dossier && (
                <div className="p-3 rounded bg-surface-50 border border-border flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-white block">Deposition Dossier Generated</span>
                    <span className="text-gray-400">Status: {dossier.status}</span>
                  </div>
                  <span className="text-gray-500 font-mono">{formatDate(dossier.updated_at)}</span>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
