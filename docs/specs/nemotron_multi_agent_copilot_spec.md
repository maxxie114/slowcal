# Nemotron Multi-Agent Copilot Spec (DGX Spark) — SlowCal

**Doc owner:** Dhruv  
**Branch:** `dkp`  
**Last updated:** 2026-01-25  
**Primary goal:** Produce a trustworthy **closure-risk analysis + mitigation strategy** for SF small businesses by combining (1) deterministic ML risk scoring with (2) Nemotron-powered narrative + planning, using a multi-agent architecture.

---

## Table of Contents

1. [Context & Requirements](#1-context--requirements)
2. [Deployment Topology (DGX Spark)](#2-deployment-topology-dgx-spark)
3. [Data Sources (DataSF / Socrata)](#3-data-sources-datasf--socrata)
4. [System Architecture](#4-system-architecture)
5. [Agent Roster](#5-agent-roster)
6. [Tooling Layer](#6-tooling-layer)
7. [Output Schemas](#7-output-schemas)
8. [Implementation Guide](#8-implementation-guide)
9. [SoQL Templates](#9-soql-templates)
10. [Security & Privacy](#10-security--privacy)
11. [Testing & Quality](#11-testing--quality)
12. [Definition of Done](#12-definition-of-done)

---

## 1) Context & Requirements

### 1.1 Target User
Small business owner / operator in San Francisco who wants:
- "How risky is my business location in the next N months?"
- "Why (evidence), and what should I do next?"

### 1.2 System Requirements
| Requirement | Details |
|-------------|---------|
| **Runtime** | Local/on-prem on **DGX Spark** for model inference and privacy |
| **LLM Endpoint** | Nemotron via NVIDIA NIM with OpenAI-compatible endpoints |
| **Data Sources** | DataSF (Socrata SODA + SoQL) for all datasets |
| **Output Format** | Structured JSON (schema validated) + UI-friendly |

### 1.3 Non-Goals (Pilot)
- ❌ Do not replace the core closure-risk score with an LLM
- ❌ Do not hallucinate: every claim must map to an evidence reference
- ❌ No legal/financial advice without disclaimers

---

## 2) Deployment Topology (DGX Spark)

### 2.1 Nemotron Inference Service

```
┌─────────────────────────────────────────────────────────────┐
│                      DGX Spark                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            NVIDIA NIM Container                       │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │  Nemotron-4-340B-Instruct                   │    │   │
│  │  │  • /v1/chat/completions                     │    │   │
│  │  │  • /v1/models                               │    │   │
│  │  │  • /v1/health/ready                         │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  │                    Port 8000                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            SlowCal Application                        │   │
│  │  • CaseManagerAgent (Orchestrator)                   │   │
│  │  • Data/Identity/ML/LLM Agents                       │   │
│  │  • Streamlit UI                                       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Health Checks
- `/v1/health/ready` - Service ready
- `/v1/health/live` - Service alive
- `/v1/models` - Model discovery

### 2.3 Optional Retrieval Microservices
- **Text Embedding NIM** - For embeddings
- **Text Reranking NIM** - For citation relevance

---

## 3) Data Sources (DataSF / Socrata)

### 3.1 Core Datasets (Configured in `src/utils/config.py`)

| Dataset | ID | Update Frequency |
|---------|----|--------------------|
| Registered Business Locations | `g8m3-pdis` | Weekly |
| Building Permits | `i98e-djp9` | Daily |
| 311 Cases | `vw6y-z8j6` | Nightly (~6am PT) |

### 3.2 Expanded Datasets

| Category | Dataset | ID | Notes |
|----------|---------|----|----|
| Code Enforcement | DBI Complaints | `gm2e-bten` | All divisions |
| Public Safety | SFPD Incident Reports | `wg3w-h783` | 2018-present, mutable |
| Economic Stress | Eviction Notices | `5cei-gny5` | Dedupe required |
| Commercial | Taxable Commercial Spaces | `rzkk-54yv` | - |
| Commercial | Commercial Vacancy Tax | `iynh-ydf2` | ⚠️ No filer name as feature |

---

## 4) System Architecture

### 4.1 High-Level Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CaseManagerAgent (Orchestrator)                    │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Stage 1:     │  │ Stage 2:     │  │ Stage 3:     │  │ Stage 4:     │ │
│  │ Data Acq.    │→ │ Entity Res.  │→ │ Features     │→ │ Risk Score   │ │
│  │ (Parallel)   │  │              │  │              │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│         ↓                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ Stage 5:     │  │ Stage 6:     │  │ Stage 7:     │                   │
│  │ Freshness    │→ │ Strategy     │→ │ QA & Output  │ → RiskAnalysis   │
│  │              │  │ (Nemotron)   │  │              │     Response      │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Core Principle: Evidence-First
- Every dataset agent outputs `evidence_refs` for every signal
- All narrative/strategy claims reference evidence IDs
- If evidence is missing, output says so explicitly

---

## 5) Agent Roster

### 5.1 Orchestrator
| Agent | File | Responsibility |
|-------|------|----------------|
| `CaseManagerAgent` | `agents/case_manager.py` | Main pipeline, state management, schema validation |

### 5.2 Data Acquisition Agents
| Agent | Dataset ID | Output Signals |
|-------|------------|----------------|
| `BusinessRegistryAgent` | `g8m3-pdis` | Canonical record, locations, dates |
| `PermitsAgent` | `i98e-djp9` | count_3m/6m/12m, avg_cost, trend |
| `Complaints311Agent` | `vw6y-z8j6` | count_3m/6m/12m, top_categories, trend |
| `DBIComplaintsAgent` | `gm2e-bten` | counts by division, open/closed ratio |
| `SFPDIncidentsAgent` | `wg3w-h783` | counts by category, radius-based |
| `EvictionsAgent` | `5cei-gny5` | neighborhood rate, trend |
| `VacancyCorridorAgent` | `rzkk-54yv`, `iynh-ydf2` | vacancy signals, trend |

### 5.3 Identity/Geo Agents
| Agent | Purpose |
|-------|---------|
| `AddressNormalizeAgent` | Normalize address strings, stable hash |
| `GeoResolveAgent` | Geocoding, spatial join keys |
| `EntityResolverAgent` | Merge candidates, match_confidence |

### 5.4 ML Agents
| Agent | Purpose |
|-------|---------|
| `FeatureBuilderAgent` | Leakage-safe features, rolling windows |
| `RiskModelAgent` | Deterministic scoring (0-1), top_drivers |
| `CalibrationAgent` | Probability calibration (optional) |
| `DataFreshnessAgent` | Freshness checks, staleness warnings |
| `DriftMonitorAgent` | Distribution drift detection (ops) |

### 5.5 LLM Agents (Nemotron)
| Agent | Purpose | Temperature |
|-------|---------|-------------|
| `EvidencePackagerAgent` | Compact evidence for LLM | N/A (deterministic) |
| `ExplanationAgent` | Plain-language explanation | 0.2 |
| `StrategyPlannerAgent` | Prioritized action plans | 0.2 |
| `LeaseNegotiationAgent` | Negotiation tactics/scripts | 0.3 |
| `CityFeesComplianceAgent` | Compliance checklist, waivers | 0.2 |
| `ScenarioSimulatorAgent` | What-if analysis | 0.3 |
| `PolicyGuardAgent` | Safety/compliance checks | N/A (rule-based) |
| `CriticQAAgent` | Validation, evidence coverage | 0.3 (optional LLM) |

---

## 6) Tooling Layer

### 6.1 Core Tools (`src/tools/`)

| Tool | File | Purpose |
|------|------|---------|
| `socrata_query` | `socrata_client.py` | SoQL queries with caching |
| `nim_chat` | `nim_client.py` | Nemotron chat completions |
| `validate_schema` | `schema_validation.py` | JSON/Pydantic validation |
| `embed_texts` | `retriever_client.py` | Text embeddings (optional) |
| `rerank` | `retriever_client.py` | Reranking (optional) |

### 6.2 Tool Signatures

```python
# Socrata
def socrata_query(
    dataset_id: str,
    soql: str,
    app_token: str = None
) -> Dict[str, Any]

# NIM
def nim_chat(
    messages: List[Dict],
    model: str,
    temperature: float,
    max_tokens: int
) -> NIMResponse

# Validation
def validate_schema(
    json_obj: Dict,
    schema: Dict
) -> Tuple[bool, List[str]]
```

---

## 7) Output Schemas

### 7.1 RiskAnalysisResponse

```json
{
  "case_id": "uuid",
  "as_of": "2026-01-25T00:00:00Z",
  "horizon_months": 6,
  "entity": {
    "entity_id": "string",
    "business_name": "string",
    "address": "string",
    "neighborhood": "string",
    "match_confidence": 0.95
  },
  "risk": {
    "score": 0.42,
    "band": "medium",
    "model_version": "v1.0.0",
    "top_drivers": [
      {
        "driver": "complaints_311_6m",
        "direction": "up",
        "evidence_refs": ["e:311-001", "e:311-002"]
      }
    ]
  },
  "signals": { ... },
  "strategy": {
    "summary": "string",
    "actions": [
      {
        "horizon": "2_weeks",
        "action": "string",
        "why": "string",
        "expected_impact": "medium",
        "effort": "low",
        "evidence_refs": ["e:311-001"],
        "success_metric": "string"
      }
    ],
    "questions_for_user": ["string"]
  },
  "limitations": ["string"],
  "audit": {
    "data_pulled_at": "ISO-8601",
    "dataset_versions": [...],
    "agent_versions": [...],
    "qa_status": "PASS"
  }
}
```

### 7.2 EvidencePack

```json
{
  "entity_summary": "string",
  "risk_score": 0.42,
  "risk_band": "medium",
  "top_drivers": [...],
  "signal_summaries": { ... },
  "evidence_items": [
    {
      "id": "e:311-001",
      "content": "Noise complaints: 15 in 6mo",
      "source": "311 Cases",
      "date": "2026-01-20"
    }
  ],
  "data_gaps": ["string"],
  "confidence_notes": ["string"],
  "as_of": "ISO-8601",
  "horizon_months": 6
}
```

---

## 8) Implementation Guide

### 8.1 Directory Structure

```
src/
├── agents/
│   ├── __init__.py
│   ├── case_manager.py          # Orchestrator
│   ├── data/
│   │   ├── business_registry_agent.py
│   │   ├── permits_agent.py
│   │   ├── complaints_311_agent.py
│   │   ├── dbi_complaints_agent.py
│   │   ├── sfpd_incidents_agent.py
│   │   ├── evictions_agent.py
│   │   └── vacancy_corridor_agent.py
│   ├── identity/
│   │   ├── address_normalize_agent.py
│   │   ├── geo_resolve_agent.py
│   │   └── entity_resolver_agent.py
│   ├── ml/
│   │   ├── feature_builder_agent.py
│   │   ├── risk_model_agent.py
│   │   ├── calibration_agent.py
│   │   ├── drift_monitor_agent.py
│   │   └── data_freshness_agent.py
│   └── llm/
│       ├── evidence_packager_agent.py
│       ├── explanation_agent.py
│       ├── strategy_planner_agent.py
│       ├── lease_negotiation_agent.py
│       ├── city_fees_compliance_agent.py
│       ├── scenario_simulator_agent.py
│       ├── policy_guard_agent.py
│       └── critic_qa_agent.py
├── tools/
│   ├── socrata_client.py
│   ├── nim_client.py
│   ├── retriever_client.py
│   └── schema_validation.py
├── schemas/
│   ├── risk_analysis_response.json
│   └── evidence_pack.json
└── utils/
    ├── config.py
    └── nemotron_client.py
```

### 8.2 Quick Start

```python
from src.agents import CaseManagerAgent

# Initialize
manager = CaseManagerAgent()

# Run analysis
result = manager.analyze(
    business_query="Blue Bottle Coffee, 300 Webster St",
    horizon_months=6
)

# Access results
if result.success:
    response = result.response
    print(f"Risk Score: {response['risk']['score']}")
    print(f"Risk Band: {response['risk']['band']}")
    for action in response['strategy']['actions']:
        print(f"- {action['action']}")
```

---

## 9) SoQL Templates

### 9.1 311 Cases (Last 6 Months Near Location)

```sql
$select=category,count(*)
&$where=case_created_date > '2025-07-25T00:00:00' 
        AND within_circle(point, {lat}, {lon}, {meters})
&$group=category
&$order=count(*) DESC
&$limit=10
```

### 9.2 SFPD Incidents (Last 6 Months by Category)

```sql
$select=incident_category,count(*)
&$where=incident_date > '2025-07-25T00:00:00' 
        AND within_circle(point, {lat}, {lon}, {meters})
&$group=incident_category
&$order=count(*) DESC
```

### 9.3 Permits (Last 12 Months)

```sql
$select=permit_type,status,count(*)
&$where=filed_date > '2025-01-25T00:00:00'
        AND street_name LIKE '{street}%'
&$group=permit_type,status
```

---

## 10) Security & Privacy

### 10.1 API Security
- NIM endpoints behind TLS/proxy
- Secure API keys in environment variables
- No sensitive data in logs

### 10.2 Data Privacy
- ❌ Do NOT model on filer names (Vacancy dataset)
- ❌ Do NOT store SSNs or PII in outputs
- ✅ Keep audit logs of datasets pulled + timestamps

### 10.3 Output Safety
- PolicyGuardAgent checks all outputs
- Required disclaimers for legal/financial content
- Evidence-grounded claims only

---

## 11) Testing & Quality

### 11.1 Acceptance Criteria

| Metric | Target |
|--------|--------|
| JSON validity | 99% of responses validate |
| Evidence coverage | 95% of strategy claims include evidence_refs |
| Join quality | match_confidence ≥ 0.6 or user confirmation |
| Determinism | Same input → materially similar output |

### 11.2 Test Suite

```
tests/
├── golden_cases/           # Expected outputs for known inputs
├── test_agents_unit.py     # Unit tests per agent
└── test_end_to_end.py      # Full pipeline tests
```

### 11.3 Golden Test Example

```python
def test_high_risk_business():
    """Business with many complaints should score high risk"""
    result = manager.analyze("Problem Business, 123 Trouble St")
    assert result.success
    assert result.response["risk"]["band"] == "high"
    assert len(result.response["strategy"]["actions"]) >= 6
```

---

## 12) Definition of Done

### 12.1 Pilot Completion Checklist

- [ ] End-to-end run for an address returns schema-valid RiskAnalysisResponse
- [ ] Strategy includes evidence refs and does not hallucinate
- [ ] System runs locally on DGX Spark with NIM endpoints healthy (`/v1/health/ready`)
- [ ] QA Agent validates 95%+ of outputs as PASS
- [ ] PolicyGuard flags 0 critical issues
- [ ] Streamlit dashboard displays results correctly
- [ ] Golden test suite passes

### 12.2 Model Selection

| Purpose | Model |
|---------|-------|
| Primary LLM | `nvidia/nemotron-4-340b-instruct` |
| Reward Model (optional) | `nvidia/nemotron-4-340b-reward` |
| Embeddings (optional) | NeMo Retriever Text Embedding NIM |

---

## Appendix: Agent Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-25 | Initial implementation |

---

*Document generated for SlowCal project - SF Small Business Risk Intelligence Platform*
