"""安全问数与单次 SQL 修复编排测试。"""

from dataclasses import dataclass, field

import pytest
from trustquery.datasources import DatasourceRecord
from trustquery.sql.executor import QueryExecution, SqlExecutionError
from trustquery.sql.service import TextToSqlService
from trustquery.sql.validator import ValidatedQuery


@dataclass
class StubGenerator:
    initial_sql: str
    repaired_sql: str
    repair_calls: int = 0

    async def generate(self, question: str, schema: dict[str, tuple[str, ...]]) -> str:
        _ = question, schema
        return self.initial_sql

    async def repair(
        self,
        question: str,
        schema: dict[str, tuple[str, ...]],
        failed_sql: str,
        error_code: str,
    ) -> str:
        _ = question, schema, failed_sql, error_code
        self.repair_calls += 1
        return self.repaired_sql


@dataclass
class StubExecutor:
    failures: int = 0
    executed_sql: list[str] = field(default_factory=list)

    async def introspect(self, datasource: DatasourceRecord) -> dict[str, tuple[str, ...]]:
        _ = datasource
        return {"sales_orders": ("id", "total_amount")}

    async def execute(self, datasource: DatasourceRecord, query: ValidatedQuery) -> QueryExecution:
        _ = datasource
        self.executed_sql.append(query.sql)
        if len(self.executed_sql) <= self.failures:
            raise SqlExecutionError("simulated")
        return QueryExecution(columns=("record_count",), rows=({"record_count": 3},))


def datasource() -> DatasourceRecord:
    return DatasourceRecord(
        id="ds-1",
        tenant_id="tenant-a",
        name="demo",
        encrypted_url="encrypted",
        allowed_tables=frozenset({"sales_orders"}),
        row_limit=100,
        statement_timeout_ms=1_000,
    )


@pytest.mark.asyncio
async def test_unsafe_initial_sql_is_blocked_without_execution_or_repair() -> None:
    generator = StubGenerator("DELETE FROM sales_orders", "SELECT * FROM sales_orders")
    executor = StubExecutor()

    result = await TextToSqlService(generator=generator, executor=executor).query(datasource(), "删除订单")

    assert result.status == "blocked"
    assert result.execution_attempts == 0
    assert executor.executed_sql == []
    assert generator.repair_calls == 0


@pytest.mark.asyncio
async def test_failed_safe_query_is_repaired_once_and_revalidated() -> None:
    generator = StubGenerator(
        "SELECT missing FROM sales_orders",
        "SELECT COUNT(*) AS record_count FROM sales_orders",
    )
    executor = StubExecutor(failures=1)

    result = await TextToSqlService(generator=generator, executor=executor).query(datasource(), "订单数量")

    assert result.status == "succeeded"
    assert result.repaired is True
    assert result.execution_attempts == 2
    assert generator.repair_calls == 1
    assert len(executor.executed_sql) == 2


@pytest.mark.asyncio
async def test_unsafe_repaired_sql_is_rejected_before_second_execution() -> None:
    generator = StubGenerator("SELECT missing FROM sales_orders", "SELECT * FROM payroll")
    executor = StubExecutor(failures=1)

    result = await TextToSqlService(generator=generator, executor=executor).query(datasource(), "订单数量")

    assert result.status == "blocked"
    assert result.decision == "repaired_sql_rejected"
    assert result.execution_attempts == 1
    assert len(executor.executed_sql) == 1


@pytest.mark.asyncio
async def test_second_execution_failure_exhausts_repair_budget() -> None:
    generator = StubGenerator("SELECT missing FROM sales_orders", "SELECT id FROM sales_orders")
    executor = StubExecutor(failures=2)

    result = await TextToSqlService(generator=generator, executor=executor).query(datasource(), "订单明细")

    assert result.status == "failed"
    assert result.decision == "repair_exhausted"
    assert result.execution_attempts == 2
    assert generator.repair_calls == 1
