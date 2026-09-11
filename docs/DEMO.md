# 3–5 minute demo script

## Preparation

```powershell
.\scripts\demo.ps1
```

Open `http://localhost:3100`. The demo uses generated local credentials, one metadata database and a
separate analytics database with a read-only role.

## 0:00–0:40 — Problem and architecture

Show **态势总览**.

“TrustQuery solves two enterprise-agent risks: knowledge answers must respect tenant/role boundaries,
and natural-language analytics must never grant the model database authority. The four checkpoints on
screen are enforced in backend code, not UI labels.”

Point to the four decision-chain nodes and the counts for accessible documents, data sources,
allowlisted tables and repair budget.

## 0:40–1:50 — Evidence-grounded RAG

Open **知识检索**, choose **差旅报销材料**, then run the query.

“The JWT decides tenant and roles. The repository applies ACL before BM25 ranking, so unauthorized
text cannot become a candidate or enter an external model. A valid result includes answer, source URI,
score and decision trace.”

Then choose **测试证据拒答** and run it.

“When accessible evidence is insufficient, the service refuses instead of inventing an answer.”

## 1:50–3:10 — Secure Text-to-SQL

Open **安全问数**, choose **订单数量**, then **生成并执行**.

“The generator sees only the authorized schema. SQLGlot parses one statement, rejects write/admin
constructs and non-allowlisted tables, and clamps LIMIT. PostgreSQL then enforces a read-only
transaction, timeout and row limit. A failed safe query can be repaired once, but the repaired SQL
must pass the same validator.”

Show normalized SQL, result `5`, `attempts=1` and `repaired=false`.

## 3:10–4:10 — Data-source boundary

Open **数据源**.

“The API stores a Fernet-encrypted connection URL but returns only name, tables and limits. The demo
analytics account has SELECT permission only; application checks and database permissions form two
independent layers.”

## 4:10–5:00 — Reproducible evidence

Show `reports/evaluation-v1.md` or run:

```powershell
.\scripts\run-evaluations.ps1
```

“The committed set has 100 RAG and 50 Text-to-SQL cases. The runner checks SHA-256 before execution,
uses real PostgreSQL for SQL, and records failures in JSON. These are synthetic deterministic
acceptance results, not production or live-LLM claims.”

Stop when needed with `./scripts/stop-demo.ps1`.
