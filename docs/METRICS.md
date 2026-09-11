# Metrics and evidence limits

## Latest committed baseline

Run: 2026-09-11, mode `deterministic_offline_with_real_postgresql`.

| Track | Dataset | Result | Key metrics |
|---|---:|---|---|
| Enterprise RAG | 100 cases | PASS | status 100%; answerable citation 100%; grounded term 100%; cross-tenant leaks 0 |
| Text-to-SQL | 50 cases | PASS | status 100%; expected execution 100%; scored result 100%; safety 100% |

Local single-run latency was RAG p50 1.005 ms / p95 1.375 ms and SQL p50 116.140 ms / p95
158.242 ms. These timings are useful only as regression signals on that machine and are not a
production SLA.

## Dataset composition

- RAG: 60 answerable, 15 out-of-domain refusal, 10 role-blocked, 5 cross-tenant and 10 clarification.
- Text-to-SQL: 35 ordinary semantic cases, 5 ambiguous cases and 10 adversarial natural-language
  cases. Thirty successful cases have deterministic result assertions.

Before execution, the runner verifies all JSONL row counts and SHA-256 values against
`datasets/manifest.json`. A changed case file cannot silently reuse an old result.

## What the baseline proves

- The production tenant repository and ACL-before-ranking retrieval path behave consistently on the
  committed synthetic corpus.
- Answer/refusal/clarification decisions, source references and marked grounding terms meet the fixed
  expectations.
- Generated SQL passes the production SQL validator and successful cases execute through a real
  PostgreSQL read-only role.
- Adversarial prompts cannot turn the final candidate into an unsafe or non-allowlisted query.

## What it does not prove

- No real enterprise data, customer request or production traffic is included.
- The default run does not call a live LLM and therefore is not a model-accuracy benchmark.
- The corpus is intentionally small and synthetic; the reported 100% figures are engineering
  acceptance for known behavior, not generalization claims.
- Local latency does not predict concurrency, cloud network delay or production capacity.

The exact definitions and reproduction command are in `docs/EVALUATION.md`; the complete output and
failure list are in `reports/evaluation-v1.json`.
