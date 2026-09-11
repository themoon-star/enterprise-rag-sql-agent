# TrustQuery

[![CI](https://github.com/themoon-star/enterprise-rag-sql-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/themoon-star/enterprise-rag-sql-agent/actions/workflows/ci.yml)

面向企业知识问答与数据分析的安全 Agent。项目采用全新 Git 历史和 clean-room 实现，核心目标是把“模型能回答”收敛为可验证的三件事：**只能访问当前租户的数据、每个结论都能追溯、生成 SQL 在执行前后均受约束**。

> 当前状态：M4 可复现验收。固定测评包含 100 条 RAG 与 50 条 Text-to-SQL 用例，结果来自确定性离线基线与真实 PostgreSQL，不代表线上模型或客户流量。

## 验收结果

| Track | Cases | Result | Evidence |
|---|---:|---|---|
| Enterprise RAG | 100 | PASS | 状态 100%、可回答引用 100%、跨租户泄漏 0 |
| Text-to-SQL | 50 | PASS | 状态 100%、确定答案 100%、安全通过率 100% |

完整定义、数据构成与限制见 [指标边界](docs/METRICS.md) 和 [机器可读报告](reports/evaluation-v1.json)。

## 一键演示

前置条件：Docker Desktop 与 Docker Compose。

```powershell
.\scripts\demo.ps1
```

打开 `http://localhost:3100`。脚本会在被 Git 忽略的 `.env.runtime` 中生成本地随机密钥，构建 4 个隔离服务并写入演示租户数据。使用 `.\scripts\stop-demo.ps1` 停止服务并清理演示数据卷。

## 核心能力

- 企业 RAG：租户与角色过滤、BM25 检索、无依据拒答、引用证据和歧义澄清。
- 安全 Text-to-SQL：结构化计划、SQLGlot AST 白名单、只读角色与事务、超时和行数限制。
- 受限自修复：仅语法或数据库语义错误可触发一次修复，修复 SQL 必须重新经过全部安全检查。
- 管理控制台：配置只读数据源、授权表和执行限制，凭证只加密保存、不回显。
- 可复现验收：100 条 RAG 与 50 条 Text-to-SQL 固定评测、一键演示和脱敏证据摘要。

## 模型模式

默认 `LLM_MODE=deterministic`，用于可复现演示和固定测评。设置 `LLM_MODE=openai` 后，RAG 回答与 SQL 候选会通过 OpenAI-compatible Chat Completions 接口生成；租户 ACL、引用、SQL AST 校验和数据库只读限制仍由服务端执行。

```dotenv
LLM_MODE=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model
```

在线模式不会静默降级；缺少 Key 或模型名时应用启动失败。请勿提交 `.env` 或 `.env.runtime`。

## 本地质量检查

```powershell
uv sync --frozen
uv run ruff check backend scripts
uv run pytest -q
.\scripts\test-postgres.ps1
.\scripts\run-evaluations.ps1
.\scripts\check-secrets.ps1

Set-Location frontend
npm ci
npm run lint
npm run typecheck
npm run build
```

## 技术栈

Python 3.12 · FastAPI · PostgreSQL · SQLAlchemy · SQLGlot · Vue 3 · Docker Compose · Pytest

## 文档

- [Clean-room 边界](docs/CLEAN_ROOM.md)
- [系统架构](docs/ARCHITECTURE.md)
- [威胁模型](docs/THREAT_MODEL.md)
- [固定测评说明](docs/EVALUATION.md)
- [指标与证据边界](docs/METRICS.md)
- [最新测评报告](reports/evaluation-v1.md)
- [个人贡献与溯源](docs/CONTRIBUTION.md)
- [3–5 分钟演示脚本](docs/DEMO.md)
- [面试与代码阅读指南](docs/INTERVIEW.md)
- [质量与发布审计](docs/QUALITY.md)
- [第三方依赖许可证](THIRD_PARTY_NOTICES.md)
- [实施进度](docs/PROGRESS.md)

## 许可证

[MIT](LICENSE)，Copyright © 2026 Zhang Junjie。
