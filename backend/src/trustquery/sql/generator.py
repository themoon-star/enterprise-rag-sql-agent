"""Text-to-SQL 候选生成接口与可复现规则生成器。"""

from typing import Protocol

from sqlglot import exp


class SqlGenerationError(RuntimeError):
    """当前生成器无法为问题生成 SQL。"""


class SqlCandidateGenerator(Protocol):
    """SQL 首次生成与单次修复的统一接口。"""

    async def generate(self, question: str, schema: dict[str, tuple[str, ...]]) -> str:
        """根据自然语言问题和授权 schema 生成 SQL。"""

    async def repair(
        self,
        question: str,
        schema: dict[str, tuple[str, ...]],
        failed_sql: str,
        error_code: str,
    ) -> str:
        """基于执行失败类型生成一次修复候选。"""


class DeterministicSqlGenerator:
    """用于离线验收和演示的可解释 SQL 生成器。"""

    async def generate(self, question: str, schema: dict[str, tuple[str, ...]]) -> str:
        """用受控意图规则生成仅引用真实 schema 的查询。"""

        if not schema:
            raise SqlGenerationError("数据源没有可用的授权表")

        table = self._choose_table(question, schema)
        columns = schema[table]
        lowered_question = question.lower()
        if any(keyword in lowered_question for keyword in ("数量", "多少", "count")):
            count = exp.alias_(exp.Count(this=exp.Star()), "record_count")
            return self._select(table, count)

        numeric_names = {"amount", "total_amount", "revenue", "price"}
        numeric_column = next(
            (column for column in columns if column.lower() in numeric_names),
            None,
        )
        total_keywords = ("销售额", "营收", "总额", "金额")
        if numeric_column and any(keyword in lowered_question for keyword in total_keywords):
            total = exp.alias_(exp.Sum(this=exp.column(numeric_column)), "total_value")
            return self._select(table, total)
        if numeric_column and any(keyword in lowered_question for keyword in ("平均", "均值", "average")):
            average = exp.alias_(exp.Avg(this=exp.column(numeric_column)), "average_value")
            return self._select(table, average)

        selected_columns = [exp.column(column) for column in columns[:6]] or [exp.Star()]
        return self._select(table, *selected_columns)

    async def repair(
        self,
        question: str,
        schema: dict[str, tuple[str, ...]],
        failed_sql: str,
        error_code: str,
    ) -> str:
        """重新从已探测 schema 生成一次候选，不复用失败 SQL。"""

        _ = failed_sql, error_code
        return await self.generate(question, schema)

    @staticmethod
    def _choose_table(question: str, schema: dict[str, tuple[str, ...]]) -> str:
        lowered_question = question.lower()
        mentioned = [table for table in schema if table.lower() in lowered_question]
        if mentioned:
            return sorted(mentioned)[0]
        if len(schema) == 1:
            return next(iter(schema))
        raise SqlGenerationError("问题未明确对应的数据表，请补充业务对象")

    @staticmethod
    def _select(table: str, *expressions: exp.Expression) -> str:
        """通过 AST 构造只引用已探测标识符的 PostgreSQL 查询。"""

        return exp.select(*expressions).from_(exp.to_table(table)).sql(dialect="postgres")
