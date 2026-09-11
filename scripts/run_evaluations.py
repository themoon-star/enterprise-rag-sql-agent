"""运行 TrustQuery v1 固定 RAG 与 Text-to-SQL 评测。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import statistics
import time
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from trustquery.datasources import CredentialCipher, DatasourceRecord
from trustquery.db import Database
from trustquery.models import KnowledgeDocument, Tenant
from trustquery.rag.service import RagService
from trustquery.repositories import DocumentRepository
from trustquery.security import TenantContext
from trustquery.sql.executor import PostgresExecutor
from trustquery.sql.generator import DeterministicSqlGenerator
from trustquery.sql.service import TextToSqlService
from trustquery.sql.validator import SqlValidationError, SqlValidator

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
REPORTS = ROOT / "reports"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """读取固定 JSONL 数据集。"""

    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def verify_manifest() -> dict[str, Any]:
    """校验数据集行数与 SHA-256，防止评测后静默改题。"""

    manifest = json.loads((DATASETS / "manifest.json").read_text(encoding="utf-8"))
    for relative_path, expected in manifest["files"].items():
        path = DATASETS / relative_path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows = len(path.read_text(encoding="utf-8").splitlines())
        if digest != expected["sha256"] or rows != expected["rows"]:
            raise RuntimeError(f"固定数据集校验失败：{relative_path}")
    return manifest


def percentile(values: list[float], ratio: float) -> float:
    """返回最近秩百分位延迟。"""

    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * ratio + 0.999999) - 1))
    return round(ordered[index], 3)


async def evaluate_rag() -> dict[str, Any]:
    """使用生产数据库仓储与 RAG 服务运行 100 条固定用例。"""

    corpus = load_jsonl(DATASETS / "rag_v1" / "corpus.jsonl")
    cases = load_jsonl(DATASETS / "rag_v1" / "cases.jsonl")
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    failures: list[dict[str, str]] = []
    latencies: list[float] = []
    status_correct = 0
    citation_correct = 0
    grounded_correct = 0
    leakage_count = 0
    answered_count = sum(case["expected_status"] == "answered" for case in cases)

    try:
        async with database.sessions() as session:
            tenant_ids = sorted({document["tenant_id"] for document in corpus})
            session.add_all(Tenant(id=tenant_id, name=tenant_id) for tenant_id in tenant_ids)
            session.add_all(
                KnowledgeDocument(
                    id=document["id"],
                    tenant_id=document["tenant_id"],
                    title=document["title"],
                    content=document["content"],
                    source_uri=document["source_uri"],
                    allowed_roles=document["allowed_roles"],
                )
                for document in corpus
            )
            await session.commit()
            service = RagService(DocumentRepository(session))

            for case in cases:
                context = TenantContext(
                    tenant_id=case["tenant_id"],
                    user_id="evaluation-user",
                    roles=frozenset(case["roles"]),
                )
                started = time.perf_counter()
                result = await service.query(context, case["question"])
                latencies.append((time.perf_counter() - started) * 1_000)

                correct = result.status == case["expected_status"]
                status_correct += correct
                if not correct:
                    failures.append(
                        {
                            "id": case["id"],
                            "gate": "status",
                            "expected": case["expected_status"],
                            "actual": result.status,
                        }
                    )

                if case["expected_status"] == "answered":
                    citation_matches = bool(
                        result.citations
                        and result.citations[0].document_id == case["expected_document_id"]
                        and result.citations[0].source_uri == case["expected_source_uri"]
                    )
                    citation_correct += citation_matches
                    grounded_matches = any(term in result.answer for term in case["expected_any_term"])
                    grounded_correct += grounded_matches
                    if not citation_matches:
                        failures.append(
                            {
                                "id": case["id"],
                                "gate": "citation",
                                "expected": case["expected_document_id"],
                                "actual": result.citations[0].document_id if result.citations else "none",
                            }
                        )
                    if not grounded_matches:
                        failures.append(
                            {
                                "id": case["id"],
                                "gate": "grounded_term",
                                "expected": " | ".join(case["expected_any_term"]),
                                "actual": result.answer,
                            }
                        )

                if case["kind"] == "cross_tenant":
                    leaked = bool(result.citations) or any(
                        marker in result.answer for marker in ("银杏", "九千万元", "十二月十五日")
                    )
                    leakage_count += leaked
    finally:
        await database.close()

    return {
        "dataset": "rag_v1",
        "cases": len(cases),
        "case_mix": dict(sorted(Counter(case["kind"] for case in cases).items())),
        "metrics": {
            "status_accuracy": round(status_correct / len(cases), 4),
            "citation_accuracy_answerable": round(citation_correct / answered_count, 4),
            "grounded_term_accuracy_answerable": round(grounded_correct / answered_count, 4),
            "cross_tenant_leakage_count": leakage_count,
            "latency_ms_p50": round(statistics.median(latencies), 3),
            "latency_ms_p95": percentile(latencies, 0.95),
        },
        "passed": not failures and leakage_count == 0,
        "failures": failures,
    }


async def evaluate_sql(postgres_url: str) -> dict[str, Any]:
    """使用生产生成器、验证器和 PostgreSQL 执行器运行 50 条固定用例。"""

    cases = load_jsonl(DATASETS / "text_to_sql_v1" / "cases.jsonl")
    cipher = CredentialCipher(Fernet.generate_key().decode())
    datasource = DatasourceRecord(
        id="evaluation-postgres",
        tenant_id="acme-demo",
        name="evaluation",
        encrypted_url=cipher.encrypt(postgres_url),
        allowed_tables=frozenset({"customers", "sales_orders"}),
        row_limit=100,
        statement_timeout_ms=2_000,
    )
    service = TextToSqlService(
        generator=DeterministicSqlGenerator(),
        executor=PostgresExecutor(cipher),
    )
    validator = SqlValidator()
    failures: list[dict[str, str]] = []
    latencies: list[float] = []
    status_correct = 0
    semantic_total = 0
    semantic_correct = 0
    safety_correct = 0
    expected_success = sum(case["expected_status"] == "succeeded" for case in cases)
    executed_success = 0

    for case in cases:
        started = time.perf_counter()
        result = await service.query(datasource, case["question"])
        latencies.append((time.perf_counter() - started) * 1_000)
        correct = result.status == case["expected_status"]
        status_correct += correct
        executed_success += result.status == "succeeded"
        if not correct:
            failures.append(
                {
                    "id": case["id"],
                    "gate": "status",
                    "expected": case["expected_status"],
                    "actual": result.status,
                }
            )

        safe = result.status == "blocked"
        if result.sql:
            try:
                validator.validate(
                    result.sql,
                    allowed_tables=datasource.allowed_tables,
                    row_limit=datasource.row_limit,
                )
                safe = True
            except SqlValidationError:
                safe = False
        safety_correct += safe
        if not safe:
            failures.append(
                {"id": case["id"], "gate": "safety", "expected": "readonly", "actual": result.sql or "none"}
            )

        expected_row = case.get("expected_row")
        if expected_row is not None:
            semantic_total += 1
            row_matches = bool(result.rows) and all(
                values_equal(result.rows[0].get(column), value) for column, value in expected_row.items()
            )
            semantic_correct += row_matches
            if not row_matches:
                failures.append(
                    {
                        "id": case["id"],
                        "gate": "result",
                        "expected": json.dumps(expected_row, ensure_ascii=False),
                        "actual": json.dumps(normalize(result.rows[:1]), ensure_ascii=False),
                    }
                )

    return {
        "dataset": "text_to_sql_v1",
        "cases": len(cases),
        "case_mix": dict(sorted(Counter(case["kind"] for case in cases).items())),
        "metrics": {
            "status_accuracy": round(status_correct / len(cases), 4),
            "execution_success_rate_expected_success": round(executed_success / expected_success, 4),
            "result_accuracy_scored": round(semantic_correct / semantic_total, 4),
            "safety_pass_rate": round(safety_correct / len(cases), 4),
            "latency_ms_p50": round(statistics.median(latencies), 3),
            "latency_ms_p95": percentile(latencies, 0.95),
        },
        "passed": not failures,
        "failures": failures,
    }


def values_equal(actual: Any, expected: Any) -> bool:
    """以稳定数值语义比较数据库 Decimal 与 JSON 数字。"""

    if isinstance(actual, Decimal):
        actual = float(actual)
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) < 0.0001
    return actual == expected


def normalize(value: Any) -> Any:
    """将报告失败样本转换为 JSON 可序列化值。"""

    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    return value


def markdown_report(report: dict[str, Any]) -> str:
    """生成适合代码审查和简历证据引用的精简报告。"""

    rag = report["rag"]
    sql = report["text_to_sql"]
    rag_status = "PASS" if rag["passed"] else "FAIL"
    sql_status = "PASS" if sql["passed"] else "FAIL"
    lines = [
        "# TrustQuery fixed evaluation v1",
        "",
        f"Run at: {report['run_at']}",
        f"Dataset manifest: `{report['manifest_sha256']}`",
        "Mode: deterministic offline baseline + real PostgreSQL execution",
        "",
        "## Result",
        "",
        "| Track | Cases | Status | Key metrics |",
        "|---|---:|---|---|",
        (
            f"| Enterprise RAG | {rag['cases']} | {rag_status} | "
            f"status {rag['metrics']['status_accuracy']:.1%}; "
            f"citation {rag['metrics']['citation_accuracy_answerable']:.1%}; "
            f"cross-tenant leaks {rag['metrics']['cross_tenant_leakage_count']} |"
        ),
        (
            f"| Text-to-SQL | {sql['cases']} | {sql_status} | "
            f"status {sql['metrics']['status_accuracy']:.1%}; "
            f"result {sql['metrics']['result_accuracy_scored']:.1%}; "
            f"safety {sql['metrics']['safety_pass_rate']:.1%} |"
        ),
        "",
        "## Scope and limitations",
        "",
        (
            "- RAG uses the production tenant repository, ACL-before-ranking BM25 service, "
            "refusal and citation path against a fixed synthetic enterprise corpus."
        ),
        (
            "- Text-to-SQL uses the production deterministic generator, SQLGlot validator "
            "and real PostgreSQL read-only executor."
        ),
        (
            "- These numbers are a reproducible offline baseline. They do not claim live-LLM quality, "
            "production traffic, business impact or real customer data."
        ),
        (
            "- Full case mix and metric definitions are documented in `docs/EVALUATION.md`; "
            "machine-readable failures are in the JSON report."
        ),
    ]
    return "\n".join(lines) + "\n"


async def main() -> None:
    """校验数据版本，执行双轨评测并持久化报告。"""

    postgres_url = os.getenv("EVAL_POSTGRES_URL")
    if not postgres_url:
        raise RuntimeError("EVAL_POSTGRES_URL 未配置；Text-to-SQL 固定评测必须连接真实 PostgreSQL")

    manifest = verify_manifest()
    manifest_path = DATASETS / "manifest.json"
    report = {
        "version": "1.0.0",
        "run_at": datetime.now(UTC).isoformat(),
        "mode": "deterministic_offline_with_real_postgresql",
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "manifest": manifest,
        "rag": await evaluate_rag(),
        "text_to_sql": await evaluate_sql(postgres_url),
    }
    report["passed"] = report["rag"]["passed"] and report["text_to_sql"]["passed"]

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "evaluation-v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (REPORTS / "evaluation-v1.md").write_text(markdown_report(report), encoding="utf-8", newline="\n")
    summary = {
        "passed": report["passed"],
        "rag": report["rag"]["metrics"],
        "sql": report["text_to_sql"]["metrics"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
