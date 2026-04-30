# Kinetic-Core

> **Autonomous Reliability Engineer (ARE) for Critical Power Systems**

An end-to-end agentic platform that manages the full lifecycle of a critical equipment failure — from the first anomalous "shiver" in sensor data to a validated, dispatched repair work order — without a human digging through a single database.

---

## The Problem

In critical infrastructure (data centers, hospitals, manufacturing plants), a power failure costs **$millions per minute**. Today's monitoring tools are **passive observers** — they show a chart, fire an alert, and wait for a human. The human then:

1. Searches through 200-page technical manuals
2. Queries the maintenance history database
3. Cross-checks safety protocols
4. Finally writes a work order — 45 minutes later

**Kinetic-Core collapses that 45 minutes to 45 seconds.**

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        KINETIC-CORE PLATFORM                       │
│                                                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────┐ │
│  │  IoT Layer   │    │  Data Layer  │    │    Knowledge Layer    │ │
│  │              │    │              │    │                       │ │
│  │ Azure IoT Hub│───▶│Azure Data    │    │  Azure AI Search      │ │
│  │ Event Grid   │    │Factory +     │───▶│  (Vector + BM25)      │ │
│  │ (Telemetry)  │    │Cosmos DB     │    │  PDF Manuals + SOPs   │ │
│  └──────────────┘    └──────────────┘    └───────────────────────┘ │
│          │                  │                       │               │
│          ▼                  ▼                       ▼               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   MULTI-AGENT CORE (Azure Functions)         │  │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐  │  │
│  │  │ Diagnostic Lead │  │Tech. Librarian   │  │Safety      │  │  │
│  │  │ (Anomaly + Root │─▶│(RAG: exact repair│─▶│Auditor     │  │  │
│  │  │  Cause Analysis)│  │ steps from PDFs) │  │(Protocol   │  │  │
│  │  └─────────────────┘  └──────────────────┘  │ Gate)      │  │  │
│  │           ▲                                  └────────────┘  │  │
│  │           │         Azure OpenAI GPT-4o                      │  │
│  │           │         (Reasoning Engine)                       │  │
│  └───────────┼──────────────────────────────────────────────────┘  │
│              │                                                      │
│  ┌──────────────────┐    ┌─────────────────────────────────────┐   │
│  │ Azure AI Studio  │    │  React Dashboard (Real-time)        │   │
│  │ Evaluations      │    │  Work Order Generation              │   │
│  │ Drift Monitoring │    │  Agent Reasoning Trace              │   │
│  └──────────────────┘    └─────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

---

## The "Architecture of Impact" — Full AI Spectrum

| Stage | Azure Data Component | Azure AI Component |
|---|---|---|
| **Ingestion** | IoT Hub + Event Grid | Edge anomaly detection (streaming) |
| **Processing** | Data Factory + Cosmos DB | Semantic chunking of industrial PDFs |
| **Knowledge** | AI Search (Vector Store) | Hybrid RAG (keyword + vector embeddings) |
| **Logic (Core)** | Azure OpenAI GPT-4o | Multi-Agent Orchestration |
| **Governance** | AI Studio Evaluations | Hallucination detection + drift monitoring |
| **CI/CD** | GitHub Actions + Bicep | Prompt versioning lifecycle |

---

## Target Scenario: Thermal Runaway in Data Center Cooling Rack

A gradual thermal escalation in a high-density server cooling rack — the kind a simple threshold would miss but an AI catches 4 hours early.

**The "Hidden Fault":** Coolant flow rate drops 8% over 6 hours due to a failing pump seal. Temperature rises non-linearly. Vibration signature shifts. A naive alert fires only when the thermal limit is breached. **Kinetic-Core detects it at hour 2, identifies the fault code, finds the repair procedure in the manual, validates against safety protocol (voltage check), and dispatches a work order for the next maintenance window.**

---

## Multi-Agent Personas

### Agent 1: The Diagnostic Lead
- **Role:** Data Scientist / Anomaly Analyst
- **Input:** Live telemetry stream (temperature, voltage, vibration, coolant flow)
- **Output:** Fault classification, severity score, root cause hypothesis
- **Model:** GPT-4o with structured outputs + time-series context

### Agent 2: The Technical Librarian
- **Role:** RAG Specialist
- **Input:** Fault code from Diagnostic Lead
- **Output:** Exact repair procedure, parts list, estimated duration
- **Retrieval:** Hybrid search (BM25 + Ada-002 embeddings) over PDF manuals

### Agent 3: The Safety Auditor
- **Role:** Senior Safety Engineer (Adversarial)
- **Input:** Proposed repair procedure + live voltage/current readings
- **Output:** GO / NO-GO decision with safety justification
- **Rule:** Cannot approve hot-swap if voltage > 480V or arc flash risk detected

### Agent 4: The Orchestrator
- **Role:** Operations Coordinator
- **Input:** Approved repair plan
- **Output:** Formatted work order, technician assignment, parts requisition
- **Integration:** Cosmos DB memory, Azure Communication Services

---

## Repository Structure

```
kinetic-core/
├── agents/                     # Multi-agent system
│   ├── diagnostic_lead/        # Anomaly detection + root cause
│   ├── technical_librarian/    # RAG-powered repair lookup
│   ├── safety_auditor/         # Safety protocol enforcement
│   └── orchestrator/           # Multi-agent coordination
├── api/                        # FastAPI backend
│   ├── routers/                # Event, agent, workorder endpoints
│   ├── models/                 # Pydantic schemas
│   └── middleware/             # Auth, logging, rate limiting
├── data/
│   ├── schemas/                # JSON schemas for telemetry & logs
│   ├── synthetic/
│   │   ├── telemetry/          # IoT data generator (with hidden fault)
│   │   ├── logs/               # SQL maintenance history seeder
│   │   └── manuals/            # Technical manual content
├── docs/
│   ├── architecture/           # System design docs + Mermaid diagrams
│   ├── adr/                    # Architecture Decision Records
│   └── runbooks/               # Operational runbooks
├── infra/
│   ├── bicep/                  # Azure IaC (IoT Hub, AI Search, OpenAI...)
│   └── scripts/                # Deployment automation
├── ingestion/
│   ├── iot_simulator/          # Publishes synthetic telemetry to IoT Hub
│   └── event_processor/        # Azure Function: IoT Hub → Cosmos DB
├── knowledge/
│   ├── chunker/                # Semantic PDF chunking
│   ├── embedder/               # Azure OpenAI Ada-002 embedding pipeline
│   └── indexer/                # AI Search index management
├── monitoring/
│   ├── drift/                  # Model drift detection
│   └── evaluation/             # AI Studio evaluation harness
├── prompts/
│   ├── versions/               # Versioned prompt snapshots (v1.0, v1.1...)
│   └── templates/              # Jinja2 prompt templates
├── frontend/                   # React dashboard
├── notebooks/                  # EDA, fault analysis, RAG evaluation
├── tests/                      # Unit, integration, e2e
└── .github/workflows/          # CI/CD pipelines
```

---

## Quick Start

### Prerequisites

- Azure CLI (`az login`)
- Python 3.11+
- Node.js 20+
- Docker (for local dev)

### 1. Clone & Configure

```bash
git clone https://github.com/vipul9811kumar/Kinetic-Core.git
cd Kinetic-Core
cp .env.template .env
# Fill in your Azure resource values
```

### 2. Deploy Azure Infrastructure

```bash
cd infra/bicep
az deployment group create \
  --resource-group kinetic-core-rg \
  --template-file main/main.bicep \
  --parameters @main/parameters.prod.json
```

### 3. Install & Run Backend

```bash
pip install -e ".[dev]"
python data/synthetic/telemetry/generator.py  # seed synthetic data
python knowledge/indexer/indexer.py           # build AI Search index
uvicorn api.main:app --reload
```

### 4. Run the Agents

```bash
python agents/orchestrator/orchestrator.py --scenario thermal_runaway
```

### 5. Start Frontend

```bash
cd frontend
npm install && npm run dev
```

---

## Azure Resources Deployed

| Resource | SKU | Purpose |
|---|---|---|
| Azure IoT Hub | S1 | Telemetry ingestion from sensors |
| Azure Event Grid | Standard | Event routing IoT → Functions |
| Azure Data Factory | Standard | Batch orchestration of historical data |
| Azure Cosmos DB | Serverless | Agent memory + operational logs |
| Azure OpenAI | GPT-4o + Ada-002 | Reasoning engine + embeddings |
| Azure AI Search | Standard | Hybrid RAG vector store |
| Azure Functions | Consumption | Agent hosting (serverless) |
| Azure Container Registry | Basic | Agent container images |
| Azure AI Studio | Standard | Evaluation + drift monitoring |
| Azure Monitor | Standard | Observability + alerting |
| Azure Key Vault | Standard | Secret management |

---

## Key Design Decisions

- **Adversarial Reasoning:** Safety Auditor is explicitly designed to _reject_ the Diagnostic Lead's recommendation if safety thresholds are violated. This prevents the classic "optimization at the expense of safety" failure mode.
- **Hybrid RAG:** Pure vector search misses exact repair codes (e.g., "KX-T2209-B"); pure BM25 misses semantic context. Hybrid combines both.
- **Prompt Versioning:** Every prompt change is committed to `prompts/versions/` and evaluated against a golden test set before deployment.
- **Cosmos DB Agent Memory:** Each agent writes its reasoning trace to Cosmos DB. The orchestrator can replay any incident for audit or retraining.
- **Edge Filtering:** A lightweight statistical model at the IoT Hub level (Azure Stream Analytics) pre-filters noise before GPT-4o is invoked — controlling cost.

---

## Governance & Evaluation

**Hallucination Guard:** Every repair step recommended by the Librarian is scored against the source document using GPT-4o with citation validation. Steps with < 0.85 faithfulness score are flagged.

**Drift Monitor:** Weekly batch job compares current anomaly detection accuracy against the baseline golden set. If F1 drops > 5%, a Slack alert fires and a retraining job is triggered.

**Prompt Registry:** Every production prompt has a version ID, evaluation score, and deployment timestamp stored in Cosmos DB.

---

## License

MIT

---

*Built to demonstrate enterprise-grade autonomous AI for critical infrastructure. Every component maps to a real-world production pattern used by Fortune 500 operations teams.*
