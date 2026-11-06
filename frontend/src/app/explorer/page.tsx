"use client";

import React, { useState, useEffect } from "react";
import {
  Compass,
  Search,
  Building2,
  User,
  Zap,
  ShieldCheck,
  Coins,
  History,
  Download,
  Copy,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Cpu,
  DollarSign,
  Briefcase,
  Users,
  Award,
  Globe,
  ArrowRight,
  Layers,
  PlusCircle,
  AlertCircle,
  X,
  Sparkles,
  Info,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  CrustdataCreditsInfo,
  CrustdataBudgetStatus,
  EntitySearchResponse,
  EntityCandidate,
  CompanyIntelligenceProfile,
  PersonIntelligenceProfile,
  CrustdataEntityType,
  CrustdataEnrichmentLevel,
  DeepEnrichmentCostEstimate,
} from "@/types";
import { formatCurrency } from "@/lib/utils";

interface InlineCreditError {
  type: "INSUFFICIENT_CREDITS" | "BUDGET_EXHAUSTED" | "GENERAL_ERROR";
  title: string;
  message: string;
  currentBalance?: number;
  requiredCredits?: number;
  safetyThreshold?: number;
}

export default function CrustdataExplorerPage() {
  const [query, setQuery] = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState<CrustdataEntityType>("UNKNOWN");
  const [mode, setMode] = useState<"LIVE" | "DEMO">("LIVE");
  const [selectedCandidate, setSelectedCandidate] = useState<EntityCandidate | null>(null);
  const [budget, setBudget] = useState<CrustdataBudgetStatus | null>(null);
  const [credits, setCredits] = useState<CrustdataCreditsInfo | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isEnriching, setIsEnriching] = useState(false);
  const [searchResults, setSearchResults] = useState<EntitySearchResponse | null>(null);
  const [activeProfile, setActiveProfile] = useState<CompanyIntelligenceProfile | PersonIntelligenceProfile | null>(null);
  const [activeTab, setActiveTab] = useState<string>("technographics");
  const [searchHistory, setSearchHistory] = useState<any[]>([]);
  const [deepCostEstimate, setDeepCostEstimate] = useState<DeepEnrichmentCostEstimate | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showBudgetModal, setShowBudgetModal] = useState(false);
  const [budgetIncreaseAmount, setBudgetIncreaseAmount] = useState<number>(500);
  const [budgetIncreaseReason, setBudgetIncreaseReason] = useState<string>("User-approved budget increase");
  const [isIncreasingBudget, setIsIncreasingBudget] = useState(false);
  const [exportNotice, setExportNotice] = useState<string | null>(null);
  const [creditError, setCreditError] = useState<InlineCreditError | null>(null);

  useEffect(() => {
    loadBudgetAndCredits();
    loadSearchHistory();
  }, []);

  const loadBudgetAndCredits = async () => {
    try {
      const budgetData = await api.getCrustdataBudget();
      setBudget(budgetData);
      if (budgetData.account_credits) {
        setCredits(budgetData.account_credits);
      } else {
        const creditData = await api.getCrustdataCredits();
        setCredits(creditData);
      }
    } catch (err) {
      console.error("Failed to load budget/credits:", err);
    }
  };

  const loadSearchHistory = async () => {
    try {
      const hist = await api.getCrustdataSearchHistory(10);
      setSearchHistory(hist);
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  };

  const parseAndHandleError = (err: any) => {
    const errMsg = typeof err?.message === "string" ? err.message : JSON.stringify(err);
    const errDetail = err?.detail || {};

    // Check for budget exhaustion
    if (
      err?.status === 402 &&
      (errMsg.includes("application budget exhausted") || errDetail?.error_type === "BUDGET_EXHAUSTED")
    ) {
      setCreditError({
        type: "BUDGET_EXHAUSTED",
        title: "Application Spending Budget Exhausted",
        message:
          typeof errDetail?.message === "string"
            ? errDetail.message
            : `The application budget of ${budget?.total_budget?.toLocaleString() || 1200} credits has been reached. Please approve a budget increase to resume paid operations.`,
      });
      setShowBudgetModal(true);
      return;
    }

    // Check for insufficient account credits
    if (
      errMsg.includes("Insufficient Crustdata credits") ||
      errMsg.includes("safety threshold") ||
      errMsg.includes("balance")
    ) {
      const balMatch = errMsg.match(/current balance ([\d.]+)/);
      const reqMatch = errMsg.match(/required ([\d.]+)/);
      const floorMatch = errMsg.match(/minimum safety threshold ([\d.]+)/);

      setCreditError({
        type: "INSUFFICIENT_CREDITS",
        title: "Insufficient Crustdata Account Credits",
        message:
          "The upstream Crustdata account balance is below the minimum safety threshold. Paid operations are paused to protect your account.",
        currentBalance: balMatch ? parseFloat(balMatch[1]) : (credits?.remaining_credits ?? 0.0),
        requiredCredits: reqMatch ? parseFloat(reqMatch[1]) : 0.5,
        safetyThreshold: floorMatch ? parseFloat(floorMatch[1]) : 5.0,
      });
      return;
    }

    // General error
    setCreditError({
      type: "GENERAL_ERROR",
      title: "Crustdata Operation Failed",
      message: errMsg,
    });
  };

  const handleSearch = async (e?: React.FormEvent, overrideQuery?: string) => {
    if (e) e.preventDefault();
    const queryToSearch = overrideQuery || query;
    if (!queryToSearch.trim()) return;

    if (budget?.is_exhausted) {
      setShowBudgetModal(true);
      return;
    }

    setIsSearching(true);
    setSearchResults(null);
    setActiveProfile(null);
    setSelectedCandidate(null);
    setDeepCostEstimate(null);
    setCreditError(null);

    try {
      const filter = entityTypeFilter === "UNKNOWN" ? undefined : entityTypeFilter;
      const res = await api.searchCrustdata({
        query: queryToSearch.trim(),
        entity_type: filter,
        limit: 6,
        mode,
      });
      setSearchResults(res);
      await loadBudgetAndCredits();
      await loadSearchHistory();

      // If single unambiguous candidate returned, auto-enrich standard profile
      if (res.candidates.length === 1 && !res.is_ambiguous) {
        const singleCand = res.candidates[0];
        handleEnrichCandidate(singleCand, "LEVEL_2_STANDARD");
      }
    } catch (err: any) {
      parseAndHandleError(err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleEnrichCandidate = async (
    candidate: EntityCandidate,
    level: CrustdataEnrichmentLevel = "LEVEL_2_STANDARD",
    confirmationConfirmed = false
  ) => {
    if (budget?.is_exhausted) {
      setShowBudgetModal(true);
      return;
    }

    setSelectedCandidate(candidate);
    setIsEnriching(true);
    setDeepCostEstimate(null);
    setCreditError(null);

    try {
      const targetId = candidate.primary_domain || candidate.profile_url || candidate.name;
      const res = await api.enrichCrustdata({
        identifier: targetId,
        entity_type: candidate.entity_type,
        level,
        confirmation_confirmed: confirmationConfirmed,
        mode,
      });

      if (res.estimated_credits && !confirmationConfirmed) {
        // Deep enrichment requires explicit confirmation
        setDeepCostEstimate(res as DeepEnrichmentCostEstimate);
        setShowConfirmModal(true);
      } else {
        setActiveProfile(res);
        if (candidate.entity_type === "COMPANY") {
          setActiveTab("technographics");
        } else {
          setActiveTab("profile");
        }
        setShowConfirmModal(false);
      }
      await loadBudgetAndCredits();
    } catch (err: any) {
      parseAndHandleError(err);
    } finally {
      setIsEnriching(false);
    }
  };

  const handleConfirmDeepEnrichment = () => {
    if (!deepCostEstimate) return;
    const dummyCand: EntityCandidate = {
      candidate_id: deepCostEstimate.target_identifier,
      entity_type: deepCostEstimate.entity_type,
      name: deepCostEstimate.entity_name,
      primary_domain: deepCostEstimate.target_identifier,
      confidence_score: 1.0,
      is_ambiguous: false,
      is_mock: false,
    };
    handleEnrichCandidate(dummyCand, "LEVEL_3_DEEP", true);
  };

  const handleApproveBudgetIncrease = async () => {
    if (budgetIncreaseAmount <= 0) return;
    setIsIncreasingBudget(true);
    try {
      const updated = await api.increaseCrustdataBudget({
        amount: budgetIncreaseAmount,
        reason: budgetIncreaseReason,
        approved_by: "User",
      });
      setBudget(updated);
      setShowBudgetModal(false);
      setCreditError(null);
      setExportNotice(`Application budget successfully increased by ${budgetIncreaseAmount} credits! Paid operations resumed.`);
      setTimeout(() => setExportNotice(null), 4000);
    } catch (err: any) {
      alert(`Failed to increase budget: ${err.message || err}`);
    } finally {
      setIsIncreasingBudget(false);
    }
  };

  const handleExport = async (format: "markdown" | "json") => {
    if (!activeProfile) return;
    try {
      const res = await api.exportCrustdataReport(activeProfile.entity_id, format);
      if (format === "markdown") {
        navigator.clipboard.writeText(res.content);
        setExportNotice("Intelligence Report copied to clipboard as Markdown!");
      } else {
        const blob = new Blob([JSON.stringify(res, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `crustdata_${activeProfile.entity_id}.json`;
        a.click();
        setExportNotice("JSON file downloaded!");
      }
      setTimeout(() => setExportNotice(null), 3500);
    } catch (err: any) {
      alert(`Export failed: ${err.message || err}`);
    }
  };

  const NATURAL_LANGUAGE_EXAMPLES = [
    "Find SaaS companies in the US with 200–1000 employees",
    "Find CTOs at companies using Datadog",
    "Find companies using Datadog and AWS",
    "Find VP Engineering at NVIDIA",
    "Find companies hiring observability engineers",
    "Find fintech companies with large engineering teams",
  ];

  const quickSearch = (term: string) => {
    setQuery(term);
    handleSearch(undefined, term);
  };

  const isCompany = activeProfile && "technographics" in activeProfile;
  const companyProfile = isCompany ? (activeProfile as CompanyIntelligenceProfile) : null;
  const personProfile = !isCompany ? (activeProfile as PersonIntelligenceProfile) : null;

  const hasIdentityConflict = Boolean(
    selectedCandidate &&
      activeProfile &&
      ((selectedCandidate.entity_type === "PERSON" &&
        selectedCandidate.company_name &&
        personProfile?.current_company &&
        selectedCandidate.company_name.toLowerCase().trim() !==
          personProfile.current_company.toLowerCase().trim()) ||
        (selectedCandidate.entity_type === "COMPANY" &&
          selectedCandidate.name &&
          companyProfile?.name &&
          selectedCandidate.name.toLowerCase().trim() !== companyProfile.name.toLowerCase().trim()))
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <Compass className="h-6 w-6 text-primary" />
              Crustdata Intelligence Explorer
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full font-mono font-medium bg-primary/20 text-primary border border-primary/30">
              AI EXTRACTION
            </span>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-semibold border ${
                mode === "LIVE"
                  ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                  : "bg-warning/20 text-warning border-warning/40"
              }`}
            >
              {mode === "LIVE" ? "LIVE DATASET (v2025-11-01)" : "OFFLINE DEMO MODE"}
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Universal B2B entity search, verified technographics, decision makers, and funding telemetry.
          </p>
        </div>

        {/* Mode Selector & Account Balance */}
        <div className="flex flex-col sm:items-end gap-2">
          <div className="flex items-center gap-1 bg-surface-200 border border-border p-1 rounded-lg">
            <button
              onClick={() => setMode("LIVE")}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition ${
                mode === "LIVE"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Live API
            </button>
            <button
              onClick={() => setMode("DEMO")}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition ${
                mode === "DEMO"
                  ? "bg-warning text-warning-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Demo Mode
            </button>
          </div>
          <div className="text-xs text-muted-foreground font-mono text-right hidden sm:block">
            <div>Crustdata API Balance: <span className="font-bold text-foreground">{credits ? credits.remaining_credits.toFixed(1) : "—"} cr</span></div>
            <div className="text-[10px] text-muted-foreground/80">Safety Floor: 5.0 cr</div>
          </div>
        </div>
      </div>

      {/* Crustdata Usage Card */}
      <div className="bg-surface-100 border border-border rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <Coins className="h-4 w-4 text-warning" />
              <h2 className="text-sm font-bold uppercase tracking-wider text-foreground font-mono">Crustdata Usage</h2>
              <span
                className={`text-[11px] px-2.5 py-0.5 rounded-full font-mono font-semibold border ${
                  budget?.status === "Active"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                    : budget?.status === "Near Limit"
                    ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                    : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                }`}
              >
                Status: {budget?.status || "Active"}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Application-level spending ceiling (1,200 cr initial). Actual account balance is verified independently.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            <button
              onClick={() => setShowBudgetModal(true)}
              className="px-3 py-1.5 bg-primary/20 hover:bg-primary/30 text-primary border border-primary/40 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <PlusCircle className="h-3.5 w-3.5" />
              Increase Budget
            </button>
            <button
              onClick={loadBudgetAndCredits}
              className="p-1.5 hover:bg-surface-200 rounded text-muted-foreground hover:text-foreground border border-border"
              title="Refresh Budget"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Usage Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono pt-1">
          <div className="bg-surface-200/60 border border-border/80 p-2.5 rounded-lg">
            <span className="text-[10px] text-muted-foreground uppercase block">Budget</span>
            <span className="text-sm font-bold text-foreground">
              {budget ? budget.total_budget.toLocaleString() : "1,200"} credits
            </span>
          </div>

          <div className="bg-surface-200/60 border border-border/80 p-2.5 rounded-lg">
            <span className="text-[10px] text-muted-foreground uppercase block">Used</span>
            <span className="text-sm font-bold text-foreground">
              {budget ? budget.used_credits.toFixed(1) : "0.0"} credits
            </span>
            <span className="text-[10px] text-muted-foreground block mt-0.5">
              {budget ? budget.usage_percentage.toFixed(1) : "0.0"}% of budget
            </span>
          </div>

          <div className="bg-surface-200/60 border border-border/80 p-2.5 rounded-lg">
            <span className="text-[10px] text-muted-foreground uppercase block">Remaining</span>
            <span
              className={`text-sm font-bold ${
                budget && budget.remaining_credits <= 0
                  ? "text-rose-400"
                  : budget && budget.remaining_credits < 240
                  ? "text-amber-400"
                  : "text-emerald-400"
              }`}
            >
              {budget ? budget.remaining_credits.toFixed(1) : "1,200.0"} credits
            </span>
          </div>

          <div className="bg-surface-200/60 border border-border/80 p-2.5 rounded-lg">
            <span className="text-[10px] text-muted-foreground uppercase block">Account Balance</span>
            <span className="text-sm font-bold text-foreground">
              {credits ? credits.remaining_credits.toFixed(1) : "—"} credits
            </span>
            <span className="text-[10px] text-muted-foreground block mt-0.5">
              API balance
            </span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="pt-1">
          <div className="w-full bg-surface-200 h-2 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                budget?.status === "Exhausted"
                  ? "bg-rose-500"
                  : budget?.status === "Near Limit"
                  ? "bg-amber-500"
                  : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(100, budget?.usage_percentage || 0)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Clear Budget-Exhausted Notification */}
      {budget?.is_exhausted && (
        <div className="bg-rose-950/30 border border-rose-500/40 p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-rose-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-rose-300 text-sm">Crustdata Application Spending Budget Exhausted</h4>
              <p className="text-xs text-rose-200/80 mt-0.5">
                The {budget?.total_budget.toLocaleString() || "1,200"}-credit application spending limit has been reached ({budget?.used_credits.toFixed(1)} credits used).
                New paid Crustdata API requests are paused to prevent unexpected spend.
              </p>
              <p className="text-xs font-medium text-rose-300 mt-1">
                Would you like to increase your application budget to resume paid operations?
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowBudgetModal(true)}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer self-start sm:self-center"
          >
            Increase Budget
          </button>
        </div>
      )}

      {/* Inline Credit or Account Error Notification */}
      {creditError && (
        <div
          className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs ${
            creditError.type === "INSUFFICIENT_CREDITS"
              ? "bg-amber-950/30 border-amber-500/40 text-amber-200"
              : creditError.type === "BUDGET_EXHAUSTED"
              ? "bg-rose-950/30 border-rose-500/40 text-rose-200"
              : "bg-surface-200/80 border-border text-foreground"
          }`}
        >
          <div className="flex items-start gap-3">
            {creditError.type === "INSUFFICIENT_CREDITS" ? (
              <Coins className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            )}
            <div className="space-y-1">
              <h4 className="font-bold text-sm">
                {creditError.title}
              </h4>
              <p className="opacity-90">{creditError.message}</p>
              {creditError.type === "INSUFFICIENT_CREDITS" && (
                <div className="flex flex-wrap items-center gap-4 pt-1 font-mono text-[11px]">
                  <span>
                    Current Account Balance:{" "}
                    <strong>{creditError.currentBalance !== undefined ? creditError.currentBalance.toFixed(1) : "0.0"} cr</strong>
                  </span>
                  <span>
                    Safety Floor:{" "}
                    <strong>{creditError.safetyThreshold !== undefined ? creditError.safetyThreshold.toFixed(1) : "5.0"} cr</strong>
                  </span>
                  <span>
                    Required for Operation:{" "}
                    <strong>{creditError.requiredCredits !== undefined ? creditError.requiredCredits.toFixed(1) : "0.5"} cr</strong>
                  </span>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-center">
            {creditError.type === "BUDGET_EXHAUSTED" && (
              <button
                onClick={() => setShowBudgetModal(true)}
                className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-semibold text-xs transition"
              >
                Increase Budget
              </button>
            )}
            <button
              onClick={() => setCreditError(null)}
              className="p-1 hover:bg-white/10 rounded text-muted-foreground hover:text-foreground"
              title="Dismiss"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Omnibar Search Form with Estimated Cost Indicator */}
      <div className="bg-surface-100 border border-border p-4 rounded-xl shadow-sm space-y-3">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter company name, person name, domain (spacex.com), or LinkedIn profile URL..."
              className="w-full pl-9 pr-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <select
            value={entityTypeFilter}
            onChange={(e) => setEntityTypeFilter(e.target.value as CrustdataEntityType)}
            className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="UNKNOWN">Auto-Detect Entity</option>
            <option value="COMPANY">Company Only</option>
            <option value="PERSON">Person Only</option>
          </select>

          <button
            type="submit"
            disabled={isSearching || !query.trim()}
            className={`btn flex items-center gap-2 whitespace-nowrap ${
              budget?.is_exhausted
                ? "bg-rose-600/30 text-rose-300 border border-rose-500/40 hover:bg-rose-600/40"
                : "btn-primary"
            }`}
            title="Estimated Cost: ~0.5 credits"
          >
            {isSearching ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            {budget?.is_exhausted ? "Extract Intelligence (Budget Exhausted)" : "Extract Intelligence (~0.5 cr)"}
          </button>
        </form>

        {/* Natural Language Example Queries */}
        <div className="space-y-1.5 pt-1">
          <div className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            <span>Natural-Language Intelligence Queries (Live Dataset):</span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {NATURAL_LANGUAGE_EXAMPLES.map((term) => (
              <button
                key={term}
                onClick={() => quickSearch(term)}
                className="px-2.5 py-1 bg-surface-200 hover:bg-surface-300 text-foreground text-xs rounded-md border border-border transition-colors font-sans text-left"
              >
                {term}
              </button>
            ))}
          </div>
        </div>

        {/* Query Interpretation Breakdown */}
        {searchResults?.interpretation && (
          <div className="bg-primary/5 border border-primary/20 rounded-lg p-3 text-xs flex flex-wrap items-center gap-2.5">
            <span className="font-semibold text-primary flex items-center gap-1">
              <Sparkles className="h-3.5 w-3.5" />
              Interpreted:
            </span>
            <span className="bg-surface-200 px-2 py-0.5 rounded font-mono font-medium">
              Target: {searchResults.interpretation.target_entity}
            </span>
            {searchResults.interpretation.country && (
              <span className="bg-surface-200 px-2 py-0.5 rounded font-mono">
                Country: {searchResults.interpretation.country}
              </span>
            )}
            {(searchResults.interpretation.headcount_min || searchResults.interpretation.headcount_max) && (
              <span className="bg-surface-200 px-2 py-0.5 rounded font-mono">
                Employees: {searchResults.interpretation.headcount_min || 0} - {searchResults.interpretation.headcount_max || "Any"}
              </span>
            )}
            {searchResults.interpretation.job_title && (
              <span className="bg-surface-200 px-2 py-0.5 rounded font-mono">
                Title: {searchResults.interpretation.job_title}
              </span>
            )}
            {searchResults.interpretation.technologies?.length > 0 && (
              <span className="bg-surface-200 px-2 py-0.5 rounded font-mono text-primary font-medium">
                Stack: {searchResults.interpretation.technologies.join(", ")}
              </span>
            )}
            <span className="text-[11px] text-muted-foreground ml-auto font-mono">
              Endpoint: <code className="text-foreground">{searchResults.interpretation.crustdata_endpoint}</code>
            </span>
          </div>
        )}

        {/* Buying Intent Distinction Warning */}
        {searchResults?.buying_intent_distinction && (
          <div className="text-[11px] text-muted-foreground flex items-center gap-1.5 px-1 bg-surface-200/50 p-2 rounded border border-border/50">
            <Info className="h-3.5 w-3.5 text-primary shrink-0" />
            <span>{searchResults.buying_intent_distinction}</span>
          </div>
        )}
      </div>

      {/* Search Candidates (Level 1 Candidate Selection) */}
      {searchResults && searchResults.candidates.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Users className="h-4 w-4" />
              Candidate Matches ({searchResults.candidates.length})
            </h2>
            {searchResults.is_ambiguous && (
              <span className="text-xs px-2 py-0.5 rounded bg-warning/20 text-warning border border-warning/30 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Multiple candidates detected — select to enrich
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {searchResults.candidates.map((cand) => (
              <div
                key={cand.candidate_id}
                className="bg-surface-100 border border-border hover:border-primary/50 p-4 rounded-lg flex flex-col justify-between gap-3 transition-colors"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs px-2 py-0.5 rounded font-mono font-medium bg-surface-200 text-muted-foreground flex items-center gap-1">
                        {cand.entity_type === "COMPANY" ? <Building2 className="h-3 w-3" /> : <User className="h-3 w-3" />}
                        {cand.entity_type}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold ${
                          cand.data_origin === "LIVE"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                            : cand.data_origin === "CACHED"
                            ? "bg-blue-500/10 text-blue-400 border border-blue-500/30"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                        }`}
                      >
                        {cand.data_origin || (cand.is_mock ? "DEMO" : "LIVE")}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                          cand.verification_status === "VERIFIED"
                            ? "bg-emerald-500/10 text-emerald-300"
                            : "bg-amber-500/10 text-amber-300"
                        }`}
                      >
                        {cand.verification_status || "VERIFIED"}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground font-mono">
                      {(cand.confidence_score * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <h3 className="font-semibold text-foreground text-base">{cand.name}</h3>
                  {cand.current_title && (
                    <p className="text-xs font-medium text-primary">
                      {cand.current_title} {cand.company_name ? `@ ${cand.company_name}` : ""}
                    </p>
                  )}
                  {cand.primary_domain && (
                    <p className="text-xs text-muted-foreground font-mono">{cand.primary_domain}</p>
                  )}
                  {cand.headline && <p className="text-xs text-muted-foreground line-clamp-2">{cand.headline}</p>}
                  <div className="text-[10px] text-muted-foreground font-mono pt-1">
                    Intent: <span className="text-foreground">Intelligence Only (No Signal)</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2 border-t border-border">
                  <button
                    onClick={() => handleEnrichCandidate(cand, "LEVEL_2_STANDARD")}
                    disabled={isEnriching}
                    className="flex-1 btn btn-secondary text-xs py-1.5 flex items-center justify-center gap-1"
                    title="Estimated Cost: ~2.0 credits"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                    Standard Enrich (~2.0 cr)
                  </button>
                  <button
                    onClick={() => handleEnrichCandidate(cand, "LEVEL_3_DEEP")}
                    disabled={isEnriching}
                    className="btn btn-outline text-xs py-1.5 px-2.5 text-warning hover:bg-warning/10"
                    title="Deep Real-Time Scrape (~15.0 credits)"
                  >
                    <Zap className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Export Feedback Banner */}
      {exportNotice && (
        <div className="bg-success/20 border border-success/40 text-success px-4 py-2.5 rounded-lg text-sm flex items-center justify-between">
          <span>{exportNotice}</span>
          <button onClick={() => setExportNotice(null)} className="text-xs underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Identity Conflict Alert Banner */}
      {hasIdentityConflict && (
        <div className="bg-rose-500/10 border border-rose-500/30 text-rose-300 p-4 rounded-xl flex items-start gap-3 shadow-sm">
          <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1.5 flex-1">
            <h4 className="font-bold text-sm text-rose-200 flex items-center gap-2">
              Identity Conflict Detected
              <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-mono">
                DATA INTEGRITY ALERT
              </span>
            </h4>
            <p className="text-xs text-rose-300/90 leading-relaxed">
              Selected candidate was <strong>{selectedCandidate?.name}</strong> at <strong>{selectedCandidate?.company_name || selectedCandidate?.primary_domain}</strong>,
              but the loaded detailed profile belongs to <strong>{personProfile?.full_name || companyProfile?.name}</strong> at <strong>{personProfile?.current_company || companyProfile?.primary_domain}</strong>.
              Dossier exports and automated outreach generation are blocked until identity is resolved.
            </p>
            <div className="pt-2 flex items-center gap-2">
              <button
                onClick={() => {
                  setActiveProfile(null);
                  setSelectedCandidate(null);
                }}
                className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold transition"
              >
                Discard Conflicted Profile
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Profile Explorer Display */}
      {activeProfile && (
        <div className="bg-surface-100 border border-border rounded-xl shadow-sm overflow-hidden space-y-6 p-6">
          {/* Entity Profile Header */}
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 border-b border-border pb-6">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-2xl font-bold tracking-tight text-foreground">
                  {companyProfile ? companyProfile.name : personProfile?.full_name}
                </h2>
                <span className="text-xs px-2.5 py-0.5 rounded font-mono font-medium bg-primary/20 text-primary border border-primary/30">
                  {companyProfile ? "COMPANY" : "PERSON"}
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded font-mono font-medium bg-surface-200 text-muted-foreground border border-border">
                  {activeProfile.enrichment_level}
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded font-mono font-medium bg-success/20 text-success border border-success/30">
                  {activeProfile.data_freshness}
                </span>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded font-mono font-semibold border ${
                    activeProfile.data_origin === "LIVE"
                      ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                      : activeProfile.data_origin === "CACHED"
                      ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                      : "bg-amber-500/20 text-amber-400 border-amber-500/30"
                  }`}
                >
                  {activeProfile.data_origin || (activeProfile.is_mock ? "DEMO" : "LIVE")}
                </span>
              </div>
              <p className="text-sm text-muted-foreground max-w-3xl">
                {companyProfile?.description || personProfile?.headline || personProfile?.summary_bio || "No summary profile available."}
              </p>
              {companyProfile?.primary_domain && (
                <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Globe className="h-3.5 w-3.5 text-primary" /> {companyProfile.primary_domain}
                  </span>
                  {companyProfile.industry && <span>Industry: {companyProfile.industry}</span>}
                  {companyProfile.headcount && <span>Headcount: {companyProfile.headcount}</span>}
                  {companyProfile.headquarters && <span>HQ: {companyProfile.headquarters}</span>}
                </div>
              )}
              {personProfile && (
                <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground">
                  {personProfile.current_title && <span>{personProfile.current_title}</span>}
                  {personProfile.current_company && <span>@ {personProfile.current_company}</span>}
                  {personProfile.location && <span>{personProfile.location}</span>}
                  {personProfile.is_decision_maker && (
                    <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      DECISION MAKER ({(personProfile.decision_maker_score * 100).toFixed(0)}%)
                    </span>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 self-start md:self-auto">
              <button
                onClick={() => handleExport("markdown")}
                disabled={hasIdentityConflict}
                className={`btn btn-secondary text-xs flex items-center gap-1.5 ${
                  hasIdentityConflict ? "opacity-50 cursor-not-allowed" : ""
                }`}
                title={hasIdentityConflict ? "Export disabled due to identity conflict" : "Copy Markdown Report to Clipboard"}
              >
                <Copy className="h-3.5 w-3.5" />
                Copy MD
              </button>
              <button
                onClick={() => handleExport("json")}
                disabled={hasIdentityConflict}
                className={`btn btn-outline text-xs flex items-center gap-1.5 ${
                  hasIdentityConflict ? "opacity-50 cursor-not-allowed" : ""
                }`}
                title={hasIdentityConflict ? "Export disabled due to identity conflict" : "Download JSON Profile"}
              >
                <Download className="h-3.5 w-3.5" />
                Export JSON
              </button>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b border-border text-sm font-medium">
            {isCompany ? (
              <>
                <button
                  onClick={() => setActiveTab("technographics")}
                  className={`pb-3 px-4 flex items-center gap-2 border-b-2 transition-colors ${
                    activeTab === "technographics"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Cpu className="h-4 w-4" />
                  Technographics ({companyProfile?.technographics.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab("funding")}
                  className={`pb-3 px-4 flex items-center gap-2 border-b-2 transition-colors ${
                    activeTab === "funding"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <DollarSign className="h-4 w-4" />
                  Funding & Investors ({companyProfile?.funding_rounds.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab("jobs")}
                  className={`pb-3 px-4 flex items-center gap-2 border-b-2 transition-colors ${
                    activeTab === "jobs"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Briefcase className="h-4 w-4" />
                  Jobs & Tech ({companyProfile?.active_jobs.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab("evidence")}
                  className={`pb-3 px-4 flex items-center gap-2 border-b-2 transition-colors ${
                    activeTab === "evidence"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <ShieldCheck className="h-4 w-4" />
                  Evidence Provenance ({activeProfile.evidence.length})
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setActiveTab("profile")}
                  className={`pb-3 px-4 flex items-center gap-2 border-b-2 transition-colors ${
                    activeTab === "profile"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <User className="h-4 w-4" />
                  Professional Profile
                </button>
                <button
                  onClick={() => setActiveTab("evidence")}
                  className={`pb-3 px-4 flex items-center gap-2 border-b-2 transition-colors ${
                    activeTab === "evidence"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <ShieldCheck className="h-4 w-4" />
                  Evidence Provenance ({activeProfile.evidence.length})
                </button>
              </>
            )}
          </div>

          {/* Tab Content */}
          {activeTab === "technographics" && companyProfile && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {companyProfile.technographics.map((tech, i) => (
                  <div key={i} className="bg-surface-200/50 border border-border p-3.5 rounded-lg space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-foreground text-sm">{tech.name}</span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-medium ${
                          tech.classification === "VERIFIED"
                            ? "bg-success/20 text-success border border-success/30"
                            : "bg-warning/20 text-warning border border-warning/30"
                        }`}
                      >
                        {tech.classification}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">{tech.category}</p>
                    {tech.source_url && (
                      <a
                        href={tech.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] text-primary hover:underline flex items-center gap-1 pt-1"
                      >
                        Source verification <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "funding" && companyProfile && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {companyProfile.funding_rounds.map((round, i) => (
                  <div key={i} className="bg-surface-200/50 border border-border p-4 rounded-lg space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-foreground text-base">{round.round_name}</span>
                      <span className="font-mono text-xs text-muted-foreground">{round.round_date || "N/A"}</span>
                    </div>
                    {round.amount_usd && (
                      <div className="text-xl font-bold font-mono text-accent-cyan">
                        {formatCurrency(round.amount_usd)}
                      </div>
                    )}
                    <div className="text-xs text-muted-foreground pt-1">
                      <span className="font-medium text-foreground">Investors: </span>
                      {round.investors.length > 0 ? round.investors.join(", ") : "Undisclosed"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "jobs" && companyProfile && (
            <div className="space-y-4">
              <div className="space-y-2">
                {companyProfile.active_jobs.map((job, i) => (
                  <div key={i} className="bg-surface-200/50 border border-border p-3.5 rounded-lg flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold text-foreground text-sm">{job.title}</h4>
                      <p className="text-xs text-muted-foreground">{job.department || "Engineering"} &bull; {job.location || "Remote"}</p>
                      {job.required_technologies.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-1.5">
                          {job.required_technologies.map((t, idx) => (
                            <span key={idx} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-300 font-mono text-muted-foreground">
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "profile" && personProfile && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-surface-200/50 border border-border p-4 rounded-lg space-y-2">
                  <h3 className="font-bold text-foreground text-sm uppercase tracking-wider font-mono">Work History</h3>
                  <div className="space-y-3 pt-2">
                    {personProfile.work_history.map((w, idx) => (
                      <div key={idx} className="border-l-2 border-primary pl-3 space-y-0.5">
                        <div className="font-semibold text-sm text-foreground">{w.title}</div>
                        <div className="text-xs text-primary">{w.company_name}</div>
                        <div className="text-[10px] text-muted-foreground font-mono">
                          {w.start_date || "N/A"} - {w.end_date || (w.is_current ? "Present" : "N/A")}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-surface-200/50 border border-border p-4 rounded-lg space-y-2">
                  <h3 className="font-bold text-foreground text-sm uppercase tracking-wider font-mono">Skills & Competencies</h3>
                  <div className="flex flex-wrap gap-1.5 pt-2">
                    {personProfile.skills.map((s, idx) => (
                      <span key={idx} className="text-xs px-2.5 py-1 rounded bg-surface-300 font-mono text-foreground border border-border">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "evidence" && (
            <div className="space-y-3">
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-border text-[10px] font-mono text-muted-foreground uppercase bg-surface-200/50">
                      <th className="p-3">Category</th>
                      <th className="p-3">Claim</th>
                      <th className="p-3">Classification</th>
                      <th className="p-3">Confidence</th>
                      <th className="p-3">Source & Link</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y border-border">
                    {activeProfile.evidence.map((ev, i) => (
                      <tr key={i} className="hover:bg-surface-200/50">
                        <td className="p-3 font-mono text-muted-foreground">{ev.data_category}</td>
                        <td className="p-3 font-medium text-foreground">{ev.claim}</td>
                        <td className="p-3 font-mono">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                              ev.verification_classification === "VERIFIED"
                                ? "bg-success/20 text-success"
                                : "bg-warning/20 text-warning"
                            }`}
                          >
                            {ev.verification_classification}
                          </span>
                        </td>
                        <td className="p-3 font-mono text-muted-foreground">{(ev.confidence * 100).toFixed(0)}%</td>
                        <td className="p-3 truncate max-w-xs">
                          {ev.source_url ? (
                            <a href={ev.source_url} target="_blank" rel="noreferrer" className="text-primary hover:underline flex items-center gap-1">
                              <ExternalLink className="h-3 w-3 shrink-0" />
                              <span className="truncate">{ev.source_url}</span>
                            </a>
                          ) : (
                            <span className="text-muted-foreground">Crustdata REST API</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Confirmation Modal for Level 3 Deep Enrichment */}
      {showConfirmModal && deepCostEstimate && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface-100 border border-border p-6 rounded-xl shadow-xl max-w-md w-full space-y-4">
            <div className="flex items-center gap-3 text-warning">
              <Zap className="h-6 w-6" />
              <h3 className="text-lg font-bold text-foreground">Confirm Deep Real-Time Scrape</h3>
            </div>

            <p className="text-sm text-muted-foreground">
              Deep enrichment triggers real-time web crawlers to fetch live headcount trends, executive changes, and latest career signals.
            </p>

            <div className="bg-surface-200 border border-border p-3.5 rounded-lg space-y-2 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-muted-foreground">TARGET ENTITY:</span>
                <span className="font-semibold text-foreground">{deepCostEstimate.entity_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">ESTIMATED CREDITS:</span>
                <span className="font-bold text-warning">{deepCostEstimate.estimated_credits.toFixed(1)} Credits</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">REMAINING APP BUDGET:</span>
                <span className="font-bold text-primary">{budget ? budget.remaining_credits.toFixed(1) : "—"} Credits</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">CRUSTDATA ACCOUNT BALANCE:</span>
                <span className="text-foreground">{deepCostEstimate.account_credits_available.toFixed(1)} Credits</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">MINIMUM SAFETY FLOOR:</span>
                <span className="text-foreground">{deepCostEstimate.safety_threshold.toFixed(1)} Credits</span>
              </div>
            </div>

            {deepCostEstimate.warning_message && (
              <p className="text-xs text-destructive font-medium">{deepCostEstimate.warning_message}</p>
            )}

            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="flex-1 btn btn-secondary text-xs py-2"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDeepEnrichment}
                disabled={!deepCostEstimate.can_proceed || isEnriching}
                className="flex-1 btn btn-primary text-xs py-2 flex items-center justify-center gap-1.5"
              >
                {isEnriching ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
                Confirm & Execute
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Budget Increase Approval Modal */}
      {showBudgetModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface-100 border border-border p-6 rounded-xl shadow-xl max-w-md w-full space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2.5 text-primary">
                <Coins className="h-5 w-5" />
                <h3 className="text-base font-bold text-foreground">Approve Crustdata Budget Increase</h3>
              </div>
              <button
                onClick={() => setShowBudgetModal(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              When the application spending budget is reached, new paid operations pause automatically. You must grant explicit approval to allocate additional budget credits.
            </p>

            <div className="bg-surface-200 border border-border p-3 rounded-lg space-y-1.5 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-muted-foreground">CURRENT BUDGET:</span>
                <span className="font-bold text-foreground">{budget ? budget.total_budget.toLocaleString() : "1,200"} credits</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">CURRENT USAGE:</span>
                <span className="text-foreground">{budget ? budget.used_credits.toFixed(1) : "0.0"} credits</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">NEW PROJECTED BUDGET:</span>
                <span className="font-bold text-emerald-400">
                  {budget ? (budget.total_budget + (budgetIncreaseAmount || 0)).toLocaleString() : 1700} credits
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-foreground block">
                Additional Credits to Approve:
              </label>
              <div className="flex gap-2">
                {[250, 500, 1000].map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setBudgetIncreaseAmount(preset)}
                    className={`flex-1 py-1.5 text-xs font-mono font-medium rounded-lg border transition ${
                      budgetIncreaseAmount === preset
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-surface-200 hover:bg-surface-300 text-foreground border-border"
                    }`}
                  >
                    +{preset} cr
                  </button>
                ))}
              </div>
              <input
                type="number"
                min="1"
                value={budgetIncreaseAmount}
                onChange={(e) => setBudgetIncreaseAmount(Math.max(1, Number(e.target.value)))}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm font-mono focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground block">
                Approval Note / Reason:
              </label>
              <input
                type="text"
                value={budgetIncreaseReason}
                onChange={(e) => setBudgetIncreaseReason(e.target.value)}
                placeholder="e.g. Approved for competitive intelligence sprint..."
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="p-2.5 rounded bg-surface-200/50 border border-border text-[11px] text-muted-foreground space-y-1">
              <div className="font-semibold text-foreground flex items-center gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                Critical Safeguard
              </div>
              <p>
                This increases the local application spending ceiling only. It does not purchase or bypass Crustdata API account credits or billing restrictions.
              </p>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowBudgetModal(false)}
                className="flex-1 btn btn-secondary text-xs py-2"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApproveBudgetIncrease}
                disabled={isIncreasingBudget || budgetIncreaseAmount <= 0}
                className="flex-1 btn btn-primary text-xs py-2 flex items-center justify-center gap-1.5"
              >
                {isIncreasingBudget ? <RefreshCw className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                Approve & Resume
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search History Drawer/Section */}
      {searchHistory.length > 0 && (
        <div className="bg-surface-100 border border-border p-4 rounded-xl space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <History className="h-4 w-4" />
            Recent Searches
          </h3>
          <div className="flex flex-wrap gap-2">
            {searchHistory.map((h) => (
              <button
                key={h.id}
                onClick={() => quickSearch(h.search_query)}
                className="px-2.5 py-1 bg-surface-200 hover:bg-surface-300 rounded text-xs font-mono text-foreground border border-border flex items-center gap-1.5"
              >
                <span>{h.search_query}</span>
                <span className="text-[10px] text-muted-foreground">({h.entity_type})</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
