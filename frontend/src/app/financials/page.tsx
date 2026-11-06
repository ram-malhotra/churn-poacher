"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  DollarSign,
  TrendingDown,
  Clock,
  Layers,
  ArrowUpRight,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";
import { api } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatCurrency } from "@/lib/utils";

export default function FinancialAnalysisPage() {
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");

  const { data: metrics } = useQuery({
    queryKey: ["finopsMetrics"],
    queryFn: () => api.getFinOpsMetrics(),
  });

  const { data: pricing } = useQuery({
    queryKey: ["finopsPricing"],
    queryFn: () => api.getFinOpsPricing(),
  });

  const { data: companies } = useQuery({
    queryKey: ["acceptedCompanies"],
    queryFn: () => api.getCompanies({ qualification_status: "ACCEPTED", limit: 20 }),
  });

  // Pick first company by default if none selected
  const activeCompanyId = selectedCompanyId || (companies && companies.length > 0 ? companies[0].id : "");

  const { data: finReport, isLoading: loadingReport } = useQuery({
    queryKey: ["finopsReport", activeCompanyId],
    queryFn: () => api.getFinOpsAnalysis(activeCompanyId),
    enabled: Boolean(activeCompanyId),
  });

  const baseScenario = finReport?.scenarios?.BASE;

  return (
    <div className="flex-1 flex flex-col min-w-0">
      <Header
        title="Financial Delta Intelligence"
        description="Granular telemetry expenditure comparisons, TCO projections, and competitor licensing tax breakdowns."
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Metric Header Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-surface-100 border border-border">
            <span className="text-[10px] font-mono text-gray-400 uppercase block">Modeled Annual Savings Pool</span>
            <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">
              {metrics?.total_potential_annual_savings_usd ? formatCurrency(metrics.total_potential_annual_savings_usd) : "$0"}
            </div>
            <span className="text-xs text-gray-400 mt-1 block">Aggregated across active dossiers</span>
          </div>

          <div className="p-4 rounded-lg bg-surface-100 border border-border">
            <span className="text-[10px] font-mono text-gray-400 uppercase block">Average Payback Horizon</span>
            <div className="text-2xl font-bold text-brand-300 font-mono mt-1">
              {metrics?.average_payback_period_months ? `~${metrics.average_payback_period_months.toFixed(1)} months` : "N/A"}
            </div>
            <span className="text-xs text-gray-400 mt-1 block">Recoups all migration engineering hours</span>
          </div>

          <div className="p-4 rounded-lg bg-surface-100 border border-border">
            <span className="text-[10px] font-mono text-gray-400 uppercase block">Supported Alternative Backends</span>
            <div className="text-sm font-semibold text-white mt-1">
              SigNoz Cloud &bull; Grafana Cloud &bull; OSS ClickHouse
            </div>
            <span className="text-xs text-gray-400 mt-1 block">Zero host tax & pure volume pricing</span>
          </div>
        </div>

        {/* Company Selector */}
        {companies && companies.length > 0 && (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-100 border border-border">
            <span className="text-xs text-gray-400 font-medium">Select Target Organization:</span>
            <select
              value={activeCompanyId}
              onChange={(e) => setSelectedCompanyId(e.target.value)}
              className="bg-surface-50 border border-border text-xs text-white rounded px-3 py-1.5 focus:outline-none"
            >
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.estimated_size})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Financial Delta Matrix Card */}
        {baseScenario && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg bg-surface-100 border border-border">
                <span className="text-[10px] font-mono text-gray-400 uppercase block">Estimated Current Datadog</span>
                <span className="text-xl font-bold text-white font-mono mt-1 block">
                  {formatCurrency(baseScenario.current_datadog_annual)}/yr
                </span>
                <span className="text-[11px] text-gray-500 font-mono">
                  {formatCurrency(baseScenario.current_datadog_monthly)}/mo
                </span>
              </div>

              <div className="p-4 rounded-lg bg-surface-100 border border-border">
                <span className="text-[10px] font-mono text-gray-400 uppercase block">SigNoz Cloud Projection</span>
                <span className="text-xl font-bold text-cyan-400 font-mono mt-1 block">
                  {formatCurrency(baseScenario.signoz_cloud_annual)}/yr
                </span>
                <span className="text-[11px] text-gray-500 font-mono">
                  {formatCurrency(baseScenario.signoz_cloud_monthly)}/mo
                </span>
              </div>

              <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-500/30">
                <span className="text-[10px] font-mono text-emerald-400 uppercase block">Net Annual Delta</span>
                <span className="text-2xl font-bold text-emerald-400 font-mono mt-1 block">
                  {formatCurrency(baseScenario.signoz_cloud_annual_savings)}/yr
                </span>
                <span className="text-[11px] text-emerald-400 font-medium">
                  ~{baseScenario.signoz_cloud_savings_pct.toFixed(0)}% annual reduction
                </span>
              </div>

              <div className="p-4 rounded-lg bg-surface-100 border border-border">
                <span className="text-[10px] font-mono text-gray-400 uppercase block">3-Year Net Cumulative ROI</span>
                <span className="text-xl font-bold text-white font-mono mt-1 block">
                  {formatCurrency(baseScenario.three_year_tco_datadog - baseScenario.three_year_tco_signoz_cloud)}
                </span>
                <span className="text-[11px] text-gray-500">Includes migration cost</span>
              </div>
            </div>

            {/* Low / Base / High Comparison */}
            <Card>
              <CardHeader>
                <CardTitle>Telemetry Volume Sensitivity Matrix</CardTitle>
                <CardDescription>
                  Stress-tested scenarios modeling cost variance across telemetry scaling bounds.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-border text-[10px] font-mono text-gray-400 uppercase bg-surface-50/50">
                        <th className="py-2.5 px-3">Scenario</th>
                        <th className="py-2.5 px-3">Datadog Run-rate</th>
                        <th className="py-2.5 px-3">SigNoz Cloud</th>
                        <th className="py-2.5 px-3">Grafana Cloud</th>
                        <th className="py-2.5 px-3">Annual Savings</th>
                        <th className="py-2.5 px-3">3-Yr SigNoz TCO</th>
                        <th className="py-2.5 px-3">Payback</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50 font-mono">
                      {Object.entries(finReport?.scenarios || {}).map(([name, sc]: [string, any]) => (
                        <tr key={name} className="hover:bg-surface-50/50">
                          <td className="py-3 px-3 font-bold text-white">{name}</td>
                          <td className="py-3 px-3 text-rose-300">{formatCurrency(sc.current_datadog_annual)}</td>
                          <td className="py-3 px-3 text-cyan-300">{formatCurrency(sc.signoz_cloud_annual)}</td>
                          <td className="py-3 px-3 text-amber-300">{formatCurrency(sc.grafana_cloud_annual)}</td>
                          <td className="py-3 px-3 font-bold text-emerald-400">
                            {formatCurrency(sc.signoz_cloud_annual_savings)}
                          </td>
                          <td className="py-3 px-3 text-gray-300">{formatCurrency(sc.three_year_tco_signoz_cloud)}</td>
                          <td className="py-3 px-3 text-brand-300">~{sc.payback_period_months.toFixed(1)} mo</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Public Verified Pricing Catalog */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Verified Public Pricing Catalog</CardTitle>
                <CardDescription>
                  Unit prices, source documentation URLs, and verification dates across all 5 benchmarked platforms.
                </CardDescription>
              </div>
              <Badge variant="success">PUBLICALLY VERIFIED</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-border text-[10px] font-mono text-gray-400 uppercase bg-surface-50/50">
                    <th className="py-2.5 px-3">Vendor</th>
                    <th className="py-2.5 px-3">Product Tier</th>
                    <th className="py-2.5 px-3">Unit Price</th>
                    <th className="py-2.5 px-3">Billing Metric</th>
                    <th className="py-2.5 px-3">Verified Date</th>
                    <th className="py-2.5 px-3 text-right">Official Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {(pricing || []).map((p, idx) => (
                    <tr key={idx} className="hover:bg-surface-50/50">
                      <td className="py-2.5 px-3 font-semibold text-white">{p.vendor}</td>
                      <td className="py-2.5 px-3 text-gray-300">{p.product}</td>
                      <td className="py-2.5 px-3 font-mono font-medium text-emerald-400">
                        ${p.unit_price} / {p.billing_unit}
                      </td>
                      <td className="py-2.5 px-3 text-gray-400 font-mono text-[11px]">{p.billing_unit}</td>
                      <td className="py-2.5 px-3 text-gray-500 font-mono text-[11px]">{p.last_verified_date}</td>
                      <td className="py-2.5 px-3 text-right">
                        <a
                          href={p.pricing_source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-brand-400 hover:underline flex items-center justify-end gap-1 text-[11px] font-mono"
                        >
                          Pricing Page <ExternalLink className="w-3 h-3" />
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
