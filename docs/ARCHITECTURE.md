# TrustQuery architecture

## 1. System boundary

```text
Vue 3 audit console
        │ Bearer JWT
        ▼
FastAPI ── verified tenant context
   ├── RAG ── tenant/role ACL → BM25 → evidence gate → answer/refusal + citations
   │                                               └── extractive or OpenAI-compatible
   ├── Text-to-SQL ── authorized schema → candidate → SQLGlot AST guard
   │                                      │                  │
   │                                      │          PostgreSQL read-only execute
   │                                      └── one repair → same AST guard
   └── datasource admin ── Fernet encrypted URL + table allowlist + runtime limits
        │
        ├── metadata PostgreSQL
        └── tenant read-only PostgreSQL
```

The deterministic adapters are the default for the demo and fixed evaluation. `LLM_MODE=openai`
replaces both answer generation and SQL candidate generation with an OpenAI-compatible Chat
Completions client. Retrieval authorization, citations, SQL validation and database enforcement do
not move into the model.

## 2. Runtime sequence

### Enterprise RAG

1. `security.py` verifies issuer, audience, expiry and signature, then creates `TenantContext`.
2. `DocumentRepository.list_accessible` applies tenant and role conditions in the database query.
3. `RagService` ranks only the returned documents and requires sufficient shared evidence terms.
4. No accepted evidence produces a refusal; a short question produces a clarification.
5. Accepted excerpts are passed to the selected answer generator and returned with source URI,
   score and a non-sensitive decision trace.

### Secure Text-to-SQL

1. `DatasourceRepository.get` resolves the data source under the token tenant.
2. `PostgresExecutor.introspect` exposes only columns from configured allowlisted tables.
3. The selected generator creates a SQL candidate from the question and authorized schema.
4. `SqlValidator` parses exactly one PostgreSQL query, blocks mutation/admin/locking constructs,
   dangerous functions and non-allowlisted tables, then clamps `LIMIT`.
5. `PostgresExecutor` opens a transaction, enables database read-only mode and statement timeout,
   executes the normalized SQL and returns at most the configured row limit.
6. A database execution failure may trigger one repair. The repaired SQL must pass the same step 4
   validator before a second and final execution attempt.

## 3. Code map

| Area | Main files | Responsibility |
|---|---|---|
| HTTP boundary | `api.py`, `schemas.py`, `security.py` | Request validation, JWT-derived identity, role checks, safe response shapes |
| Persistence | `db.py`, `models.py`, `repositories.py` | Async sessions, tenant documents and ACL-filtered reads |
| RAG | `rag/bm25.py`, `rag/service.py`, `rag/generator.py` | Tokenization, ranking, evidence gate, citations and answer adapter |
| Data sources | `datasources.py` | URL validation, encryption, tenant isolation and no-echo summaries |
| Text-to-SQL | `sql/generator.py`, `sql/validator.py`, `sql/executor.py`, `sql/service.py` | Candidate generation, AST policy, read-only execution and repair budget |
| Model boundary | `llm.py` | OpenAI-compatible JSON request/response handling without logging credentials |
| Product demo | `frontend/`, `compose.yml`, `scripts/demo.ps1` | Audit console and four-service reproducible environment |
| Evidence | `datasets/`, `scripts/run_evaluations.py`, `reports/` | Versioned cases, hash verification, strict metrics and reports |

## 4. Invariants

1. Tenant identity comes only from a verified bearer token, never from a request body.
2. RAG authorization happens before ranking, so inaccessible text never reaches retrieval or a model.
3. An answer requires accessible evidence and carries citations; otherwise the service refuses.
4. Only one PostgreSQL `SELECT` or read-only `WITH` statement may execute.
5. Table allowlists, AST rules, database role, read-only transaction, timeout and row limit all apply.
6. Repair is limited to one attempt and re-enters the complete validator.
7. Connection strings, encrypted values and model keys never enter API responses or reports.
8. Deterministic and live-model evidence are separate; a deterministic report is never labeled as
   live-model accuracy.

## 5. Deployment topology

`compose.yml` starts four containers: Vue/Nginx, FastAPI, metadata PostgreSQL and a separate analytics
PostgreSQL reached through a generated read-only role. `scripts/demo.ps1` creates random local secrets
in ignored `.env.runtime`; `scripts/stop-demo.ps1` removes containers and demo volumes. Production use
must replace demo session issuance with an external identity provider and provide per-tenant database
roles and network policy.
