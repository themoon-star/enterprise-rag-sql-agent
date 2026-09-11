# Personal contribution and provenance

## Attribution statement

This repository is a clean-room, independent project authored in a new directory and new Git history.
It does not contain Yuxi or SQLBot source code, assets, documentation text or commits. Third-party
libraries are used through their public APIs and remain declared in the dependency manifests.

## Independently delivered scope

- Designed the tenant trust boundary: verified JWT context, role ACL filtering before retrieval and
  cross-tenant 404 behavior.
- Implemented enterprise RAG with deterministic BM25 retrieval, evidence thresholding, clarification,
  refusal, citations and a replaceable OpenAI-compatible answer generator.
- Implemented encrypted, tenant-scoped PostgreSQL data-source management without credential echo.
- Implemented Text-to-SQL generation, SQLGlot AST policy, table allowlists, read-only transactions,
  timeout/row controls and a single fully revalidated repair attempt.
- Built the Vue 3 audit console, responsive navigation and the four-service Docker Compose demo.
- Authored 100 RAG and 50 Text-to-SQL fixed cases, hash verification, real PostgreSQL runners,
  machine-readable reports and CI checks.
- Wrote the architecture, threat model, metric definitions, demo script and interview reading guide.

## Evidence map

| Claim | Inspectable evidence |
|---|---|
| Independent history | Root commit and `docs/CLEAN_ROOM.md` |
| Tenant isolation | `security.py`, repository filters and integration tests |
| RAG grounding | `rag/service.py`, RAG tests and `datasets/rag_v1/` |
| SQL safety | `sql/validator.py`, `sql/executor.py` and unit/integration tests |
| Repair limit | `sql/service.py` and repair regression tests |
| Reproducibility | Compose files, PowerShell runners and `.github/workflows/ci.yml` |
| Quantitative results | `datasets/manifest.json` and `reports/evaluation-v1.json` |

## Resume-safe wording

“独立设计并实现多租户企业 RAG 与安全 Text-to-SQL Agent；以 JWT 租户上下文、ACL 检索前过滤、
SQLGlot AST 白名单和 PostgreSQL 只读事务构建纵深防御，并建立 100 条 RAG、50 条 Text-to-SQL
固定测评与可复现 Docker 演示。”

The percentages in a resume must be described as fixed synthetic/offline acceptance results. They
must not be presented as customer traffic, production SLA, business revenue or live-model quality.
