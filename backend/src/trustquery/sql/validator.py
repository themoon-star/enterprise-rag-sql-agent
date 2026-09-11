"""基于 SQLGlot AST 的 PostgreSQL 查询安全策略。"""

from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError

MUTATING_NODES = (
    exp.Alter,
    exp.Command,
    exp.Create,
    exp.Delete,
    exp.Drop,
    exp.Insert,
    exp.Into,
    exp.Lock,
    exp.Merge,
    exp.Set,
    exp.Transaction,
    exp.Update,
    exp.Use,
)
DANGEROUS_FUNCTIONS = {
    "dblink",
    "lo_export",
    "lo_import",
    "pg_ls_dir",
    "pg_read_file",
    "pg_read_binary_file",
    "pg_sleep",
}


class SqlValidationError(ValueError):
    """候选 SQL 未通过只读安全策略。"""


@dataclass(frozen=True, slots=True)
class ValidatedQuery:
    """通过 AST 校验并受行数约束的 SQL。"""

    sql: str
    tables: frozenset[str]


class SqlValidator:
    """只允许单条查询、白名单表和安全函数，并强制最大行数。"""

    def validate(self, sql: str, *, allowed_tables: frozenset[str], row_limit: int) -> ValidatedQuery:
        """解析、验证并规范化候选 PostgreSQL 查询。"""

        try:
            statements = [statement for statement in parse(sql, read="postgres") if statement is not None]
        except ParseError as exc:
            raise SqlValidationError("SQL 无法解析") from exc

        if len(statements) != 1:
            raise SqlValidationError("只允许提交一条 SQL 查询")

        statement = statements[0]
        if not isinstance(statement, exp.Query):
            raise SqlValidationError("只允许 SELECT 或 WITH 查询")
        if any(statement.find(node_type) is not None for node_type in MUTATING_NODES):
            raise SqlValidationError("查询包含写入、锁定或管理语句")

        self._validate_functions(statement)
        tables = self._validate_tables(statement, allowed_tables)
        self._apply_row_limit(statement, row_limit)
        return ValidatedQuery(sql=statement.sql(dialect="postgres"), tables=frozenset(tables))

    @staticmethod
    def _validate_functions(statement: exp.Expression) -> None:
        for function in statement.find_all(exp.Func):
            if isinstance(function, exp.Anonymous):
                name = function.name.lower()
            else:
                name = function.sql_name().lower()
            if name in DANGEROUS_FUNCTIONS:
                raise SqlValidationError(f"函数 {name} 不在安全白名单中")

    @staticmethod
    def _validate_tables(statement: exp.Expression, allowed_tables: frozenset[str]) -> set[str]:
        cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}
        tables: set[str] = set()
        for table in statement.find_all(exp.Table):
            table_name = table.name.lower()
            if table_name in cte_names:
                continue
            if table.catalog or (table.db and table.db.lower() != "public"):
                raise SqlValidationError("只允许访问 public schema 中的授权表")
            tables.add(table_name)

        unauthorized = tables.difference(name.lower() for name in allowed_tables)
        if unauthorized:
            raise SqlValidationError(f"查询访问了未授权表：{', '.join(sorted(unauthorized))}")
        return tables

    @staticmethod
    def _apply_row_limit(statement: exp.Query, row_limit: int) -> None:
        limit = statement.args.get("limit")
        if limit is None:
            statement.set("limit", exp.Limit(expression=exp.Literal.number(row_limit)))
            return

        limit_expression = limit.expression
        if not isinstance(limit_expression, exp.Literal) or not limit_expression.is_int:
            raise SqlValidationError("LIMIT 必须是整数常量")
        if int(limit_expression.this) > row_limit:
            limit.set("expression", exp.Literal.number(row_limit))
