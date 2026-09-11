# TrustQuery

面向企业知识问答与数据分析的安全 Agent。项目采用全新 Git 历史和 clean-room 实现，核心目标是把“模型能回答”收敛为可验证的三件事：**只能访问当前租户的数据、每个结论都能追溯、生成 SQL 在执行前后均受约束**。

> 当前状态：M0 工程骨架。功能与指标只有在对应测试和报告落库后才会更新为完成。

## 计划能力

- 企业 RAG：租户与角色过滤、BM25 检索、无依据拒答、引用证据和歧义澄清。
- 安全 Text-to-SQL：结构化计划、SQLGlot AST 白名单、只读角色与事务、超时和行数限制。
- 受限自修复：仅语法或数据库语义错误可触发一次修复，修复 SQL 必须重新经过全部安全检查。
- 管理控制台：配置只读数据源、授权表和执行限制，凭证只加密保存、不回显。
- 可复现验收：100 条 RAG 与 50 条 Text-to-SQL 固定评测、一键演示和脱敏证据摘要。

## 技术栈

Python 3.12 · FastAPI · PostgreSQL · SQLAlchemy · SQLGlot · Vue 3 · Docker Compose · Pytest

## 文档

- [Clean-room 边界](docs/CLEAN_ROOM.md)
- [系统架构](docs/ARCHITECTURE.md)
- [实施进度](docs/PROGRESS.md)

## 许可证

[MIT](LICENSE)，Copyright © 2026 Zhang Junjie。

