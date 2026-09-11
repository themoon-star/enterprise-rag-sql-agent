"""租户知识文档与 RAG API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from trustquery.db import get_session
from trustquery.rag.service import RagService
from trustquery.repositories import DocumentRecord, DocumentRepository
from trustquery.schemas import DocumentCreate, DocumentOutput, RagQueryInput, RagQueryOutput
from trustquery.security import TenantContext, get_tenant_context, require_roles

router = APIRouter(prefix="/api")


def _document_output(document: DocumentRecord) -> DocumentOutput:
    return DocumentOutput(
        id=document.id,
        title=document.title,
        content=document.content,
        source_uri=document.source_uri,
        allowed_roles=sorted(document.allowed_roles),
    )


@router.post("/documents", response_model=DocumentOutput, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    context: Annotated[TenantContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentOutput:
    """在当前令牌租户中创建知识文档。"""

    document = await DocumentRepository(session).create(context, **payload.model_dump())
    return _document_output(document)


@router.get("/documents/{document_id}", response_model=DocumentOutput)
async def get_document(
    document_id: str,
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentOutput:
    """获取当前租户且当前角色可见的文档。"""

    document = await DocumentRepository(session).get_accessible(context, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    return _document_output(document)


@router.post("/rag/query", response_model=RagQueryOutput)
async def query_knowledge(
    payload: RagQueryInput,
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RagQueryOutput:
    """在可信租户和角色边界内执行知识问答。"""

    result = await RagService(DocumentRepository(session)).query(
        context,
        payload.question,
        top_k=payload.top_k,
    )
    return RagQueryOutput.model_validate(result, from_attributes=True)
