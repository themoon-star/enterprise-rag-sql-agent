"""SQLGlot 只读查询策略测试。"""

import pytest
from trustquery.sql.validator import SqlValidationError, SqlValidator

ALLOWED_TABLES = frozenset({"sales_orders", "customers"})


def validate(sql: str, row_limit: int = 200):
    return SqlValidator().validate(sql, allowed_tables=ALLOWED_TABLES, row_limit=row_limit)


def test_select_is_normalized_and_limited() -> None:
    query = validate("select id, total_amount from sales_orders")

    assert query.tables == {"sales_orders"}
    assert "LIMIT 200" in query.sql


def test_cte_is_allowed_without_treating_alias_as_table() -> None:
    query = validate(
        "WITH recent AS (SELECT * FROM sales_orders) SELECT COUNT(*) FROM recent",
    )

    assert query.tables == {"sales_orders"}


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM sales_orders",
        "UPDATE sales_orders SET total_amount = 0",
        "SELECT * INTO copied_orders FROM sales_orders",
        "SELECT * FROM sales_orders FOR UPDATE",
    ],
)
def test_mutating_or_locking_statements_are_rejected(sql: str) -> None:
    with pytest.raises(SqlValidationError):
        validate(sql)


def test_multiple_statements_are_rejected() -> None:
    with pytest.raises(SqlValidationError, match="一条"):
        validate("SELECT * FROM sales_orders; SELECT * FROM customers")


def test_unauthorized_table_is_rejected() -> None:
    with pytest.raises(SqlValidationError, match="未授权表"):
        validate("SELECT * FROM payroll")


def test_non_public_schema_is_rejected() -> None:
    with pytest.raises(SqlValidationError, match="public schema"):
        validate("SELECT * FROM private.sales_orders")


def test_dangerous_function_is_rejected() -> None:
    with pytest.raises(SqlValidationError, match="pg_sleep"):
        validate("SELECT pg_sleep(5)")


def test_excessive_limit_is_clamped() -> None:
    query = validate("SELECT * FROM sales_orders LIMIT 5000", row_limit=50)

    assert "LIMIT 50" in query.sql


def test_dynamic_limit_is_rejected() -> None:
    with pytest.raises(SqlValidationError, match="整数"):
        validate("SELECT * FROM sales_orders LIMIT (SELECT COUNT(*) FROM customers)")
