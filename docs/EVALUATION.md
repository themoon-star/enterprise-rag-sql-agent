# Fixed evaluation v1

TrustQuery 使用固定、可哈希、可复跑的合成企业数据验证工程行为。数据不来自真实企业，也不代表线上用户流量。

## 数据集

| Track | Cases | Coverage |
|---|---:|---|
| Enterprise RAG | 100 | 60 可回答、15 领域外拒答、10 角色拒答、5 跨租户拒答、10 歧义澄清 |
| Text-to-SQL | 50 | 35 常规语义、5 歧义阻断、10 对抗式自然语言安全 |

`datasets/manifest.json` 记录每个 JSONL 文件的行数与 SHA-256。运行器会在执行前重新计算，两者不一致时直接失败。

## 指标定义

- `status_accuracy`：回答、拒答、澄清或 SQL 执行状态与预期一致的比例。
- `citation_accuracy_answerable`：60 条可回答 RAG 用例的首条引用同时命中预期文档与来源 URI 的比例。
- `grounded_term_accuracy_answerable`：回答包含预先标注事实词的比例。
- `cross_tenant_leakage_count`：跨租户用例返回引用或出现隐藏事实标记的次数，门槛为 0。
- `result_accuracy_scored`：30 条带确定数值答案的 SQL 用例中，真实 PostgreSQL 首行结果正确的比例。
- `safety_pass_rate`：50 条 SQL 用例最终处于阻断状态，或返回 SQL 可再次通过生产验证器的比例。
- 延迟为单机本地运行的端到端服务耗时，仅用于回归，不作为生产 SLA。

## 运行

```powershell
.\scripts\run-evaluations.ps1
```

脚本为 PostgreSQL 管理账号与只读账号生成临时随机凭证，启动隔离测试库，运行生产 RAG/SQL 主链路并清理容器。最终生成：

- `reports/evaluation-v1.json`：完整机器可读指标与失败样本。
- `reports/evaluation-v1.md`：适合代码审查的摘要。

## 解释边界

v1 是“确定性离线基线 + 真实 PostgreSQL 执行”。它证明权限、检索、拒答、引用、SQL AST 约束与只读执行链路可复现；不声称线上大模型准确率、真实客户价值或生产吞吐。接入模型后的报告必须单独记录供应商、模型版本、参数、运行时间和数据集哈希。
