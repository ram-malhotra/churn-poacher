"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Radio,
  Filter,
  ArrowUpRight,
  Play,
  Search,
  ExternalLink,
  Flame,
  CheckCircle,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { formatDate, cleanSignalText } from "@/lib/utils";

export default function SignalMonitorPage() {
  const queryClient = useQueryClient();
  const [sourceFilter, setSourceFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [minUrgency, setMinUrgency] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeSignalId, setActiveSignalId] = useState<string | null>(null);

  const { data: signals, isLoading, refetch } = useQuery({
    queryKey: ["signals", sourceFilter, categoryFilter, minUrgency],
    queryFn: () =>
      api.getSignals({
        source: sourceFilter || undefined,
        complaint_category: categoryFilter || undefined,
        min_urgency: minUrgency ? parseFloat(minUrgency) : undefined,
        limit: 100,
      }),
  });

  const runMutation = useMutation({
    mutationFn: (signalId: string) =>
      api.runWorkflow({
        signal_id: signalId,
        target_challenger: "SigNoz Cloud",
        timeout_seconds: 45,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signals"] });
      queryClient.invalidateQueries({ queryKey: ["recentWorkflows"] });
    },
  });

  const filteredSignals = (signals || []).filter((s) => {
    if (!searchQuery) return true;
    const cleanContent = cleanSignalText(s.raw_content).toLowerCase();
    const query = searchQuery.toLowerCase();
    return (
      cleanContent.includes(query) ||
      s.source.toLowerCase().includes(query) ||
      s.complaint_category.toLowerCase().includes(query) ||
      (s.author_handle && s.author_handle.toLowerCase().includes(query))
    );
  });

  return (
    <div className="flex-1 flex flex-col min-w-0">
      <Header
        title="Signal Monitor"
        description="Real-time multi-source listening stream tracking competitor outages, price spikes, and customer dissatisfaction."
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Filter & Search Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-lg bg-surface-100 border border-border">
          <div className="flex items-center gap-3 flex-1 min-w-[240px]">
            <Search className="w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search content, keywords, handles..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent border-none text-xs text-white placeholder-gray-500 focus:outline-none w-full"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Source selector */}
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="bg-surface-50 border border-border text-xs text-gray-300 rounded px-2.5 py-1.5 focus:outline-none"
            >
              <option value="">All Sources</option>
              <option value="HACKER_NEWS">Hacker News</option>
              <option value="REDDIT">Reddit</option>
              <option value="DATADOG_STATUS">Datadog Status</option>
              <option value="SYNTHETIC">Synthetic Demo</option>
            </select>

            {/* Category selector */}
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-surface-50 border border-border text-xs text-gray-300 rounded px-2.5 py-1.5 focus:outline-none"
            >
              <option value="">All Categories</option>
              <option value="PRICING_SHOCK">Pricing Shock</option>
              <option value="OUTAGE">Outage</option>
              <option value="RELIABILITY">Reliability</option>
              <option value="MIGRATION_INTENT">Migration Intent</option>
              <option value="GENERAL_DISCUSSION">General</option>
            </select>

            {/* Urgency selector */}
            <select
              value={minUrgency}
              onChange={(e) => setMinUrgency(e.target.value)}
              className="bg-surface-50 border border-border text-xs text-gray-300 rounded px-2.5 py-1.5 focus:outline-none"
            >
              <option value="">Any Urgency</option>
              <option value="0.75">High Urgency (&ge; 7.5)</option>
              <option value="0.5">Medium Urgency (&ge; 5.0)</option>
            </select>

            <button
              onClick={() => refetch()}
              className="p-1.5 rounded bg-surface-50 hover:bg-surface-200 border border-border text-gray-400 hover:text-white transition"
              title="Refresh feeds"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Signals Feed List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-gray-400 px-1">
            <span>Showing {filteredSignals.length} competitive distress signals</span>
            <span className="font-mono text-[11px]">Stream: Datadog Watchlist</span>
          </div>

          {isLoading ? (
            <div className="p-12 text-center text-xs text-gray-500">Connecting to intelligence stream...</div>
          ) : filteredSignals.length > 0 ? (
            <div className="space-y-3">
              {filteredSignals.map((signal) => {
                const isExecuting = runMutation.isPending && activeSignalId === signal.id;
                return (
                  <Card key={signal.id} className="hover:border-border/80 transition-all">
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-3 border-b border-border/50">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="purple">{signal.source}</Badge>
                        <Badge
                          variant={
                            signal.complaint_category === "PRICING_SHOCK"
                              ? "danger"
                              : signal.complaint_category === "OUTAGE"
                              ? "warning"
                              : "default"
                          }
                        >
                          {signal.complaint_category}
                        </Badge>
                        {signal.is_synthetic && <Badge variant="synthetic">SYNTHETIC</Badge>}
                        <StatusBadge status={signal.status} />
                      </div>

                      <div className="flex items-center gap-4 text-xs font-mono text-gray-400">
                        <span className="flex items-center gap-1 text-rose-400 font-semibold">
                          <Flame className="w-3.5 h-3.5" /> {(signal.urgency_score * 10).toFixed(1)}/10
                        </span>
                        <span>{formatDate(signal.created_at)}</span>
                      </div>
                    </div>

                    <div className="py-3">
                      <p className="text-xs text-gray-200 leading-relaxed font-sans select-text">
                        &ldquo;{cleanSignalText(signal.raw_content)}&rdquo;
                      </p>
                    </div>

                    <div className="pt-2 flex flex-wrap items-center justify-between gap-3 text-xs border-t border-border/40">
                      <div className="flex items-center gap-3 text-gray-400 text-[11px]">
                        {signal.author_handle && <span>Author: @{signal.author_handle}</span>}
                        <a
                          href={signal.original_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-brand-400 hover:underline flex items-center gap-1 font-medium"
                        >
                          View Source URL <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>

                      <button
                        onClick={() => {
                          setActiveSignalId(signal.id);
                          runMutation.mutate(signal.id);
                        }}
                        disabled={isExecuting}
                        className="flex items-center gap-1.5 px-3 py-1 rounded bg-surface-50 hover:bg-brand-600 border border-border hover:border-brand-500 text-gray-300 hover:text-white transition text-[11px] font-medium cursor-pointer"
                      >
                        {isExecuting ? (
                          <RefreshCw className="w-3 h-3 animate-spin text-brand-400" />
                        ) : (
                          <Play className="w-3 h-3 fill-current text-emerald-400" />
                        )}
                        <span>{isExecuting ? "Poaching Account..." : "Investigate & Poach"}</span>
                      </button>
                    </div>
                  </Card>
                );
              })}
            </div>
          ) : (
            <div className="p-12 text-center text-xs text-gray-500 bg-surface-100 rounded-lg border border-border">
              No distress signals match your filter criteria.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
