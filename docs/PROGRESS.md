# TrustQuery progress

Last updated: 2026-09-11

## Status

| Milestone | State | Completion evidence |
|---|---|---|
| M0 Clean-room repository | Complete | Root commit `9fe6f6f`; no remote; boundary and architecture documented |
| M1 Tenant and RAG backend | Complete | 10 unit/integration tests; Ruff clean |
| M2 Secure Text-to-SQL | Not started | AST, executor and repair tests |
| M3 Management console | Not started | Unit, build and browser acceptance |
| M4 Fixed evaluations | Not started | 100 RAG + 50 Text-to-SQL reports |
| M5 Public showcase | Not started | Clean scan, focused commits and public GitHub URL |

## Acceptance checklist

- [x] Independent repository initialized from an empty directory with no upstream remote.
- [x] Verified tenant tokens and cross-tenant 404 behavior.
- [x] RAG ACL-before-ranking, refusal, clarification and citations.
- [ ] Encrypted datasource configuration with no credential echo.
- [ ] SQL AST allowlist plus database read-only enforcement.
- [ ] At most one repair and full revalidation of repaired SQL.
- [ ] Responsive management and demo frontend.
- [ ] One-command Docker demo.
- [ ] 100-case RAG evaluation and 50-case Text-to-SQL evaluation.
- [ ] Architecture, contribution, metrics, demo and interview documentation.
- [ ] Tests, lint, build, secret scan and license review.
- [ ] Public GitHub repository with focused commits.

## Decision log

- 2026-09-11: Chose an independent repository instead of relabeling a derivative codebase.
- 2026-09-11: Chose server-derived JWT tenancy and PostgreSQL as the first supported structured datasource.
- 2026-09-11: Chose a self-contained BM25 retriever for deterministic RAG acceptance; live LLM generation remains an explicit adapter mode.
- 2026-09-11: Completed M1 with persistent tenant documents, role ACL filtering before BM25 ranking, evidence refusal, clarification and citations.
