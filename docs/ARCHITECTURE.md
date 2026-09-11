# TrustQuery architecture

## System boundary

```text
Vue control console
        │ Bearer token
        ▼
FastAPI ── verified tenant context
   ├── RAG service ── ACL filter → BM25 rank → answer/refusal → citations
   ├── SQL service ── schema → plan → AST guard → read-only execute → table/chart
   │                                  ▲                 │
   │                                  └── one repair ───┘
   └── admin service ── encrypted datasource + table allowlist + limits
        │
        ▼
PostgreSQL metadata and tenant demo schemas
```

## Invariants

1. **Server-derived tenancy**: tenant identity comes only from a verified bearer token.
2. **Filter before rank**: RAG candidates are filtered by tenant and role before scoring.
3. **Evidence-or-refusal**: an answer without an accessible citation is rejected.
4. **Single-statement SQL**: only one PostgreSQL `SELECT` or read-only `WITH` statement is accepted.
5. **Defense in depth**: AST rules, table allowlists, database role checks, read-only transactions, timeout and row limit all apply.
6. **One repair maximum**: repair is limited to recoverable generation/execution errors and re-enters the same AST guard.
7. **No credential echo**: plaintext connection strings and model keys never enter API responses or evaluation reports.

## Replaceable model boundary

The model adapter accepts an OpenAI-compatible endpoint and returns typed plans. Offline acceptance uses an explicitly selected deterministic adapter so tests do not silently claim live-model quality. A live-model report is a separate artifact with its provider and model recorded.

