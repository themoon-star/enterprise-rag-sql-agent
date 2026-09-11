"""HTTP API 的输入输出模型。"""

from typing import Literal

from pydantic import BaseModel, Field


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
