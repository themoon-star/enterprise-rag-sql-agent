"""Text-to-SQL 候选生成接口、在线适配器与可复现规则生成器。"""

import json
from typing import Protocol

from sqlglot import exp

from trustquery.llm import ModelAdapterError, OpenAICompatibleClient


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
        numeric_names = {"amount", "total_amount", "revenue", "price"}
        numeric_column = next(
            (column for column in columns if column.lower() in numeric_names),
            None,
        )
        average_keywords = ("平均", "均值", "average")
        if numeric_column and any(keyword in lowered_question for keyword in average_keywords):
            average = exp.alias_(exp.Avg(this=exp.column(numeric_column)), "average_value")
            return self._select(table, average)

        total_keywords = ("销售额", "营收", "总额", "金额")
        if numeric_column and any(keyword in lowered_question for keyword in total_keywords):
            total = exp.alias_(exp.Sum(this=exp.column(numeric_column)), "total_value")
            return self._select(table, total)

        count_keywords = ("数量", "多少", "count", "总数", "几条", "记录数", "数一下")
        if any(keyword in lowered_question for keyword in count_keywords):
            count = exp.alias_(exp.Count(this=exp.Star()), "record_count")
            return self._select(table, count)

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
        table_aliases = {
            "sales_orders": ("订单", "销售", "营收"),
            "customers": ("客户",),
        }
        mentioned = [
            table
            for table in schema
            if table.lower() in lowered_question
            or any(alias in lowered_question for alias in table_aliases.get(table.lower(), ()))
        ]
        if mentioned:
            return sorted(mentioned)[0]
        if len(schema) == 1:
            return next(iter(schema))
        raise SqlGenerationError("问题未明确对应的数据表，请补充业务对象")

    @staticmethod
    def _select(table: str, *expressions: exp.Expression) -> str:
        """通过 AST 构造只引用已探测标识符的 PostgreSQL 查询。"""

        return exp.select(*expressions).from_(exp.to_table(table)).sql(dialect="postgres")


class OpenAISqlGenerator:
    """通过 OpenAI-compatible 接口生成 SQL 候选，安全性仍由生产验证器决定。"""

    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

    async def generate(self, question: str, schema: dict[str, tuple[str, ...]]) -> str:
        """仅向模型暴露当前租户数据源的授权 schema。"""

        return await self._complete(
            question=question,
            schema=schema,
            repair_context=None,
        )

    async def repair(
        self,
        question: str,
        schema: dict[str, tuple[str, ...]],
        failed_sql: str,
        error_code: str,
    ) -> str:
        """基于脱敏错误类型生成一次新候选，不绕过后续完整校验。"""

        return await self._complete(
            question=question,
            schema=schema,
            repair_context={"failed_sql": failed_sql, "error_code": error_code},
        )

    async def _complete(
        self,
        *,
        question: str,
        schema: dict[str, tuple[str, ...]],
        repair_context: dict[str, str] | None,
    ) -> str:
        if not schema:
            raise SqlGenerationError("数据源没有可用的授权表")

        prompt = {
            "question": question,
            "authorized_schema": {table: list(columns) for table, columns in schema.items()},
        }
        if repair_context is not None:
            prompt["repair_context"] = repair_context

        try:
            payload = await self.client.complete_json(
                system_prompt=(
                    "你是 PostgreSQL 查询规划器。只生成一个只读 SELECT 或 WITH 查询；"
                    "只能引用 authorized_schema 中的表和列，不得使用注释或多语句。"
                    "返回 JSON 对象，唯一字段为 sql。"
                ),
                user_prompt=json.dumps(prompt, ensure_ascii=False),
            )
        except ModelAdapterError as error:
            raise SqlGenerationError("SQL 模型调用失败") from error

        sql = payload.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            raise SqlGenerationError("SQL 模型缺少 sql 字段")
        return sql.strip()
