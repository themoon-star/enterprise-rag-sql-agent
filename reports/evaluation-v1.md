# TrustQuery fixed evaluation v1

Run at: 2026-09-11T09:06:08.875955+00:00
Dataset manifest: `0e02312fcfb0758fb72764bff1775d9c9ab9fa6c7f75bdf86f8bd479e6c1bca5`
Mode: deterministic offline baseline + real PostgreSQL execution

## Result

| Track | Cases | Status | Key metrics |
|---|---:|---|---|
| Enterprise RAG | 100 | PASS | status 100.0%; citation 100.0%; cross-tenant leaks 0 |
| Text-to-SQL | 50 | PASS | status 100.0%; result 100.0%; safety 100.0% |

## Scope and limitations

- RAG uses the production tenant repository, ACL-before-ranking BM25 service, refusal and citation path against a fixed synthetic enterprise corpus.
- Text-to-SQL uses the production deterministic generator, SQLGlot validator and real PostgreSQL read-only executor.
- These numbers are a reproducible offline baseline. They do not claim live-LLM quality, production traffic, business impact or real customer data.
- Full case mix and metric definitions are documented in `docs/EVALUATION.md`; machine-readable failures are in the JSON report.
