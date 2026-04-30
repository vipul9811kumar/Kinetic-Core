# Kinetic-Core — System Architecture

## 1. High-Level System Flow

```mermaid
flowchart TD
    subgraph EDGE["Edge / Field Layer"]
        SENSOR[Industrial Sensors\nTemp · Voltage · Vibration · Flow]
        SIM[IoT Simulator\niot_simulator.py]
    end

    subgraph INGEST["Ingestion Layer — Azure"]
        IOTHUB[Azure IoT Hub\nS1 Tier]
        EG[Azure Event Grid\nTopic: telemetry-events]
        SA[Azure Stream Analytics\nEdge Anomaly Filter]
    end

    subgraph STORE["Storage & Processing Layer — Azure"]
        COSMOS[Azure Cosmos DB\nContainers: telemetry · incidents · agent-memory]
        ADF[Azure Data Factory\nPipeline: cold-batch-ingest]
        BLOB[Azure Blob Storage\nPDF Manuals · Historical CSVs]
    end

    subgraph KNOWLEDGE["Knowledge Layer — Azure"]
        CHUNKER[Semantic Chunker\nAzure Function]
        EMBED[Ada-002 Embedder\nAzure OpenAI]
        SEARCH[Azure AI Search\nHybrid Index: BM25 + Vector]
    end

    subgraph AGENTS["Multi-Agent Core — Azure Functions"]
        ORCH[Orchestrator Agent\norchestrator.py]
        DIAG[Diagnostic Lead\nAnomaly + Root Cause]
        LIB[Technical Librarian\nHybrid RAG]
        SAFE[Safety Auditor\nAdversarial Gate]
    end

    subgraph REASON["Reasoning Engine"]
        GPT4O[Azure OpenAI\nGPT-4o]
    end

    subgraph OUTPUT["Output Layer"]
        WO[Work Order Generator]
        NOTIFY[Azure Communication Services\nEmail · SMS · Teams]
        DASH[React Dashboard\nReal-time Incident View]
    end

    subgraph GOVERN["Governance Layer"]
        EVAL[Azure AI Studio\nEvaluations]
        DRIFT[Drift Detector\nWeekly Batch]
        PROM[Prompt Registry\nCosmos DB]
    end

    SENSOR --> SIM
    SIM --> IOTHUB
    IOTHUB --> EG
    EG --> SA
    SA --> COSMOS
    SA --> ORCH

    BLOB --> ADF
    ADF --> CHUNKER
    CHUNKER --> EMBED
    EMBED --> SEARCH

    ORCH --> DIAG
    DIAG --> GPT4O
    DIAG --> LIB
    LIB --> SEARCH
    LIB --> GPT4O
    LIB --> SAFE
    SAFE --> GPT4O
    SAFE --> WO
    WO --> NOTIFY
    WO --> DASH

    AGENTS --> COSMOS
    GPT4O --> EVAL
    EVAL --> DRIFT
    PROM --> AGENTS
```

---

## 2. Agent Interaction Sequence

```mermaid
sequenceDiagram
    participant S as Sensor Stream
    participant O as Orchestrator
    participant D as Diagnostic Lead
    participant L as Technical Librarian
    participant SA as Safety Auditor
    participant GPT as GPT-4o
    participant DB as Cosmos DB
    participant WO as Work Order

    S->>O: Telemetry event (temp=87°C, Δflow=-8%)
    O->>DB: Log incident_id: INC-2024-0847
    O->>D: Analyze telemetry window (last 2h)

    D->>GPT: [Diagnostic prompt v1.2] Classify anomaly
    GPT-->>D: FaultCode=KX-T2209-B, Severity=HIGH, Cause=pump_seal_degradation
    D->>DB: Write diagnostic trace

    D->>L: Lookup FaultCode KX-T2209-B
    L->>SA: Hybrid search → 3 candidate procedures
    Note over L: BM25 score + vector score → rerank
    L->>GPT: [Librarian prompt v1.1] Synthesize repair steps
    GPT-->>L: Steps 1-7, Parts: [P-2209, P-3301], ETA: 45min
    L->>DB: Write librarian trace

    L->>SA: Validate repair plan + live readings (V=420V)
    SA->>GPT: [Auditor prompt v1.0] Check safety constraints
    Note over SA: V=420V < 480V → arc flash risk: LOW
    GPT-->>SA: APPROVED — voltage within safe range
    SA->>DB: Write audit trace

    SA->>WO: Generate work order
    WO->>DB: Persist WO-2024-0847
    WO-->>O: Work order dispatched
    O-->>S: Incident resolved — 38 seconds elapsed
```

---

## 3. Data Flow Architecture

```mermaid
flowchart LR
    subgraph HOT["Hot Path (< 1 second)"]
        A1[IoT Hub] --> A2[Event Grid]
        A2 --> A3[Stream Analytics\nAnomaly Filter]
        A3 --> A4[Cosmos DB\ntelemetry container]
        A3 --> A5[Agent Trigger\nHTTP Function]
    end

    subgraph WARM["Warm Path (minutes)"]
        B1[Cosmos DB CDC] --> B2[Change Feed Processor]
        B2 --> B3[Incident Aggregator]
        B3 --> B4[AI Studio Eval]
    end

    subgraph COLD["Cold Path (daily/weekly)"]
        C1[Blob Storage\nArchived Telemetry] --> C2[Data Factory\nBatch Pipeline]
        C2 --> C3[Drift Detector]
        C3 --> C4[Retraining Trigger\nif F1 drops > 5%]
    end

    subgraph KNOWLEDGE_PATH["Knowledge Path (on-demand)"]
        D1[PDF Upload\nBlob Storage] --> D2[Semantic Chunker]
        D2 --> D3[Ada-002 Embedder]
        D3 --> D4[AI Search Index]
    end
```

---

## 4. Infrastructure Architecture

```mermaid
graph TB
    subgraph RG["Resource Group: kinetic-core-rg"]
        subgraph NET["VNet: kinetic-core-vnet"]
            subgraph FUNC_SUBNET["Subnet: functions"]
                FUNC[Azure Functions\nPlan: Consumption]
            end
            subgraph DATA_SUBNET["Subnet: data"]
                COSMOS2[Cosmos DB\nPrivate Endpoint]
                SEARCH2[AI Search\nPrivate Endpoint]
            end
        end

        IOT[IoT Hub S1]
        EG2[Event Grid]
        ADF2[Data Factory]
        OPENAI[Azure OpenAI\nGPT-4o + Ada-002]
        KV[Key Vault]
        ACR[Container Registry]
        MONITOR[Azure Monitor\n+ Log Analytics]
        AI_STUDIO[Azure AI Studio\nProject: kinetic-core]
    end

    IOT --> EG2
    EG2 --> FUNC
    FUNC --> COSMOS2
    FUNC --> SEARCH2
    FUNC --> OPENAI
    FUNC --> KV
    ADF2 --> SEARCH2
    OPENAI --> AI_STUDIO
    FUNC --> MONITOR
```

---

## 5. Hybrid RAG Architecture

```mermaid
flowchart TD
    Q[User Query\nor Fault Code] --> PRE[Query Pre-processor\nExpand acronyms · normalize fault codes]

    PRE --> BM25[BM25 Lexical Search\nKeyword match on fault codes]
    PRE --> VEC[Vector Search\nAda-002 semantic similarity]

    BM25 --> RR[Reciprocal Rank Fusion\nk=60]
    VEC --> RR

    RR --> TOP5[Top-5 Chunks]
    TOP5 --> GPT2[GPT-4o\nSynthesis + Citation]

    GPT2 --> CITE[Citation Validator\nFaithfulness ≥ 0.85]
    CITE --> OUT[Repair Procedure\nwith source references]
    CITE -->|score < 0.85| FLAG[Flagged for Human Review]
```

---

## 6. Prompt Versioning Lifecycle

```mermaid
gitGraph
   commit id: "v1.0 — baseline prompts"
   branch feature/diagnostic-v1.1
   commit id: "Add CoT for thermal faults"
   commit id: "Eval: F1 0.82 → 0.91"
   checkout main
   merge feature/diagnostic-v1.1 id: "v1.1 — diagnostic"
   branch feature/auditor-safety-gate
   commit id: "Strengthen voltage constraint"
   commit id: "Eval: false approval rate 0%"
   checkout main
   merge feature/auditor-safety-gate id: "v1.2 — safety hardened"
```

---

## 7. Security Architecture

| Layer | Control | Implementation |
|---|---|---|
| **Network** | Private endpoints for Cosmos DB + AI Search | VNet integration |
| **Identity** | Managed Identity for all Azure Functions | No stored credentials |
| **Secrets** | All API keys in Key Vault | Key Vault references in Function App settings |
| **Data** | Cosmos DB encryption at rest | Azure-managed keys (CMK roadmap) |
| **API** | JWT validation on all endpoints | Azure AD B2C |
| **Audit** | All agent reasoning traces stored immutably | Cosmos DB time-to-live disabled for audit container |

---

## 8. Scalability & Cost Model

| Load | IoT Messages/sec | Agent Invocations/day | Estimated Azure Cost/month |
|---|---|---|---|
| **Dev** | 1 | 50 | ~$85 |
| **Pilot (1 facility)** | 100 | 500 | ~$420 |
| **Production (10 facilities)** | 1,000 | 5,000 | ~$2,100 |
| **Enterprise (100 facilities)** | 10,000 | 50,000 | ~$9,800 |

*GPT-4o invocations dominate cost; Stream Analytics edge filter reduces agent calls by ~85%.*
