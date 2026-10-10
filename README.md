# Dalanda AI — Local File Agent & Multi-MCP Execution Harness

A secure, modular, tool-augmented AI workspace assistant built in Python. The system implements a **ReAct (Reasoning + Acting)** execution loop with autonomous task decomposition, dependency-aware parallel/sequential sub-agent scheduling, semantic vector memory retrieval, token-budget-aware context management, sandboxed filesystem tools, offline document/OCR processing, an extensible **Model Context Protocol (MCP)** multi-server integration layer, **sub-agent delegation**, a **permission gate with switchable runtime modes**, and a full **observability stack** (Prometheus metrics, OpenTelemetry distributed tracing, Perses dashboards).

---

## Table of Contents

- [Overview & Key Features](#overview--key-features)
- [System Architecture](#system-architecture)
- [Core Components](#core-components)
- [Project Directory Structure](#project-directory-structure)
- [Prerequisites & Requirements](#prerequisites--requirements)
- [Installation & Setup](#installation--setup)
- [Configuration & Environment Variables](#configuration--environment-variables)
- [How to Run the Agent](#how-to-run-the-agent)
- [Interactive CLI Commands & Prompts](#interactive-cli-commands--prompts)
- [Model Context Protocol (MCP) Integrations](#model-context-protocol-mcp-integrations)
- [Tool Capabilities & Registry](#tool-capabilities--registry)
- [Sub-Agent Delegation & Task Scheduling](#sub-agent-delegation--task-scheduling)
- [Tool Router](#tool-router)
- [Context & Token Budget Management](#context--token-budget-management)
- [Permission System](#permission-system)
- [Observability Stack](#observability-stack)
- [Security & Sandboxing Architecture](#security--sandboxing-architecture)
- [Automated Test Suite](#automated-test-suite)
- [Docker Deployment](#docker-deployment)
- [Academic & Engineering Highlights](#academic--engineering-highlights)

---

## Overview & Key Features

### 1. Plan-then-Act, Task Decomposition & Dependency-Aware Scheduling
- **Deep Thinking & Task Decomposition**: Complex user requests are analyzed by the `Planner` and decomposed into a dependency graph of tasks (`{id, description, depends_on}`).
- **Dependency-Aware Task Scheduler**: `TaskScheduler` (`agent/task_scheduler/scheduler.py`) tracks task status and exposes only the tasks whose dependencies have completed — independent tasks become eligible to run together, dependent tasks wait for their prerequisites.
- **Parallel / Sequential / Hybrid Sub-Agent Execution**: `Agent.run_scheduled_tasks()` runs each batch of ready tasks **concurrently** via `asyncio.gather`, each as its own sub-agent. Tasks with no shared dependencies execute in parallel; tasks with dependencies wait their turn — both patterns can occur in the same request.
- **ReAct Execution Loop**: After any scheduled batch completes, the agent alternates between model reasoning, structured tool invocation via the `Harness`, and environment observation until the task is complete.

### 2. Sub-Agent Delegation
- **Specialized Sub-Agents**: The main agent can spawn `SubAgent` instances (`agent/subagent.py`) — either ad hoc, when the model calls `delegate_to_subagent` mid-conversation, or automatically, once per task produced by the scheduler — each with its own role, instructions, context, and independent tool-call budget (default: 10).
- **Task-Scoped Tool Selection**: Each sub-agent receives only the tools relevant to its assigned task, routed by the `ToolRouter`.
- **Unique Run IDs**: Every sub-agent execution is tagged with a unique `run_id` and linked to its parent's `parent_run_id` for full traceability.
- **Shared Harness**: Every sub-agent — ad hoc or scheduled — runs through the exact same `Harness` instance as its parent, so it is bound by the same permissions and observability.

### 3. Dual-Layer Semantic Memory & Token-Budget-Aware Context Compaction
- **Semantic Vector Retrieval**: Persistent long-term memory entries stored in `workspace/organizer/memory.json` are embedded using Sentence Transformers (`all-MiniLM-L6-v2`) and stored in `workspace/organizer/memory_embeddings.json`. Memory queries use cosine similarity ranking (threshold configured via `MIN_SIMILARITY` in `config/settings.py`) to retrieve only relevant context per turn.
- **Token-Aware Context Budgeting**: `CntxMgmt/budget.py` counts real tokens for the configured model (via its Hugging Face tokenizer) and computes how much of the model's context window is left for conversation history after reserving space for the system prompt, tool schemas, and the current turn.
- **Automatic Compaction**: Older conversation turns are summarized into a structured 7-section Markdown summary (`Goals & Intent`, `Constraints`, `Files & State`, `Key Decisions & Facts`, `Tool Results`, `Errors & Resolutions`, `Pending Next Steps`) whenever the stored history exceeds the available token budget, **or** whenever more than `COMPACTION_TRIGGER_TURNS` (12) turns have accumulated — whichever comes first.
- **Request-Level Overflow Guardrail**: Before every LLM call, the fully-assembled request is measured in tokens; if it would exceed the model's input limit, the agent stops itself with a clear message instead of sending an oversized (or truncated) request.
- **Oversized-Prompt Rejection**: A single user message larger than `MAX_USER_PROMPT_TOKENS` is rejected immediately, before any processing starts.
- **Short-Term Session Memory**: Ephemeral conversation history can be reset instantly with `/reset`.

### 4. Multi-Server Model Context Protocol (MCP)
- **Generic Multi-Client Manager**: `MCPManager` coordinates connections across multiple MCP servers over Streamable HTTP and Stdio transports.
- **Supported MCP Servers**:
  - **Exa MCP**: Real-time web search and information retrieval.
  - **Notion MCP**: Hosted Notion workspace integration with browser-assisted OAuth flow and persistent token storage (`mcp_client/notion_oauth.json`).
  - **Email MCP Server**: Custom-built local MCP microservice (`mcp_servers/email_server.py`) running via Uvicorn/HTTP for drafting and sending emails via SMTP.
  - **Google Calendar MCP Server**: Stdio MCP integration (`uvx calendar-mcp-server`) for calendar agenda querying, event creation, updates, and deletion.

### 5. Tool Router
- **Keyword-Based Tool Selection**: `ToolRouter` (`tools/router.py`) analyses the user's task text and selects only the relevant tool groups (filesystem, memory, web, email, calendar, scheduler, delegation) before passing them to the LLM or sub-agent.
- **Reduced Context Noise**: By limiting the active tool set per turn, the router keeps the model's context clean and reduces spurious tool calls — and reduces the token cost reserved for tool schemas (see [Context & Token Budget Management](#context--token-budget-management)).

### 6. Permission System with Switchable Runtime Modes
- **Central Permission Gate**: `PermissionManager` (`permissions/manager.py`) intercepts every tool call inside the Harness and classifies it as `read`, `write`, or `delete`.
- **Configurable Policies**: Per-tool policies are loaded from `config/permissions.json` and always take precedence over the active mode — e.g. `delete_memory` is permanently denied regardless of mode.
- **Runtime Permission Modes**: Switchable at any time via the `/mode` command — `default` (reads allowed, writes/deletes require confirmation), `auto` (reads and writes allowed automatically, deletes still require confirmation), and `bypass` (everything allowed, no prompts — requires re-typing `bypass` to confirm, since it removes the last safety net).

### 7. Sandboxed Local Compute & Document / OCR Processing
- **Filesystem Sandbox**: All local file operations are strictly restricted to the designated `workspace/` directory with path traversal protection (`safe_path()`).
- **Offline Document Extraction & OCR**: Tesseract OCR, PyPDF, and pdf2image extract text from images, scanned PDFs, and text files.
- **Rule-Based Document Classification**: Automatically classifies documents by keyword rules into categories (e.g., invoices, resumes, contracts) and exports reports to CSV and Excel (`.xlsx`).

### 8. Full Observability Stack
- **Prometheus Metrics** (`Observability/metrics.py`): Counters, gauges, and histograms tracking agent runs, LLM calls (latency + token counts), tool calls (per tool, per type, success/failure), memory operations, permission decisions, planner operations, and sub-agent lifecycle.
- **OpenTelemetry Distributed Tracing** (`Observability/tracing.py`): Every agent run, LLM call, and tool execution is wrapped in an OTel span. Traces are exported via OTLP/HTTP to **Grafana Tempo**.
- **Structured JSON Logging** (`Observability/logging.py`): A structured logger emits JSON records including `run_id`, `trace_id`, and `span_id` for log-trace correlation.
- **Lifecycle Hooks** (`Observability/hooks.py`): A single `ObservabilityHooks` interface decouples Prometheus/OTel logic from all agent components — agent, sub-agent, planner, LLM, tool, memory, and permission layers each call a hook without knowing the backend.
- **Perses Dashboards** (`deploy/perses/`): Pre-built dashboard resources visualizing the metrics above, connected to Prometheus.

### 9. Configurable LLM Backend & Polished CLI
- Works with any OpenAI-compatible API endpoint (InnKube, OpenAI, Ollama, vLLM, OpenRouter).
- Includes the **Dalanda AI** stylized ANSI color banner and interactive help command (`/help`).

---

## System Architecture

```text
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         Interactive CLI / User Terminal                     │
 │                              main.py / calandar-agent.py                    │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                                Agent Loop                                   │
 │                              agent/agent.py                                 │
 └──────┬────────────┬────────────┬────────────┬────────────┬───────────┬──────┘
        │            │            │            │            │           │
        ▼            ▼            ▼            ▼            ▼           ▼
 ┌────────────┐┌──────────────┐┌─────────┐┌──────────────┐┌──────────┐┌────────┐
 │  Planner   ││TaskScheduler ││MemoryMgr││  ToolRouter  ││ SubAgent ││CntxMgmt│
 │ & Thinking ││Dependency DAG││RAG/Embed││ Group Select ││Delegation││ Budget │
 └────────────┘└──────────────┘└─────────┘└──────────────┘└──────────┘└────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                              Execution Harness                              │
 │                             harness/harness.py                              │
 │                   [Permission Gate → Observability Hooks]                   │
 └──────────────────────┬───────────────────────────────┬──────────────────────┘
                        │                               │
                        ▼                               ▼
 ┌──────────────────────────────────────────┐   ┌──────────────────────────────┐
 │             Local Tool Registry          │   │         MCP Manager          │
 │              tools/registry.py           │   │    mcp_client/manager.py     │
 ├───────────────────┬──────────────────────┤   ├──────────────┬───────────────┤
 │  filesystem.py    │   ocr_classifier.py  │   │   Exa MCP    │  Notion MCP   │
 │  - list_files     │   - extract_classify │   │  (Search)    │  (OAuth/Work) │
 │  - read_file      │   - folder_classify  │   ├──────────────┼───────────────┤
 │  - create_file    │   tools/memory.py    │   │  Email MCP   │  Google Cal   │
 │  - update_file    │   - save/get/delete  │   │  (Uvicorn)   │  (Stdio/uvx)  │
 │  - search_files   │   ScheduleTool.py    │   └──────────────┴───────────────┘
 └───────────────────┴──────────────────────┘
                        │
                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                          Observability Stack                                │
 │   Prometheus metrics ──► Perses dashboards  (port 8080)                    │
 │   OpenTelemetry spans ──► Grafana Tempo     (port 3200)                    │
 │   Structured JSON logs (stdout, log-trace correlated)                      │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

| Component | File Path | Responsibilities |
| :--- | :--- | :--- |
| **Agent Core** | [`agent-harness/agent/agent.py`](agent-harness/agent/agent.py) | Coordinates the main ReAct loop, combines local + MCP tools, enforces prompt/context token limits, dispatches scheduled task batches and sub-agents. |
| **Planner & Thinking** | [`agent-harness/agent/planner.py`](agent-harness/agent/planner.py) | Generates visible execution plans and decomposes multi-step goals into a dependency graph of tasks. |
| **Task Scheduler** | [`agent-harness/agent/task_scheduler/scheduler.py`](agent-harness/agent/task_scheduler/scheduler.py) | Dependency-aware task graph: tracks per-task status and exposes which tasks are ready to run. |
| **Memory Manager** | [`agent-harness/agent/memory.py`](agent-harness/agent/memory.py) | Combines semantic persistent memory retrieval, session history, and token-budget-aware context compaction. |
| **Semantic Embeddings** | [`agent-harness/agent/memory_embedding.py`](agent-harness/agent/memory_embedding.py) | Computes sentence embeddings (`all-MiniLM-L6-v2`) and calculates cosine similarity for memory retrieval. |
| **Sub-Agent** | [`agent-harness/agent/subagent.py`](agent-harness/agent/subagent.py) | Runs an isolated delegated task in its own ReAct loop with a scoped tool set, independent budget, and full observability. |
| **Context / Token Budget** | [`agent-harness/CntxMgmt/budget.py`](agent-harness/CntxMgmt/budget.py) | Real-tokenizer-based token counting and budget calculation used to size tool schemas, history, and summaries against the model's context window. |
| **Execution Harness** | [`agent-harness/harness/harness.py`](agent-harness/harness/harness.py) | Permission-gated, observable tool dispatcher routing calls between local functions, the task scheduler, and MCP clients. |
| **Tool Router** | [`agent-harness/tools/router.py`](agent-harness/tools/router.py) | Keyword-based selection of relevant tool groups per task to minimise model context noise. |
| **Permission Manager** | [`agent-harness/permissions/manager.py`](agent-harness/permissions/manager.py) | Classifies every tool call as read/write/delete, applies allow/confirm/deny policies from `config/permissions.json`, and supports switchable runtime permission modes. |
| **MCP Manager** | [`agent-harness/mcp_client/manager.py`](agent-harness/mcp_client/manager.py) | Manages lifecycle, tool discovery, and routing for Exa, Notion, Email, and Google Calendar servers. |
| **Generic MCP Client** | [`agent-harness/mcp_client/client.py`](agent-harness/mcp_client/client.py) | Transport-agnostic client supporting both Streamable HTTP (with OAuth) and Stdio transports. |
| **Email MCP Server** | [`agent-harness/mcp_servers/email_server.py`](agent-harness/mcp_servers/email_server.py) | Custom-built local MCP server providing `write_email` (drafting) and `send_email` (SMTP delivery). |
| **Filesystem Tools** | [`agent-harness/tools/filesystem.py`](agent-harness/tools/filesystem.py) | Sandboxed directory and file manipulation routines strictly bounded by `safe_path()`. |
| **OCR & Classification** | [`agent-harness/tools/ocr_classifier.py`](agent-harness/tools/ocr_classifier.py) | Offline document text extraction (Tesseract, PyPDF) and rule-based keyword categorization. |
| **Observability Hooks** | [`agent-harness/Observability/hooks.py`](agent-harness/Observability/hooks.py) | Central lifecycle hook interface updating Prometheus metrics and structured logs for every agent component. |
| **Prometheus Metrics** | [`agent-harness/Observability/metrics.py`](agent-harness/Observability/metrics.py) | Defines all counters, gauges, and histograms for agent, LLM, tool, memory, permission, planner, and sub-agent events. |
| **OTel Tracing** | [`agent-harness/Observability/tracing.py`](agent-harness/Observability/tracing.py) | Bootstraps the OpenTelemetry SDK and provides `traced_span()` context manager; exports via OTLP/HTTP to Tempo. |

---

## Project Directory Structure

```text
group-1/
├── README.md                          # This overview document
├── daily_reports/                     # Student daily engineering reports
│
└── agent-harness/
    ├── Dockerfile                     # Container image definition (Python 3.12, Tesseract, Poppler, uv)
    ├── docker-compose.yml             # Multi-service stack: agent + Prometheus + Tempo + Perses
    ├── README.md                      # Docker setup & run guide
    ├── requirements.txt               # Python package dependencies
    ├── main.py                        # Interactive agent CLI entrypoint
    ├── calandar-agent.py              # Dedicated Google Calendar CLI agent
    ├── dalanda_banner.py              # Stylized CLI splash screen
    │
    ├── agent/
    │   ├── agent.py                   # Main ReAct Agent — orchestrates planning, memory, tools, sub-agents
    │   ├── planner.py                 # Plan generation & dependency-graph task decomposition
    │   ├── memory.py                  # Dual-layer memory & token-budget-aware context compactor
    │   ├── memory_embedding.py        # Sentence-Transformers semantic search
    │   ├── prompts.py                 # System and planner prompt templates
    │   ├── subagent.py                # Sub-agent implementation & SubAgentRequest dataclass
    │   └── task_scheduler/
    │       ├── __init__.py
    │       └── scheduler.py           # Dependency-aware task graph scheduler
    │
    ├── CntxMgmt/
    │   └── budget.py                  # Token counting & context-window budget calculations
    │
    ├── config/
    │   ├── config.json                # Runtime configuration overrides (model, temperature)
    │   ├── mcp.json                   # Local MCP server process definitions
    │   ├── permissions.json           # Per-tool permission policies (allow/confirm/deny)
    │   └── settings.py                # Environment variable loader (incl. OTEL_* settings)
    │
    ├── harness/
    │   └── harness.py                 # Permission-gated, observed tool execution engine
    │
    ├── mcp_client/
    │   ├── __init__.py
    │   ├── client.py                  # Generic MCP Client (HTTP / Stdio)
    │   ├── config.py                  # Server URLs, OAuth config, Stdio params
    │   ├── manager.py                 # Multi-server MCP manager & router
    │   ├── server_process.py          # Background Uvicorn process manager
    │   └── storage.py                 # Persistent file-based OAuth token store
    │
    ├── mcp_servers/
    │   └── email_server.py            # Custom-built Streamable HTTP Email MCP service
    │
    ├── tools/
    │   ├── __init__.py
    │   ├── definitions.py             # OpenAI-format tool JSON schemas (incl. delegate_to_subagent)
    │   ├── filesystem.py              # Sandboxed file/folder manipulation
    │   ├── memory.py                  # Memory CRUD & vector sync
    │   ├── ocr_classifier.py          # Tesseract OCR & document classifier
    │   ├── registry.py                # Local function mapping table
    │   ├── router.py                  # Keyword-based tool group selector
    │   └── ScheduleTool.py            # Follow-up scheduling tool schema
    │
    ├── permissions/
    │   ├── __init__.py
    │   └── manager.py                 # PermissionManager: classify & gate every tool call, runtime modes
    │
    ├── Observability/
    │   ├── hooks.py                   # ObservabilityHooks: central lifecycle interface
    │   ├── metrics.py                 # Prometheus counters, gauges & histograms
    │   ├── tracing.py                 # OpenTelemetry bootstrap & traced_span() helper
    │   └── logging.py                 # StructuredLogger: JSON log records with trace correlation
    │
    ├── prometheus/
    │   └── prometheus.yml             # Prometheus scrape configuration
    │
    ├── deploy/
    │   ├── perses/                    # Perses server config & pre-built dashboard resources
    │   └── tempo/                     # Grafana Tempo configuration
    │
    ├── docs/
    │   └── OBSERVABILITY.md           # Full observability setup & dashboard guide
    │
    ├── tests/
    │   ├── run_tests.py               # Test runner & discovery
    │   ├── test_filesystem.py         # Sandboxing & path safety tests
    │   ├── test_memory.py             # Long-term memory & semantic tests
    │   ├── test_harness.py            # Harness execution & safety limits
    │   ├── test_ocr_classifier.py     # OCR & classification pipeline tests
    │   ├── test_agenda_e2e.py         # Google Calendar agenda E2E tests
    │   ├── test_e2e_scenarios.py      # End-to-end multi-step scenario tests
    │   ├── test_e2e.py                # Full-agent end-to-end test
    │   ├── test_email_e2e.py          # Email MCP E2E tests
    │   ├── test_exa_tools.py          # Exa MCP tool discovery script
    │   ├── test_CntxMgmt.py           # Token/context budget calculation tests
    │   ├── test_Compaction.py         # Memory compaction tests
    │   ├── test_ReActLLM.py           # ReAct loop test
    │   ├── test_obs.py                # Observability hooks & metrics tests
    │   └── e2e/                       # Shared fixtures for end-to-end tests
    │
    └── workspace/                     # Sandboxed agent working directory
        ├── incoming/                  # Incoming raw files / documents
        ├── notes/                     # Workspace notes
        ├── organizer/                 # memory.json & memory_embeddings.json
        ├── output/                    # Generated output files
        └── results/                   # Classification reports (CSV / XLSX)
```

> [!NOTE]
> `mcp_client/notion_oauth.json` and `.gcp-saved-tokens.json` store runtime OAuth session tokens and are excluded from version control via `.gitignore`.

---

## Prerequisites & Requirements

1. **Python 3.12+**
2. **Tesseract OCR**:
   - **Windows**: Install [Tesseract-OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki) and ensure `tesseract.exe` is added to your system `PATH`.
   - **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
   - **macOS**: `brew install tesseract`
3. **Poppler Utilities** (Required for PDF-to-image OCR rendering):
   - **Ubuntu/Debian**: `sudo apt-get install poppler-utils`
   - **macOS**: `brew install poppler`
   - **Windows**: Install via Conda (`conda install -c conda-forge poppler`) or download Windows binaries and add `bin/` to `PATH`.
4. **uv / uvx** (Required for the Google Calendar MCP server):
   - Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`
5. **Docker Desktop** (Required for the full stack including observability services).

---

## Installation & Setup

### 1. Clone & Navigate
```bash
git clone https://github.com/aie/group-1.git
cd "group-1/agent-harness"
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
```

- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Linux / macOS**:
  ```bash
  source .venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Configuration & Environment Variables

Create a `.env` file in the `agent-harness/` directory:

```env
# ==========================================
# LLM Endpoint Configuration
# ==========================================
INNKUBE_API_KEY="your-api-key-here"
INNKUBE_BASE_URL="https://your-llm-endpoint.com/v1"
INNKUBE_MODEL="qwen-agentworld-35b-a3b"
INNKUBE_TEMPERATURE="0.2"

# ==========================================
# Hugging Face (Sentence-Transformers Embeddings
# + tokenizer used for context/token budgeting)
# ==========================================
HF_TOKEN="hf_your_token_here"

# ==========================================
# Exa MCP (Web Search)
# ==========================================
EXA_API_KEY="your-exa-api-key-here"

# ==========================================
# Email MCP Server (SMTP Settings)
# ==========================================
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"
EMAIL_FROM="your-email@gmail.com"

# ==========================================
# Google Calendar MCP (Agenda)
# ==========================================
GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
TOKEN_FILE_PATH=".gcp-saved-tokens.json"

# ==========================================
# Observability (OpenTelemetry)
# ==========================================
OTEL_ENABLED="true"
OTEL_SERVICE_NAME="agent-harness"
OTEL_ENVIRONMENT="local"
OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
```

### Local LLM Alternative (Ollama / vLLM)
To use a local model via Ollama:
```env
INNKUBE_API_KEY="ollama"
INNKUBE_BASE_URL="http://localhost:11434/v1"
INNKUBE_MODEL="qwen2.5:32b"
INNKUBE_TEMPERATURE="0.2"
```

> [!NOTE]
> The token/context budget calculations in `CntxMgmt/budget.py` load a tokenizer matching the configured model. If you switch `INNKUBE_MODEL` to a different model family, update the tokenizer name accordingly so token counts stay accurate.

---

## How to Run the Agent

### 1. Main Interactive Assistant
Runs the full Dalanda agent with all local tools, automatic background Email MCP process, Notion MCP, Exa search, and Google Calendar integrations:
```bash
python main.py
```

<!-- ### 2. Standalone Google Calendar Agent -->
<!-- Runs a focused Calendar/Agenda agent interface: -->
<!-- ```bash

```

--- -->

## Interactive CLI Commands & Prompts

### Session Commands
- `/help` — Display list of available commands and all currently active local, scheduler, and MCP tools.
- `/reset` — Clear short-term conversation turns while preserving persistent long-term memory.
- `/mode [name]` — Show the current permission mode and all available modes, or switch to one (`default`, `auto`, `bypass`). Switching to `bypass` requires re-typing `bypass` to confirm.
- `/exit` or `/quit` — Gracefully disconnect all MCP clients and shut down local microservices.

### Example Prompts & Use Cases

#### 1. Autonomous Planning & Parallel Task Execution
```text
You: Analyze the incoming files, extract and classify any receipts found, and write a summary report into results/summary.md.
```
*The agent decomposes this into a dependency graph of subtasks, runs independent ones concurrently as sub-agents, then continues reasoning over the combined results to produce the final report.*

#### 2. Sub-Agent Delegation
```text
You: Search the web for AI agent frameworks and summarize findings, while simultaneously organizing my workspace files.
```
*The agent delegates independent tasks to specialized sub-agents — one for web research via Exa, one for filesystem operations — then merges their results.*

#### 3. Semantic Memory & Personalization
```text
You: Remember that I prefer financial reports in EUR currency and Markdown table format.
You: What were my preferences for generating reports?
```
*The agent stores the memory with semantic embeddings and retrieves it automatically whenever relevant financial or reporting queries arise.*

#### 4. Workspace Filesystem & Document OCR
```text
You: Scan the workspace/incoming folder for PDFs and images and categorize them into results/classification.csv.
You: Read the extracted text from notes/meeting.txt and search for any action items.
```

#### 5. Web Search via Exa MCP
```text
You: Search the web for the latest updates on Model Context Protocol specification in 2026.
```

#### 6. Notion Integration via MCP
```text
You: List all pages in my Notion workspace and retrieve the contents of the Project Roadmap page.
```

#### 7. Email Drafting & Sending via Local Email MCP
```text
You: Draft an email to team@company.com with the subject "Weekly Status Update" summarizing our project milestones.
You: Send the email draft to supervisor@company.com with subject "Milestone 2 Completed".
```

#### 8. Google Calendar Management
```text
You: Check my schedule for tomorrow and list all upcoming meetings.
You: Schedule a meeting titled "Sprint Review" on 2026-09-15 from 10:00 to 11:00 UTC.
```

#### 9. Switching Permission Mode
```text
You: /mode auto
```
*Writes now execute without a confirmation prompt for the rest of the session (or until switched back); deletes still require confirmation.*

---

## Model Context Protocol (MCP) Integrations

Dalanda AI uses a modular multi-client MCP architecture:

```text
               ┌────────────────────────────────────────────────────────┐
               │                  MCPManager (manager.py)               │
               └────────┬──────────────┬──────────────┬──────────────┬──┘
                        │              │              │              │
           ┌────────────┘              │              │              └────────────┐
           ▼                           ▼              ▼                           ▼
    ┌──────────────┐            ┌──────────────┐ ┌──────────────┐          ┌──────────────┐
    │   Exa MCP    │            │  Notion MCP  │ │  Email MCP   │          │  Google Cal  │
    │ (Streamable) │            │ (OAuth HTTP) │ │(Uvicorn HTTP)│          │ (Stdio/uvx)  │
    └──────────────┘            └──────────────┘ └──────────────┘          └──────────────┘
```

1. **Dynamic Tool Discovery**: At startup, `MCPManager.connect_all()` initializes all configured clients, queries `list_tools()`, and converts server schemas into OpenAI function calling definitions (`TOOLS + mcp_tools`).
2. **Transparent Tool Routing**: When the LLM calls an MCP tool (e.g. an Exa search tool, `notion-get-users`, `write_email`, `list_events`), the `Harness` delegates execution directly to `MCPManager.call_tool()`, routing to the responsible server without exposing credentials to the model.
3. **Background Process Management**: Local MCP servers (such as `mcp_servers/email_server.py`) are automatically managed via `MCPServerProcess` using subprocess lifecycle management.

> [!NOTE]
> This project previously integrated web search through **Tavily**. That integration has been fully replaced by **Exa** — the Tavily client is disabled in code, and this document no longer describes it as an active integration.

---

## Tool Capabilities & Registry

### Local Tools (`tools/registry.py`)

| Tool Name | Module | Parameters | Description |
| :--- | :--- | :--- | :--- |
| `list_files` | `filesystem.py` | `path` | Lists files and directories within the sandboxed workspace. |
| `read_file` | `filesystem.py` | `path` | Reads UTF-8 content from a workspace file. |
| `create_folder` | `filesystem.py` | `path` | Creates a new directory within the workspace. |
| `create_file` | `filesystem.py` | `path`, `content` | Creates a file with specified text content. |
| `update_file` | `filesystem.py` | `path`, `content` | Replaces the content of an existing workspace file. |
| `search_files` | `filesystem.py` | `query`, `path` | Performs case-insensitive recursive substring search across workspace files. |
| `extract_and_classify_document` | `ocr_classifier.py` | `source_path`, `csv_output_path`, `xlsx_output_path`, `classification_rules` | Extracts text from TXT/PDF/image and classifies document into categories. |
| `extract_and_classify_folder` | `ocr_classifier.py` | `source_directory`, `csv_output_path`, `xlsx_output_path`, `recursive`, `max_files` | Batch classifies all supported files in a directory into a CSV/XLSX report. |
| `save_memory` | `memory.py` | `category`, `key`, `value`, `tags` | Saves long-term memory entry and generates semantic vector embedding. |
| `get_memories` | `memory.py` | `category`, `query` | Retrieves stored long-term memory records. |
| `delete_memory` | `memory.py` | `category`, `key` | Deletes a stored long-term memory entry (denied by default policy — see [Permission System](#permission-system)). |
| `schedule_followup` | `ScheduleTool.py` | `task` | Adds a follow-up task to the agent's execution queue. |
| `delegate_to_subagent` | `definitions.py` | `task`, `role`, `instructions`, `context`, `max_tool_calls` | Spawns a specialized sub-agent to execute a delegated task. |

### Dynamic MCP Tools

| Server | Transport | Capabilities |
| :--- | :--- | :--- |
| **Exa** | Streamable HTTP | Live web search, content retrieval, source extraction. |
| **Notion** | Streamable HTTP + OAuth | Access and modify Notion workspace databases and documents. |
| **Email** | Local HTTP (Uvicorn) | Validated email drafting (`write_email`) and authenticated SMTP sending (`send_email`). |
| **Google Calendar** | Stdio (`uvx`) | Google Agenda event querying, scheduling, and management. |

> [!TIP]
> The exact tool names each MCP server exposes are discovered at runtime (`MCPManager.get_tool_definitions()`), not hardcoded — use `/help` after starting the agent to see the live list.

---

## Sub-Agent Delegation & Task Scheduling

The agent can delegate work to `SubAgent` instances in two ways:

1. **Ad hoc delegation** — the model calls `delegate_to_subagent` directly mid-conversation, per deterministic rules in the system prompt (e.g. web research, document processing, code/project analysis, or organization tasks).
2. **Scheduled delegation** — when the `Planner` decomposes a request into a dependency graph, `Agent.run_scheduled_tasks()` automatically runs each batch of ready tasks as sub-agents, concurrently, via `asyncio.gather`:

```text
 Parent Agent
     │
     │ Planner.create_task_plan() → dependency graph of tasks
     ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  TaskScheduler (agent/task_scheduler/scheduler.py)            │
 │  - Tracks each task's status (pending/completed/failed)      │
 │  - get_ready_tasks(): tasks whose dependencies are done       │
 └───────────────────────────┬────────────────────────────────────┘
                             │ batch of ready tasks
                             ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  asyncio.gather(*subagents)  — runs the batch concurrently    │
 │  Each SubAgent (agent/subagent.py):                           │
 │  - Unique run_id + parent_run_id link                        │
 │  - ToolRouter selects only task-relevant tools                │
 │  - Independent tool-call budget (default: 10)                │
 │  - Full ObservabilityHooks instrumentation                    │
 └──────────────────────────────────────────────────────────────┘
                             │
                             ▼
        Results are merged back into the parent's conversation,
        which then continues reasoning in its own ReAct loop.
```

Tasks with no shared dependencies run in the same parallel batch; tasks that depend on others wait until their dependencies are marked completed — so a single request can mix parallel and sequential execution as needed. Sub-agents always share the same `Harness` and `MCPManager` as the parent, so they benefit from the same permission gate, observability, and MCP connections without duplication.

---

## Tool Router

`ToolRouter` (`tools/router.py`) prevents the model from being overwhelmed with irrelevant tools by selecting only the groups needed for the current task:

| Group | Tools Included | Activated by keywords |
| :--- | :--- | :--- |
| `filesystem` | `list_files`, `read_file`, `create_file`, `update_file`, `search_files`, `extract_*` | file, folder, document, workspace |
| `memory` | `save_memory`, `get_memories`, `delete_memory` | memory, remember, saved, stored |
| `scheduler` | `schedule_followup` | remind, schedule, follow-up, later |
| `web` | Exa MCP tools | search, research, find, web, url, arxiv |
| `notion` | Notion MCP tools | notion, page, database |
| `email` | Email MCP tools | email, mail, send |
| `calendar` | Google Calendar MCP tools | calendar, event, meeting, appointment |
| `delegation` | `delegate_to_subagent` | (always available to the parent agent) |

---

## Context & Token Budget Management

`CntxMgmt/budget.py` makes context management token-accurate rather than turn-count-only, by loading the real tokenizer for the configured model:

1. **Oversized-prompt rejection**: a user message larger than `MAX_USER_PROMPT_TOKENS` is rejected immediately.
2. **Tool-schema-aware budgeting**: before building the prompt, `get_message_token_budget()` counts the token cost of the currently-selected tool schemas and subtracts it from the model's usable input window, giving the true remaining budget for conversation history.
3. **Compaction trigger**: `MemoryManager.compact()` fires whenever stored history exceeds that budget, **or** whenever more than `COMPACTION_TRIGGER_TURNS` (12) turns have accumulated — whichever happens first — summarizing older turns into a bounded, structured summary (reserving a configurable fraction of the older turns' token size, `SUMMARY_COMPRESSION_RATIO`, for the summary itself) and keeping only as many recent turns as still fit.
4. **Request-level guardrail**: immediately before every LLM call, the fully-assembled request (system prompt + memory + history + current turn + tool schemas) is measured again; if it would still exceed the model's input limit, the agent stops itself with a clear message rather than sending an oversized request.

This keeps long-running sessions and large tool catalogs from silently overflowing the model's context window.

---

## Permission System

Every tool call passes through `PermissionManager` before execution:

```text
Tool Call Request
       │
       ▼
 ┌─────────────────────────────────┐
 │      PermissionManager          │
 │  1. Check explicit policy       │  ← config/permissions.json (always wins)
 │  2. Classify action type        │  ← read / write / delete
 │  3. Apply decision for the      │  ← depends on the active mode
 │     current permission mode     │
 └────────┬────────────────────────┘
          │
    ┌─────┴──────────────────┐
    │                        │
    ▼                        ▼
 ALLOW                 REQUIRE_USER_CONFIRMATION / DENY
 (proceed)             (prompt user or block)
```

### Runtime Permission Modes

Switchable at any point in the conversation via `/mode <name>` (human-only — the model can never change its own permission mode):

| Mode | Read | Write | Delete |
| :--- | :--- | :--- | :--- |
| `default` | Allow | Require confirmation | Require confirmation |
| `auto` | Allow | Allow | Require confirmation |
| `bypass` | Allow | Allow | Allow |

Explicit per-tool policies in `config/permissions.json` (e.g. `delete_memory → Deny`) always take precedence over the active mode, in every mode — including `bypass`. Switching into `bypass` requires re-typing `bypass` at a warning prompt, since it removes the last safety net.

---

## Observability Stack

The full observability stack runs as Docker Compose services alongside the agent:

| Service | Image | Port | Purpose |
| :--- | :--- | :--- | :--- |
| **agent** | `dalanda-agent` (local build) | `8001` | Agent + Prometheus `/metrics` endpoint |
| **prometheus** | `prom/prometheus:v3.0.1` | `9090` | Metrics scraping & storage |
| **tempo** | `grafana/tempo:2.6.1` | `3200` / `4317` / `4318` | Distributed trace storage (OTLP gRPC + HTTP) |
| **perses** | `persesdev/perses:v0.50.1` | `8080` | Dashboard UI (reads from Prometheus) |

### Metrics Tracked

| Category | Metrics |
| :--- | :--- |
| **Agent** | `agent_runs_total`, `agent_active_runs`, `agent_run_duration_seconds`, `agent_run_failures_total` |
| **LLM** | `llm_calls_total`, `llm_call_duration_seconds`, `llm_input_tokens_total`, `llm_output_tokens_total`, `llm_errors_total` |
| **Tools** | `tool_calls_total`, `tool_call_duration_seconds`, `tool_success_total`, `tool_failure_total` |
| **Memory** | `memory_operations_total`, `memory_retrieval_duration_seconds` |
| **Permissions** | `permission_decisions_total`, `permission_check_duration_seconds` |
| **Planner** | `planner_duration_seconds`, `planner_errors_total` |
| **Sub-Agents** | `subagent_runs_total`, `subagent_active_runs`, `subagent_run_duration_seconds`, `subagent_failures_total` |

> [!TIP]
> See [`agent-harness/docs/OBSERVABILITY.md`](agent-harness/docs/OBSERVABILITY.md) for the full setup guide and dashboard walkthrough.

---

## Security & Sandboxing Architecture

1. **Strict Path Sandboxing (`safe_path`)**:
   All filesystem interactions resolve paths relative to `workspace/`. Any attempt to traverse out of the workspace (e.g., `../../etc/passwd` or `..\Windows\System32`) raises a `PermissionError` and is safely caught by the Harness.
2. **No Deletion Operations on Files**:
   The local filesystem tool registry deliberately does not expose file/folder deletion tools, preventing destructive filesystem modifications.
3. **Turn & Prompt Execution Limits**:
   Tool executions per user turn are bounded (`MAX_TOOL_CALLS_PER_TURN = 20`), sub-agents have their own independent budget (default `10`), and oversized prompts/requests are rejected before or during processing (see [Context & Token Budget Management](#context--token-budget-management)).
4. **Credential Isolation**:
   API keys, OAuth tokens, and SMTP credentials remain strictly in environment variables or isolated local JSON files (`notion_oauth.json`, `.gcp-saved-tokens.json`), never injected into prompts or accessible to the model.
5. **Permission Gate with Human-Only Mode Control**:
   Every tool call — local or MCP — is intercepted by `PermissionManager` before execution. The active permission mode can only be changed by the human operator via `/mode`, never by the model itself.

---

## Automated Test Suite

The test suite covers local tools, memory, the permission/scheduler subsystems, context/token budgeting, and end-to-end agent workflows:

```bash
python tests/run_tests.py
```

### Test Coverage
- **`test_filesystem.py`**: Workspace isolation, relative path traversal prevention, file read/write/update/search.
- **`test_memory.py`**: Persistent memory storage, category isolation, vector embedding generation, query matching.
- **`test_Compaction.py`**: Context compaction behavior under the token-budget-aware compactor.
- **`test_CntxMgmt.py`**: Token counting and context-window budget calculations.
- **`test_harness.py`**: Local tool execution, error isolation, execution turn budget enforcement.
- **`test_ocr_classifier.py`**: Text extraction, PDF OCR, rule-based classification, CSV/Excel report output.
- **`test_agenda_e2e.py`**: Google Calendar MCP end-to-end scenarios (search, create, update, delete events).
- **`test_email_e2e.py`**: Email MCP drafting and sending end-to-end tests.
- **`test_e2e_scenarios.py`** / **`test_e2e.py`**: Multi-turn and full-agent end-to-end task automation.
- **`test_ReActLLM.py`**: Core ReAct loop behavior.
- **`test_obs.py`**: Observability hooks and Prometheus metric increments.

> [!NOTE]
> As with any actively-developed test suite, not every test passes on every commit — run `python tests/run_tests.py` (or `pytest agent-harness/tests`) locally to see the current pass/fail state before relying on it.

---

## Docker Deployment

The full stack is defined in `docker-compose.yml` and includes the agent, Prometheus, Grafana Tempo, and Perses dashboards.

### Build & Start

Run from the `agent-harness/` directory:

```bash
docker compose up --build
```

### Attach to the Agent

Once the stack is running, open a new terminal and attach to the interactive agent session:

```bash
docker attach agent-harness-agent-1
```

> [!NOTE]
> `agent-harness-agent-1` is the default container name generated by Docker Compose. Run `docker ps` to confirm the name if needed.

### Observability UIs (after stack is up)

| UI | URL |
| :--- | :--- |
| Prometheus | http://localhost:9090 |
| Perses Dashboards | http://localhost:8080 |
| Tempo (trace query API) | http://localhost:3200 |
| Agent metrics endpoint | http://localhost:8001/metrics |

- Workspace files, OAuth tokens, and memory are persisted via volume mounts defined in `docker-compose.yml` and survive container restarts.

---

## Academic & Engineering Highlights

- **Native Implementation**: Built without heavy black-box frameworks (like LangChain or AutoGen), providing transparent, fine-grained control over execution flow, memory boundaries, and error recovery.
- **Multi-Transport Model Context Protocol**: Implements both Streamable HTTP and Stdio MCP transports in a unified client manager with automated sub-process handling.
- **Hybrid Parallel/Sequential Sub-Agent Architecture**: Dependency-aware scheduling lets independent subtasks run concurrently while dependent ones wait their turn — all sub-agents run on the same shared `Harness` as the parent, so permissions and observability apply uniformly.
- **Semantic Vector-Augmented Memory (RAG)**: Integrates lightweight local embeddings (`all-MiniLM-L6-v2`) for targeted memory injection, keeping context concise while maintaining long-term personalization.
- **Token-Accurate Context Management**: Uses the model's real tokenizer to budget tool schemas, history, and summaries against the actual context window, with a hard request-level guardrail rather than best-effort truncation.
- **Runtime-Configurable Safety**: A human-only, switchable permission mode system layered on top of per-tool policies that always take precedence — letting an operator trade off friction vs. autonomy without ever letting the model grant itself more permission.
- **Production-Grade Observability**: A Prometheus + OpenTelemetry tracing + structured logging stack wired into every agent component lifecycle, with pre-built Perses dashboards — making the system's internal behavior inspectable without modifying application code.
