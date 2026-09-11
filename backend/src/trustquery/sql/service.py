"""安全 Text-to-SQL 编排与单次自修复。"""

from dataclasses import dataclass
from typing import Any, Protocol

from trustquery.datasources import DatasourceRecord
from trustquery.sql.executor import QueryExecution, SqlExecutionError
from trustquery.sql.generator import SqlCandidateGenerator, SqlGenerationError
from trustquery.sql.validator import SqlValidationError, SqlValidator, ValidatedQuery


class QueryExecutor(Protocol):
    """Text-to-SQL 服务依赖的最小执行器接口。"""

    async def introspect(self, datasource: DatasourceRecord) -> dict[str, tuple[str, ...]]:
        """返回授权表的 schema。"""

    async def execute(self, datasource: DatasourceRecord, query: ValidatedQuery) -> QueryExecution:
        """执行已经验证的查询。"""


@dataclass(frozen=True, slots=True)
class SqlQueryResult:
    """安全问数的结构化结果与审计摘要。"""

    status: str
    sql: str | None
    repaired: bool
    execution_attempts: int
    columns: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]
    decision: str


class TextToSqlService:
    """生成、验证、执行，并在首次执行失败后至多修复一次。"""

    def __init__(
        self,
        *,
        generator: SqlCandidateGenerator,
        executor: QueryExecutor,
        validator: SqlValidator | None = None,
    ) -> None:
        self.generator = generator
        self.executor = executor
        self.validator = validator or SqlValidator()

    async def query(self, datasource: DatasourceRecord, question: str) -> SqlQueryResult:
        """执行安全 Text-to-SQL 主链路。"""

        try:
            schema = await self.executor.introspect(datasource)
            candidate = await self.generator.generate(question.strip(), schema)
            validated = self._validate(candidate, datasource)
        except SqlGenerationError:
            return self._result("blocked", None, False, 0, "generation_needs_clarification")
        except SqlValidationError:
            return self._result("blocked", candidate, False, 0, "initial_sql_rejected")
        except SqlExecutionError:
            return self._result("failed", None, False, 0, "schema_unavailable")

        try:
            execution = await self.executor.execute(datasource, validated)
            return self._success(validated.sql, False, 1, execution)
        except SqlExecutionError:
            return await self._repair_once(datasource, question, schema, validated.sql)

    async def _repair_once(
        self,
        datasource: DatasourceRecord,
        question: str,
        schema: dict[str, tuple[str, ...]],
        failed_sql: str,
    ) -> SqlQueryResult:
        try:
            repaired_candidate = await self.generator.repair(
                question.strip(),
                schema,
                failed_sql,
                "database_execution_error",
            )
            repaired_query = self._validate(repaired_candidate, datasource)
        except (SqlGenerationError, SqlValidationError):
            return self._result("blocked", failed_sql, True, 1, "repaired_sql_rejected")

        try:
            execution = await self.executor.execute(datasource, repaired_query)
            return self._success(repaired_query.sql, True, 2, execution)
        except SqlExecutionError:
            return self._result("failed", repaired_query.sql, True, 2, "repair_exhausted")

    def _validate(self, sql: str, datasource: DatasourceRecord) -> ValidatedQuery:
        return self.validator.validate(
            sql,
            allowed_tables=datasource.allowed_tables,
            row_limit=datasource.row_limit,
        )

    @staticmethod
    def _success(sql: str, repaired: bool, attempts: int, execution: QueryExecution) -> SqlQueryResult:
        return SqlQueryResult(
            status="succeeded",
            sql=sql,
            repaired=repaired,
            execution_attempts=attempts,
            columns=execution.columns,
            rows=execution.rows,
            decision="query_executed",
        )

    @staticmethod
    def _result(status: str, sql: str | None, repaired: bool, attempts: int, decision: str) -> SqlQueryResult:
        return SqlQueryResult(
            status=status,
            sql=sql,
            repaired=repaired,
            execution_attempts=attempts,
            columns=(),
            rows=(),
            decision=decision,
        )
