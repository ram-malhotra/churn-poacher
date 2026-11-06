# The Churn Poacher
### AI-Powered Competitive Intelligence & Customer Acquisition System

**The Churn Poacher** is a multi-agent AI system that detects when customers experience severe pain with their existing enterprise software vendors (outages, unexpected price spikes, deprecations) and converts those signals into actionable, high-conviction migration opportunities.

**First ICP Target**: Datadog $\to$ SigNoz / Grafana

---

## Architecture Overview

```
                                      ┌────────────────────────────────┐
                                      │       CENTRAL ORCHESTRATOR     │
                                      └────────────────┬───────────────┘
                                                       │
         ┌────────────────────────┬────────────────────┼───────────────────┬────────────────────────┐
         │                        │                    │                   │                        │
         ▼                        ▼                    ▼                   ▼                        ▼
┌──────────────────┐    ┌──────────────────┐  ┌─────────────────┐  ┌──────────────────┐   ┌──────────────────┐
│  LISTENER AGENT  │───▶│  PROFILER AGENT  │─▶│ FINOPS & ARCH   │─▶│ COPYWRITER AGENT │──▶│ DEPOSITION PACK  │
│  (Reddit, HN,    │    │  (Entity Match,  │  │ (Delta Matrix,  │  │ (Tailored Exec   │   │ (Actionable      │
│   Status, X)     │    │   Tech Stack)    │  │  Migration Arch)│  │  Outreach Draft) │   │  Dossier)        │
└──────────────────┘    └──────────────────┘  └─────────────────┘  └──────────────────┘   └──────────────────┘
```

---

## 10-Phase Implementation Roadmap

- [x] **Phase 1: Project Structure & Environment Setup** (Modular layout, Pydantic settings, health check API, test harness)
- [x] **Phase 2: Database & Backend Foundation** (SQLAlchemy models, Async DB sessions, CRUD repositories, REST API v1)
- [x] **Phase 3: Listener Agent** (Datadog Status & HN Live Adapters, Reddit OAuth Graceful Fallback, Synthetic Generator, Normalization, Classification, Deduplication)
- [x] **Phase 4: Profiler Agent** (Entity resolution, DNS verification, GitHub/Job technology profiling, explainable 5-dimension ICP scoring, strict anti-hallucination evidence validation)
- [x] **Phase 5: FinOps & Architect Agent** (Datadog vs. SigNoz/Grafana Delta Matrix, 5 platforms, Low/Base/High scenarios, sensitivity ranking, OpenTelemetry dual-shipping YAML generator, 7-phase migration plan, rollback strategy, DepositionDossier persistence)
- [x] **Phase 6: Copywriter Agent** (Context-aware outreach drafts, executive emails, LinkedIn sequences, technical pitch, value prop, objection matrix, evidence guard, human-in-the-loop review)
- [x] **Phase 7: Central Orchestration** (End-to-end multi-agent pipeline, workflow state machine, retry policies, qualification-based routing, duplicate execution prevention, REST APIs)
- [x] **Phase 8: Frontend Dashboard** (Next.js 14 App Router, TypeScript, Tailwind CSS, TanStack Query, Recharts, React Flow DAG, 10 Production Views, Human-in-the-Loop review & export gating)
- [x] **Phase 9: End-to-End Testing & LLM Integration** (Multi-provider LLM abstraction [OpenAI, Gemini, Claude, Fallback], structured Pydantic schemas, full E2E lifecycle tests, export security gating, 89 green backend tests, clean Next.js build)
- [x] **Phase 10: Production Deployment & Infrastructure** (Docker Compose multi-service stack, PostgreSQL async connection pooling & Alembic migrations, Redis persistent task queue & background worker daemon, Role-Based Access Control [RBAC] & JWT security, deep health check probes, enterprise operational documentation)

---

## Phase 5: FinOps & Architect Agent

### 1. Part A: FinOps Intelligence Engine
- **Supported Platforms**:
  1. Datadog (Enterprise Hosts, APM, Custom Metrics, Log Ingestion & Retention)
  2. SigNoz Cloud (Zero per-node tax, pure usage-based ingestion)
  3. SigNoz Self-Hosted (Free OSS Community Edition + AWS compute/storage)
  4. Grafana Cloud (Active series metrics, logs, traces)
  5. Grafana OSS (Mimir, Loki, Tempo self-hosted stack)
- **Granular Scenarios**:
  - `LOW`: Conservative telemetry scale (-35%)
  - `BASE`: Standard derived baseline based on company size and infrastructure footprint
  - `HIGH`: Heavy custom metrics expansion (+50%)
- **Calculations**:
  - Itemized monthly & annual platform expenditures
  - Annual savings and savings percentage
  - Estimated migration cost & payback period in months
  - 3-Year Total Cost of Ownership (TCO) across all target platforms
  - Sensitivity analysis identifying highest-variance telemetry levers

### 2. Part B: Architecture Migration Engine
- **Current Architecture Assessment**: Audits application services, Kubernetes environments, and ingestion methods, labeling components as `VERIFIED`, `INFERRED`, or `UNKNOWN`.
- **OpenTelemetry Dual-Shipping Configuration**: Produces validated, production-grade `otel-collector-config.yaml` with native Datadog trace receiver (`:8126`) and dual-shipping pipeline multiplexing.
- **7-Phase Takeout Roadmap**:
  - Phase 1: Telemetry Discovery & Footprint Audit (Days 1–3)
  - Phase 2: Parallel OpenTelemetry Collector Deployment (Days 4–7)
  - Phase 3: Dual-Shipping & Data Parity Validation (Days 8–14)
  - Phase 4: Performance & Dashboard Cost Verification (Days 15–21)
  - Phase 5: Gradual Traffic Cutover / Canary Waves (Days 22–30)
  - Phase 6: Datadog Dependency Reduction (Days 31–45)
  - Phase 7: Final Decommissioning & Contract Termination (Days 46–60)
- **Rollback Playbook**: Zero-loss rollback strategy with parallel pipeline isolation.

---

## REST API FinOps & Architecture Endpoints

```bash
# Generate financial analysis for an identified company
curl -X POST "http://localhost:8000/api/v1/finops/run/{company_id}"

# Generate OpenTelemetry migration blueprint and collector YAML
curl -X POST "http://localhost:8000/api/v1/architecture/run/{company_id}?target_backend=SigNoz Cloud"

# Generate and persist complete Deposition Dossier in SQLite
curl -X POST "http://localhost:8000/api/v1/finops/dossier/{company_id}"

# Retrieve stored financial report or migration blueprint
curl "http://localhost:8000/api/v1/finops/{company_id}"
curl "http://localhost:8000/api/v1/architecture/{company_id}"

# Inspect published pricing catalog with verification dates & source URLs
curl "http://localhost:8000/api/v1/finops/pricing"

# Retrieve aggregate financial metrics across all dossiers
curl "http://localhost:8000/api/v1/finops/metrics"
```

---

## Phase 6: Copywriter Agent

The Copywriter Agent translates the intelligence generated by the Listener, Profiler, and FinOps/Architect agents into personalized, evidence-grounded B2B sales collateral without generic cold spam or creepy tracking tropes.

### 1. Key Modules & Collateral Outputs
- **Executive Email Generator** (`executive_email.py`):
  - *Variant 1 (Executive Concise)*: Targeted at CTOs & VPs of Engineering. High impact, 3 subject lines with distinct hooks, preheader, projected savings ($ and %), and low-friction 15-minute architecture review CTA.
  - *Variant 2 (Technical-Commercial)*: Targeted at Heads of Infrastructure & FinOps Leads. Granular cost breakdown (APM host tax vs. ingestion-only), OpenTelemetry port `:8126` Datadog compatibility receiver, and dual-shipping POC proposal.
- **LinkedIn Multi-Touch Writer** (`linkedin_writer.py`):
  - *Touch 1*: Connection request strictly under 300 characters, engineering peer tone.
  - *Touch 2*: Post-connection value-add sharing architectural benchmarks and OTel patterns.
  - *Touch 3*: Technical-commercial follow-up sharing financial delta and parallel testing blueprint.
- **Technical Migration Pitch** (`technical_pitch.py`):
  - In-depth architectural brief: Datadog proprietary agent vs. CNCF OpenTelemetry Collector.
  - Zero-code migration via port `:8126` native Datadog trace receiver (no application code refactor).
  - Dual-shipping validation and PromQL alert/dashboard parity mapping.
- **Value Proposition Brief** (`value_proposition.py`):
  - 1-page financial business case comparing Datadog baseline to target challenger (BASE scenario).
  - The "Datadog Tax" decomposition: Host tax, custom metrics multiplication, and log retention fees.
  - TCO calculation: Net 1st-year ROI after migration costs, payback period in months, and 3-year cumulative savings.
- **Enterprise Objection Handler** (`objection_handler.py`):
  - Pre-arms teams with talking points and technical proofs for 7 standard enterprise objections: Engineering Bandwidth, Downtime Risk, Contract Lock-in, Historical Data Loss, Self-Hosted Maintenance, "Datadog Works Fine", and Rollback Safety.
- **Evidence Guard & Anti-Hallucination Layer** (`evidence_guard.py`):
  - Enforces strict estimation labeling ("estimated", "projected", "modeled") when numbers derive from inferred profiles.
  - Scans for and flags forbidden marketing buzzwords (`game-changing`, `revolutionary`, `rockstar`, `10x engineer`, etc.).
  - Blocks fabricated email addresses or invented personal identities.
  - Generates an `EvidenceAuditReport` with a quantitative `hallucination_risk_score`.

### 2. Human-in-the-Loop Governance & Gated Export
All generated outreach collateral is persisted into `DepositionDossier.outreach_drafts` in a default status of `DRAFT_PENDING_APPROVAL`.
- **Strict Export Gate**: The `/copywriter/{dossier_id}/export` endpoint **strictly prohibits export** (returning HTTP 403 Forbidden) unless the dossier has been explicitly reviewed and approved via `/copywriter/{dossier_id}/approve`.
- Never automatically sends unsolicited emails or messages.

```bash
# Generate outreach package and attach to dossier
curl -X POST "http://localhost:8000/api/v1/copywriter/run/{company_id}?target_challenger=SigNoz Cloud"

# Retrieve generated drafts
curl "http://localhost:8000/api/v1/copywriter/{company_id}"

# Attempt export BEFORE approval (returns 403 Forbidden)
curl -X POST "http://localhost:8000/api/v1/copywriter/{dossier_id}/export"

# Approve draft
curl -X PATCH "http://localhost:8000/api/v1/copywriter/{dossier_id}/approve"

# Export approved package as markdown/JSON bundle (succeeds with 200 OK)
curl -X POST "http://localhost:8000/api/v1/copywriter/{dossier_id}/export"

# Reject draft with feedback reason
curl -X PATCH "http://localhost:8000/api/v1/copywriter/{dossier_id}/reject" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Revise tone for enterprise compliance team"}'

# View copywriting & governance metrics
curl "http://localhost:8000/api/v1/copywriter/metrics"
```

---

## Phase 7: Central Orchestrator

The Central Orchestrator is the mission-control engine of The Churn Poacher. It coordinates the execution lifecycle of all specialized agents (Listener, Profiler, FinOps, Architecture, and Copywriter) with qualification-based gating, error recovery, duplicate prevention, and strict human governance.

### 1. Workflow Pipeline & State Machine

```
   PENDING
      │
      ▼
   LISTENER_RUNNING ───▶ Signal Ingestion & Anomaly Triage
      │
      ▼
   PROFILER_RUNNING ───▶ Entity Resolution & Technology Fingerprinting
      │
      ▼
   QUALIFICATION_REVIEW ──[Unqualified / Hobbyist / Student]──▶ REJECTED (Halted)
      │
   [Qualified / Enterprise]
      ▼
   FINOPS_RUNNING ───▶ Telemetry Cost Modeling & Savings Delta
      │
      ▼
   ARCHITECT_RUNNING ───▶ OTel Collector Blueprint (:8126) & 7-Stage Migration
      │
      ▼
   COPYWRITER_RUNNING ───▶ Personalized Collateral & Evidence Guard Audit
      │
      ▼
   DRAFT_PENDING_APPROVAL ──▶ Human-in-the-Loop Review Gate
      │
      ├───────────────────────┬────────────────────────┐
      ▼                       ▼                        ▼
   APPROVED                REJECTED             EXPORT (Gated)
      │                                       (403 if unapproved)
      ▼
   COMPLETED
```

### 2. Orchestration Policies & Features
- **Qualification-Based Routing**: Disqualifies non-commercial signals (students, hobbyists, micro-teams) at the Profiler/Qualification gate. Unqualified companies are marked `REJECTED` and immediately dropped from downstream FinOps and collateral processing to conserve resources.
- **Duplicate Execution Prevention**: Active in-flight workflows prevent duplicate concurrent executions targeting the same company or signal, returning HTTP 409 Conflict.
- **Partial Failure Recovery & Resumption**: When retrying a failed workflow (`/api/v1/orchestrator/retry/{workflow_id}`), successfully completed upstream steps are preserved and skipped, resuming execution directly from the failed milestone.
- **Timeout Protection**: Workflows are bound to configurable execution deadlines (default: 60s) with graceful `TimeoutError` handling.
- **Full Observability**: Step execution durations, started/completed timestamps, inputs, outputs, and errors are tracked in `WorkflowExecution.step_history` and logged to `AgentExecutionLog`.
- **Human Approval Preservation**: The orchestrator strictly leaves generated dossiers in `DRAFT_PENDING_APPROVAL`. It never automatically emails, messages, or exports unapproved materials.

### 3. Orchestration REST API Endpoints

```bash
# 1. Trigger an orchestrated pipeline run (full pipeline, single signal, or single company)
curl -X POST "http://localhost:8000/api/v1/orchestrator/run" \
  -H "Content-Type: application/json" \
  -d '{
    "target_challenger": "SigNoz Cloud",
    "include_synthetic": true,
    "timeout_seconds": 60
  }'

# 2. Get status and step-by-step history of a specific workflow
curl "http://localhost:8000/api/v1/orchestrator/status/{workflow_id}"

# 3. List recent workflows (with optional status filter and pagination)
curl "http://localhost:8000/api/v1/orchestrator/workflows?status=DRAFT_PENDING_APPROVAL&limit=20"

# 4. Inspect aggregate orchestration metrics
curl "http://localhost:8000/api/v1/orchestrator/metrics"

# 5. Retry a failed workflow from its last failed step
curl -X POST "http://localhost:8000/api/v1/orchestrator/retry/{workflow_id}"
```

### 4. Known Limitations
- Background task queues (e.g. Celery / ARQ / Redis) are intentionally deferred to Phase 10; current execution is fully asynchronous within FastAPI's async runtime.
- External vendor APIs (e.g., Live Reddit PRAW, LinkedIn APIs) require configured API credentials; otherwise, the system seamlessly uses live Hacker News, Datadog Status RSS, and synthetic labeled pipelines.

---

## Phase 8: Frontend Dashboard (Next.js 14 & Tailwind CSS)

A dark-mode enterprise intelligence dashboard (`#08090d` charcoal canvas with violet/cyan accents and Linear/Palantir aesthetics).

### 1. Technology Stack
- **Framework**: Next.js 14 (App Router) & React 18
- **Language**: TypeScript (strict type checking enabled)
- **Styling**: Tailwind CSS & PostCSS
- **Data Fetching**: TanStack React Query v5 (automatic polling & cache invalidation)
- **Charts & Visualizations**: Recharts (modeled financial delta charts & scenario comparisons)
- **Agent Topology**: `@xyflow/react` v12 (interactive, navigable execution DAG)
- **Icons**: Lucide React

### 2. Available Views & Routes
1. `/` — **Intelligence Overview**: High-level KPI metrics (signals detected, qualified prospects, potential annual savings, dossiers created), top opportunity cards, recent distress signals, and agent execution readiness.
2. `/signals` — **Distress Signal Monitor**: Live stream of ingested Datadog complaints, outage alerts, and price spikes with source badges, urgency tags, search, and one-click pipeline execution.
3. `/companies` — **Identified Companies Directory**: Searchable list of resolved companies, qualification status badges, ICP score bars, tech stack indicators, and quick links to dossiers.
4. `/companies/[id]` — **Deep Company Dossier**: Complete 7-tab intelligence dossier:
   - *Overview*: Executive summary, ICP score, qualification rationales.
   - *Evidence*: Distinguish between `VERIFIED` (with source URL) and `INFERRED` facts.
   - *Technology*: Detected Datadog agents, Kubernetes clusters, APM, and cloud providers.
   - *Financials*: Datadog vs. SigNoz/Grafana Delta Matrix across Low, Base, and High scenarios.
   - *Architecture*: Side-by-side architecture comparison, syntax-highlighted `otel-collector-config.yaml` (`:8126`), 7-stage migration schedule, and rollback plan.
   - *Outreach Studio*: Executive email variations, LinkedIn sequences, 7-point objection matrix, Evidence Guard anti-hallucination verification badge, and Human-in-the-Loop Approve/Reject/Export controls.
   - *Activity*: Timestamped audit trail of agent actions and transitions.
5. `/financials` — **FinOps Analytics**: Modeled annual savings breakdown, 3-year TCO projections, payback periods, sensitivity ranking, and the published pricing catalog.
6. `/architect` — **Migration Architect**: Current vs. OpenTelemetry target architecture, dual-shipping collector configurations, 7-phase takeout timeline, and disaster recovery playbooks.
7. `/outreach` — **Outreach Studio**: Central collateral review hub with strict Human-in-the-Loop approval/rejection and markdown export gating.
8. `/agents` — **Agent Monitor**: Live, interactive React Flow DAG showing node states (`Listener` $\to$ `Profiler` $\to$ `FinOps` $\to$ `Architect` $\to$ `Copywriter` $\to$ `Human Approval Gate`) and recent execution logs.
9. `/history` — **Execution History**: Chronological log of multi-agent pipeline executions, searchable by workflow ID, status filters, latency metrics, and expandable granular step transitions.
10. `/settings` — **System Settings & Governance**: Monitored vendor defaults, displacement targets (SigNoz vs. Grafana), FinOps hourly rates, anti-hallucination policies, and synthetic distress injection triggers.

### 3. How to Run Frontend

```powershell
# Development server (http://localhost:3000)
cd frontend
npm run dev

# Production build & verification
npm run build
npm run start
```

---

## Phase 9: End-to-End Testing & LLM Provider Abstraction

### 1. Multi-Provider LLM Architecture (`app/core/llm/`)
Provides a unified abstraction across three major commercial LLM providers with automatic credential discovery and zero-latency deterministic fallbacks:
- **Google Gemini**: Uses `GEMINI_API_KEY` and `GEMINI_MODEL` (default: `gemini-1.5-flash`) via the Gemini REST API with native JSON schemas.
- **OpenAI**: Uses `OPENAI_API_KEY` and `OPENAI_MODEL` (default: `gpt-4o-mini`) via chat completions with JSON mode.
- **Anthropic Claude**: Uses `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` (default: `claude-3-5-sonnet-20241022`) via Messages API.
- **Deterministic Fallback Engine**: Always available, produces 100% compliant structured output without external API keys or network dependencies. Ensures full automated test reliability.

### 2. Guardrails & Separation of Concerns
- **LLM Tasks**: Nuance sentiment analysis, unstructured evidence extraction, executive briefing summarization, natural language migration explanations, and executive copy polish.
- **Deterministic Python Enforcement**: ICP scoring, qualification thresholds, telemetry cost modeling, savings calculations, 7-stage migration scheduling, Evidence Guard anti-hallucination audits, and human approval gates remain strictly implemented in deterministic Python code. Financial numbers are locked to prevent fabricated savings claims.

### 3. End-to-End Test Suite
Comprehensive integration tests cover the entire system lifecycle:
- Ingestion of public complaints & vendor incidents via Listener adapters.
- Content fingerprint deduplication preventing redundant processing.
- Entity resolution and deterministic ICP qualification.
- FinOps cost modeling (Datadog vs. SigNoz/Grafana across Low, Base, High scenarios).
- OpenTelemetry Collector YAML (`:8126`) and 7-stage migration blueprint synthesis.
- Copywriter personalized collateral generation with Evidence Guard anti-hallucination audits.
- Human Approval Gate: strict HTTP 403 Forbidden enforcement on `/export` prior to approval; successful export of markdown bundles once approved.

---

## Phase 10: Production Deployment & Infrastructure

### 1. Multi-Service Container Topology (`docker-compose.yml`)
The complete stack is packaged as containerized microservices ready for staging and production:
- **`postgres`**: PostgreSQL 16 Alpine with persistent volume (`postgres_data`), connection pooling, and health checks.
- **`redis`**: Redis 7 Alpine with persistent volume (`redis_data`) serving the asynchronous workflow queue and distributed locking.
- **`backend`**: FastAPI application running on Python 3.11-slim as an unprivileged user (`appuser`), multi-stage build, exposed on `:8000`.
- **`worker`**: Background worker daemon (`app.worker.main`) executing pipeline runs asynchronously from Redis, with 15s heartbeats.
- **`frontend`**: Next.js 14 standalone container running on Node 20-alpine as an unprivileged user (`nextjs`), exposed on `:3000`.

### 2. Database Pooling & Alembic Migrations
- **Async Connection Pooling**: Production PostgreSQL engine configured with `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, and `pool_recycle=3600`.
- **Alembic Engine**: Async migration setup (`alembic/env.py`) with initial revision `f3ca93a9fb86_initial_schema_with_users.py` managing all tables and indexes.

### 3. Redis Queue & Persistent Background Workers
- **Queue Engine** (`app/worker/queue.py`): Redis list-based queue (`churn_poacher:workflow_queue`) with JSON task envelopes and task metadata tracking.
- **Distributed Locking**: Protects targets from concurrent duplicate runs with `churn_poacher:lock:<target_id>` and automatic TTL expiration.
- **Worker Daemon** (`app/worker/worker.py`): Non-blocking `blpop` worker polling with timeout protection, isolated database sessions per task, and graceful SIGTERM/SIGINT shutdown.
- **Orchestrator Integration**: `run_pipeline(..., async_worker=True)` enqueues tasks and returns immediately with `status: "queued"`.

### 4. Security & Role-Based Access Control (RBAC)
- **User Roles**: `ADMINISTRATOR`, `SALES_MANAGER`, `ANALYST`.
- **Password Security**: Salted PBKDF2-HMAC-SHA256 password hashing (100,000 iterations).
- **JWT Auth**: HS256 tokens with role claims and configurable expiration.
- **Human Approval & Export Gate**: `/approve`, `/reject`, and `/export` endpoints enforce `SALES_MANAGER` or `ADMINISTRATOR` permissions. `ANALYST` users cannot approve or export collateral.

### 5. Deep Observability Probes
- `/api/v1/health/deep` validates end-to-end component readiness:
  - Database connectivity and query round-trip latency (ms).
  - Redis connectivity, ping latency (ms), and active queue length.
  - Background worker heartbeat freshness (<60s = active).
  - Configured vs. active LLM provider.

### 6. Production Documentation
Complete enterprise operational manuals are available in `docs/`:
- [`docs/ARCHITECTURE.md`](file:///C:/Users/Ram%20Malhotra/.gemini/antigravity/scratch/churn-poacher/docs/ARCHITECTURE.md): System topology, micro-architecture, and state transitions.
- [`docs/DEPLOYMENT.md`](file:///C:/Users/Ram%20Malhotra/.gemini/antigravity/scratch/churn-poacher/docs/DEPLOYMENT.md): Docker Compose quickstart, production checklist, and seeding.
- [`docs/ENVIRONMENT_VARIABLES.md`](file:///C:/Users/Ram%20Malhotra/.gemini/antigravity/scratch/churn-poacher/docs/ENVIRONMENT_VARIABLES.md): Comprehensive dictionary of all configuration parameters.
- [`docs/SECURITY.md`](file:///C:/Users/Ram%20Malhotra/.gemini/antigravity/scratch/churn-poacher/docs/SECURITY.md): RBAC matrix, secret rotation, and human-in-the-loop safeguards.
- [`docs/DATABASE_BACKUP.md`](file:///C:/Users/Ram%20Malhotra/.gemini/antigravity/scratch/churn-poacher/docs/DATABASE_BACKUP.md): Automated PostgreSQL dump, restore runbooks, and disaster recovery.
- [`docs/TROUBLESHOOTING.md`](file:///C:/Users/Ram%20Malhotra/.gemini/antigravity/scratch/churn-poacher/docs/TROUBLESHOOTING.md): Operational runbooks, lock release, and container diagnostics.

### 7. How to Launch with Docker Compose

```bash
# 1. Clone & copy environment configuration
cp .env.example .env

# 2. Start all services in detached mode
docker compose up -d

# 3. Apply database migrations
docker compose run --rm backend alembic upgrade head

# 4. Seed default admin & sales manager accounts
curl -X POST http://localhost:8000/api/v1/auth/seed-defaults

# 5. Access the applications
# Frontend Dashboard: http://localhost:3000
# Backend OpenAPI Docs: http://localhost:8000/docs
# Deep Health Probe: http://localhost:8000/api/v1/health/deep
```
<img width="3994" height="1354" alt="image" src="https://github.com/user-attachments/assets/dc53d9ef-ea96-4d59-98b3-72679165c322" />


---

## Automated Test Execution

```powershell
cd backend
.\.venv\Scripts\pytest.exe -v
```
All **96 automated tests** passing 100% green across all components, agents, orchestrator, LLM abstraction, auth & RBAC, Redis worker queue, and end-to-end integration flows.
