"""HTTP API 的输入输出模型。"""

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr, field_validator

IDENTIFIER_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


class DocumentCreate(BaseModel):
    """创建租户知识文档的请求。"""

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=50_000)
    source_uri: str = Field(default="internal://manual", max_length=500)
    allowed_roles: list[str] = Field(default_factory=list, max_length=20)


class DocumentOutput(DocumentCreate):
    """不包含租户外部信息的知识文档响应。"""

    id: str


class RagQueryInput(BaseModel):
    """知识问答请求。"""

    question: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=3, ge=1, le=10)


class CitationOutput(BaseModel):
    """可核验的回答引用。"""

    document_id: str
    title: str
    source_uri: str
    score: float
    excerpt: str


class TraceOutput(BaseModel):
    """检索决策轨迹。"""

    accessible_candidates: int
    ranked_candidates: int
    decision: str


class RagQueryOutput(BaseModel):
    """RAG 回答、拒答或澄清结果。"""

    status: Literal["answered", "refused", "clarification"]
    answer: str
    citations: list[CitationOutput]
    trace: TraceOutput


class DatasourceCreate(BaseModel):
    """创建只读 PostgreSQL 数据源的请求。"""

    name: str = Field(min_length=1, max_length=120)
    database_url: SecretStr
    allowed_tables: list[str] = Field(min_length=1, max_length=50)
    row_limit: int = Field(default=200, ge=1, le=1_000)
    statement_timeout_ms: int = Field(default=3_000, ge=100, le=30_000)

    @field_validator("allowed_tables")
    @classmethod
    def validate_allowed_tables(cls, tables: list[str]) -> list[str]:
        """限制表名为不含 schema 或表达式的 PostgreSQL 标识符。"""

        normalized = [table.lower() for table in tables]
        if any(not IDENTIFIER_PATTERN.fullmatch(table) for table in normalized):
            raise ValueError("表名只能包含小写字母、数字和下划线")
        return sorted(set(normalized))


class DatasourceOutput(BaseModel):
    """不返回连接串或密文的数据源摘要。"""

    id: str
    name: str
    dialect: Literal["postgresql"] = "postgresql"
    allowed_tables: list[str]
    row_limit: int
    statement_timeout_ms: int


class SqlQueryInput(BaseModel):
    """自然语言问数请求。"""

    datasource_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=2, max_length=2_000)


class SqlQueryOutput(BaseModel):
    """安全问数结果与可检查决策状态。"""

    status: Literal["succeeded", "blocked", "failed"]
    sql: str | None
    repaired: bool
    execution_attempts: int
    columns: list[str]
    rows: list[dict[str, Any]]
    decision: str
