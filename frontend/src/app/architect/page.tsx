"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Cpu,
  Layers,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { CodeViewer } from "@/components/ui/CodeViewer";

export default function MigrationArchitectPage() {
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");

  const { data: companies } = useQuery({
    queryKey: ["allCompaniesForArchitect"],
    queryFn: () => api.getCompanies({ limit: 50 }),
  });

  const eligibleCompanies = React.useMemo(() => {
    return (companies || []).filter((c) => c.qualification_status !== "REJECTED");
  }, [companies]);

  const activeCompanyId = selectedCompanyId || (eligibleCompanies && eligibleCompanies.length > 0 ? eligibleCompanies[0].id : "");

  const { data: blueprint, isLoading, error: blueprintError } = useQuery({
    queryKey: ["architectureBlueprint", activeCompanyId],
    queryFn: () => api.getArchitectureBlueprint(activeCompanyId),
    enabled: Boolean(activeCompanyId),
  });

  const yamlContent = React.useMemo(() => {
    if (!activeCompanyId) {
      return "# No companies available.\n# Ingest signals and run the pipeline to generate target architecture blueprints.";
    }
    if (isLoading) {
      return "# Loading OpenTelemetry Collector YAML from architecture engine...";
    }
    if (blueprintError) {
      return `# API Error loading blueprint: ${(blueprintError as Error).message || "Unable to fetch blueprint"}`;
    }
    if (blueprint?.collector_config_yaml) {
      return blueprint.collector_config_yaml;
    }
    return "# Company selected, but migration blueprint has not been generated yet.\n# Run the investigation pipeline for this account to synthesize the dual-shipping collector configuration.";
  }, [activeCompanyId, isLoading, blueprintError, blueprint]);

  return (
    <div className="flex-1 flex flex-col min-w-0">
      <Header
        title="Migration Architect"
        description="Zero-code OpenTelemetry receiver pipelines (:8126), dual-shipping blueprints, and zero-loss rollback playbooks."
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Company Selector */}
        {eligibleCompanies && eligibleCompanies.length > 0 ? (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-100 border border-border">
            <span className="text-xs text-gray-400 font-medium">Select Target Organization:</span>
            <select
              value={activeCompanyId}
              onChange={(e) => setSelectedCompanyId(e.target.value)}
              className="bg-surface-50 border border-border text-xs text-white rounded px-3 py-1.5 focus:outline-none"
            >
              {eligibleCompanies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.qualification_status} · {c.estimated_size})
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div className="p-4 rounded-lg bg-surface-100 border border-border text-xs text-gray-400 text-center">
            No qualified accounts available. Ingest signals and run the pipeline to generate architecture blueprints.
          </div>
        )}

        {/* Architectural Transition Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="border-rose-500/20 bg-gradient-to-br from-surface-100 to-rose-950/10">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-rose-300">Legacy Architecture (Datadog)</CardTitle>
                <Badge variant="danger">PROPRIETARY LOCK-IN</Badge>
              </div>
              <CardDescription>Closed-source proprietary daemonset with host tax licensing.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="p-3 rounded bg-surface-50/80 border border-border space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-400">Agent DaemonSet:</span>
                  <span className="font-mono text-white">Datadog Agent 7</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Tracing Library:</span>
                  <span className="font-mono text-white">dd-trace (Proprietary)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Host Tax Surcharge:</span>
                  <span className="font-mono text-rose-400 font-bold">$15–$31 / node / mo</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Backend Index:</span>
                  <span className="font-mono text-white">Blackbox multi-tenant SaaS</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-emerald-500/20 bg-gradient-to-br from-surface-100 to-emerald-950/10">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-emerald-300">Target Architecture ({blueprint?.target_backend || "SigNoz Cloud"})</CardTitle>
                <Badge variant="success">CNCF OPEN STANDARD</Badge>
              </div>
              <CardDescription>OpenTelemetry Collector with native Datadog trace compatibility.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="p-3 rounded bg-surface-50/80 border border-border space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-400">Collector DaemonSet:</span>
                  <span className="font-mono text-emerald-400 font-bold">OTel Collector Contrib</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Receiver Port:</span>
                  <span className="font-mono text-emerald-400 font-bold">:8126 (Native dd-trace receiver)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Host Tax:</span>
                  <span className="font-mono text-emerald-400 font-bold">$0 (Zero Node Tax)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Storage Backend:</span>
                  <span className="font-mono text-white">High-performance ClickHouse</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* OpenTelemetry Collector YAML */}
        <Card>
          <CardHeader>
            <CardTitle>OpenTelemetry Collector Production Configuration</CardTitle>
            <CardDescription>
              Drop-in DaemonSet YAML mapping port 8126 to OTLP exporters while preserving simultaneous dual-shipping to Datadog.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CodeViewer
              code={yamlContent}
              language="yaml"
              title="otel-collector-production.yaml"
            />
          </CardContent>
        </Card>

        {/* 7-Stage Phased Migration Plan */}
        <Card>
          <CardHeader>
            <CardTitle>7-Stage Zero-Loss Migration Roadmap</CardTitle>
            <CardDescription>
              Sequenced milestones preventing production outages, metric loss, and operational disruption.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {!activeCompanyId ? (
              <div className="py-6 text-center text-xs text-gray-500">
                No target organization selected. Select or qualify an organization to view migration stages.
              </div>
            ) : isLoading ? (
              <div className="py-6 text-center text-xs text-gray-500">
                Loading migration stages from architecture engine...
              </div>
            ) : blueprint?.phases && blueprint.phases.length > 0 ? (
              blueprint.phases.map((phase: any) => (
                <div key={phase.phase_number} className="p-4 rounded-lg bg-surface-50 border border-border">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-brand-400">Stage {phase.phase_number}:</span>
                      <span className="text-xs font-semibold text-white">{phase.name}</span>
                    </div>
                    <span className="text-[11px] font-mono text-gray-400">Window: ~{phase.duration_days} days</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-1">
                    <div>
                      <span className="text-[10px] font-mono text-gray-400 uppercase block mb-1">Key Tasks</span>
                      <ul className="list-disc list-inside space-y-0.5 text-gray-300">
                        {phase.tasks?.map((t: string, idx: number) => (
                          <li key={idx}>{t}</li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <span className="text-[10px] font-mono text-emerald-400 uppercase block mb-1">Success Criteria</span>
                      <ul className="list-disc list-inside space-y-0.5 text-gray-300">
                        {phase.success_criteria?.map((sc: string, idx: number) => (
                          <li key={idx}>{sc}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-6 text-center text-xs text-gray-500">
                No migration phases generated for this account yet. Run the investigation pipeline to generate milestones.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Zero-Loss Rollback Procedure */}
        <Card className="border-amber-500/20 bg-amber-950/10">
          <CardHeader>
            <div className="flex items-center gap-2 text-amber-300">
              <RotateCcw className="w-4 h-4" />
              <CardTitle className="text-amber-300">Zero-Loss Rollback Playbook</CardTitle>
            </div>
            <CardDescription>Instant fail-safe procedure in case of telemetry drift or compatibility failure.</CardDescription>
          </CardHeader>
          <CardContent className="text-xs space-y-2 text-gray-300">
            <p>
              Because the OpenTelemetry Collector dual-ships traffic, Datadog remains active throughout Stages 1–6. 
              Rolling back requires a single config change: disable the OTLP target exporter in the collector DaemonSet. 
              Zero application code changes, zero metric blackouts, zero downtime.
            </p>
            <div className="p-3 rounded bg-surface-100 border border-border font-mono text-[11px] text-gray-300">
              $ kubectl patch configmap otel-collector-config -n monitoring --type merge -p &apos;{JSON.stringify({ data: { "rollback": "true" } })}&apos;
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
