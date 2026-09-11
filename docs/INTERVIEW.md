# Interview and code-reading guide

## One-minute introduction

“TrustQuery 是我独立从零实现的多租户企业 RAG 与安全 Text-to-SQL Agent。它重点解决的不是单纯
‘能回答’，而是回答和问数是否可授权、可追溯、可复现。RAG 链路从 JWT 中解析租户和角色，先在
数据库层做 ACL 过滤再 BM25 排序；证据不足就拒答，回答必须携带引用。问数链路只向生成器暴露授权
Schema，SQL 经 SQLGlot AST 白名单校验后，再用 PostgreSQL 只读事务、超时和行数限制执行；如果执行
失败只允许修复一次，修复结果必须重新走同一套校验。我还做了 Vue 审计控制台、四服务 Docker 一键
演示，以及 100 条 RAG、50 条 Text-to-SQL 的固定测评和 CI。当前 100% 是合成离线验收结果，不是
线上大模型指标。”

## Three-minute structure

1. **Problem**: enterprise assistants face cross-tenant leakage, unsupported answers and unsafe SQL.
2. **Boundary**: models generate candidates; server policy and database permissions make decisions.
3. **RAG**: verified token → ACL-before-rank → evidence gate → extractive/OpenAI answer → citations.
4. **SQL**: authorized schema → candidate → AST validation → read-only execution → at most one repair.
5. **Engineering**: async FastAPI/PostgreSQL, encrypted data-source credentials, Vue audit UI, Docker
   Compose, fixed hash-verified evaluation and GitHub Actions.
6. **Evidence and limits**: 100/50 synthetic cases pass; real PostgreSQL is used, but no live-model or
   customer claim is made.

## Recommended code-reading order

1. `docs/ARCHITECTURE.md` — establish boundaries and invariants.
2. `backend/src/trustquery/security.py` — understand trusted tenant context.
3. `repositories.py` then `rag/service.py` — verify ACL precedes rank and how refusal works.
4. `sql/validator.py` then `sql/executor.py` — separate AST and database defenses.
5. `sql/service.py` — trace the one-repair state machine.
6. `llm.py`, `rag/generator.py`, `sql/generator.py` — see why model adapters cannot bypass policy.
7. `scripts/run_evaluations.py` and datasets — understand every published number.
8. `frontend/src/App.vue` and `compose.yml` — connect the visible demo to backend behavior.

For each file, answer three questions: what input is trusted, what decision is made here, and what test
would fail if this boundary were removed.

## Common interview questions

### Why filter before retrieval rather than after generation?

Post-filtering is too late: unauthorized text could already affect ranking, prompts, logs or model
output. Repository-level tenant/role predicates ensure hidden content never enters retrieval.

### Why use both an AST validator and a read-only database role?

They cover different failure modes. AST validation enforces application policy before execution;
database permissions and read-only transactions contain mistakes or validator gaps at the resource
boundary.

### Why allow one SQL repair?

It recovers from a realistic schema/semantic error while keeping latency and risk bounded. Unlimited
repair creates an unbounded agent loop. The second candidate is treated as untrusted and revalidated.

### Is BM25 enough for enterprise RAG?

It is a deliberate deterministic baseline that makes security behavior and regression metrics
reproducible. A production evolution can add hybrid dense retrieval and reranking, but tenant/role
filtering must stay before every retriever and the fixed baseline remains a control group.

### Where is the “Agent” behavior?

The SQL path is a bounded decision loop: introspect authorized tools/data, generate, validate, execute,
observe failure, optionally repair once, revalidate and terminate. It is intentionally constrained
rather than an open-ended autonomous loop.

### How would you extend it?

First add tenant-filtered vector retrieval and retrieval recall evaluation; then evaluate a named live
model in a separate report; finally add OpenTelemetry/Langfuse traces with prompt and credential
redaction. None of these should weaken the existing server-side policy boundary.

## Honest resume numbers

Use: “建立 100 条 RAG + 50 条 Text-to-SQL 固定合成测评，离线验收状态/引用/结果/安全指标均为
100%，跨租户泄漏 0；SQL 在真实 PostgreSQL 只读账号上执行。”

Avoid: “线上准确率 100%”, “服务真实客户”, “生产 p95”, or any business-impact number not backed by
external evidence.
