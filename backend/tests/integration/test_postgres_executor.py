"""真实 PostgreSQL 只读执行与 schema 探测测试。"""

import os

import pytest
from cryptography.fernet import Fernet
from trustquery.datasources import CredentialCipher, DatasourceRecord
from trustquery.sql.executor import PostgresExecutor, SqlExecutionError
from trustquery.sql.validator import SqlValidator, ValidatedQuery

pytestmark = pytest.mark.integration
POSTGRES_URL = os.getenv("TEST_POSTGRES_URL")


def datasource(cipher: CredentialCipher) -> DatasourceRecord:
    if POSTGRES_URL is None:
        pytest.skip("TEST_POSTGRES_URL 未配置")
    return DatasourceRecord(
        id="postgres-test",
        tenant_id="tenant-a",
        name="analytics",
        encrypted_url=cipher.encrypt(POSTGRES_URL),
        allowed_tables=frozenset({"sales_orders"}),
        row_limit=100,
        statement_timeout_ms=2_000,
    )


@pytest.mark.asyncio
async def test_executor_introspects_allowlist_and_runs_readonly_query() -> None:
    cipher = CredentialCipher(Fernet.generate_key().decode())
    source = datasource(cipher)
    executor = PostgresExecutor(cipher)

    schema = await executor.introspect(source)
    query = SqlValidator().validate(
        "SELECT COUNT(*) AS order_count FROM sales_orders",
        allowed_tables=source.allowed_tables,
        row_limit=source.row_limit,
    )
    result = await executor.execute(source, query)

    assert set(schema) == {"sales_orders"}
    assert {"id", "customer_id", "status", "total_amount", "ordered_at"}.issubset(schema["sales_orders"])
    assert result.rows == ({"order_count": 5},)


@pytest.mark.asyncio
async def test_database_readonly_transaction_blocks_write_even_if_validator_is_bypassed() -> None:
    cipher = CredentialCipher(Fernet.generate_key().decode())
    source = datasource(cipher)
    executor = PostgresExecutor(cipher)
    forged_query = ValidatedQuery(
        sql="UPDATE sales_orders SET total_amount = 0",
        tables=frozenset({"sales_orders"}),
    )

    with pytest.raises(SqlExecutionError, match="只读查询执行失败"):
        await executor.execute(source, forged_query)
