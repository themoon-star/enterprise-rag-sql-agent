"""TrustQuery 元数据模型。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from trustquery.db import Base


def new_id() -> str:
    """生成不暴露业务信息的随机主键。"""

    return uuid4().hex


class Tenant(Base):
    """隔离知识与数据源配置的企业租户。"""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))


class KnowledgeDocument(Base):
    """可按租户和角色访问的知识文档。"""

    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    source_uri: Mapped[str] = mapped_column(String(500), default="internal://manual")
    allowed_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
