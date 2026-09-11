"""租户知识文档的数据访问层。"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trustquery.models import KnowledgeDocument, Tenant
from trustquery.security import TenantContext


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """供检索层消费的不可变文档快照。"""

    id: str
    tenant_id: str
    title: str
    content: str
    source_uri: str
    allowed_roles: frozenset[str]


def _to_record(document: KnowledgeDocument) -> DocumentRecord:
    return DocumentRecord(
        id=document.id,
        tenant_id=document.tenant_id,
        title=document.title,
        content=document.content,
        source_uri=document.source_uri,
        allowed_roles=frozenset(document.allowed_roles),
    )


class DocumentRepository:
    """确保租户与角色过滤发生在检索排序之前。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_tenant(self, tenant_id: str) -> None:
        """为首次写入的演示租户创建元数据记录。"""

        if await self.session.get(Tenant, tenant_id) is None:
            self.session.add(Tenant(id=tenant_id, name=tenant_id))

    async def create(
        self,
        context: TenantContext,
        *,
        title: str,
        content: str,
        source_uri: str,
        allowed_roles: list[str],
    ) -> DocumentRecord:
        """在当前令牌租户内创建知识文档。"""

        await self.ensure_tenant(context.tenant_id)
        document = KnowledgeDocument(
            tenant_id=context.tenant_id,
            title=title,
            content=content,
            source_uri=source_uri,
            allowed_roles=sorted(set(allowed_roles)),
        )
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return _to_record(document)

    async def list_accessible(self, context: TenantContext) -> list[DocumentRecord]:
        """先按令牌租户取候选，再执行角色 ACL 过滤。"""

        result = await self.session.scalars(
            select(KnowledgeDocument).where(KnowledgeDocument.tenant_id == context.tenant_id)
        )
        is_admin = "admin" in context.roles
        return [
            _to_record(document)
            for document in result
            if is_admin or not document.allowed_roles or not context.roles.isdisjoint(document.allowed_roles)
        ]

    async def get_accessible(self, context: TenantContext, document_id: str) -> DocumentRecord | None:
        """对越租户或越角色访问统一返回不存在，避免资源枚举。"""

        document = await self.session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.tenant_id == context.tenant_id,
            )
        )
        if document is None:
            return None

        if "admin" not in context.roles and document.allowed_roles:
            if context.roles.isdisjoint(document.allowed_roles):
                return None
        return _to_record(document)
