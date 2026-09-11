"""租户知识文档与 RAG API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from trustquery.datasources import CredentialCipher, DatasourceRecord, DatasourceRepository
from trustquery.db import get_session
from trustquery.rag.service import RagService
from trustquery.repositories import DocumentRecord, DocumentRepository
from trustquery.schemas import (
    DatasourceCreate,
    DatasourceOutput,
    DemoSessionOutput,
    DocumentCreate,
    DocumentOutput,
    RagQueryInput,
    RagQueryOutput,
    SqlQueryInput,
    SqlQueryOutput,
)
from trustquery.security import TenantContext, create_access_token, get_tenant_context, require_roles
from trustquery.sql.service import TextToSqlService

router = APIRouter(prefix="/api")


def _document_output(document: DocumentRecord) -> DocumentOutput:
    return DocumentOutput(
        id=document.id,
        title=document.title,
        content=document.content,
        source_uri=document.source_uri,
        allowed_roles=sorted(document.allowed_roles),
    )


def _datasource_output(datasource: DatasourceRecord) -> DatasourceOutput:
    return DatasourceOutput(
        id=datasource.id,
        name=datasource.name,
        allowed_tables=sorted(datasource.allowed_tables),
        row_limit=datasource.row_limit,
        statement_timeout_ms=datasource.statement_timeout_ms,
    )


def _datasource_repository(session: AsyncSession, key: str) -> DatasourceRepository:
    return DatasourceRepository(session, CredentialCipher(key))


@router.post("/documents", response_model=DocumentOutput, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    context: Annotated[TenantContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentOutput:
    """在当前令牌租户中创建知识文档。"""

    document = await DocumentRepository(session).create(context, **payload.model_dump())
    return _document_output(document)


@router.get("/documents", response_model=list[DocumentOutput])
async def list_documents(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[DocumentOutput]:
    """列出当前租户与角色可访问的知识文档。"""

    documents = await DocumentRepository(session).list_accessible(context)
    return [_document_output(document) for document in documents]


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


@router.post("/datasources", response_model=DatasourceOutput, status_code=status.HTTP_201_CREATED)
async def create_datasource(
    payload: DatasourceCreate,
    context: Annotated[TenantContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DatasourceOutput:
    """加密保存当前租户的只读 PostgreSQL 数据源。"""

    repository = _datasource_repository(session, session.info["credential_encryption_key"])
    datasource = await repository.create(
        context,
        **payload.model_dump(exclude={"database_url"}),
        database_url=payload.database_url.get_secret_value(),
    )
    return _datasource_output(datasource)


@router.get("/datasources", response_model=list[DatasourceOutput])
async def list_datasources(
    context: Annotated[TenantContext, Depends(require_roles("admin", "analyst"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[DatasourceOutput]:
    """列出当前租户可用于问数的数据源摘要。"""

    repository = _datasource_repository(session, session.info["credential_encryption_key"])
    return [_datasource_output(item) for item in await repository.list(context)]


@router.post("/sql/query", response_model=SqlQueryOutput)
async def query_datasource(
    payload: SqlQueryInput,
    context: Annotated[TenantContext, Depends(require_roles("admin", "analyst"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SqlQueryOutput:
    """对当前租户的数据源执行安全自然语言问数。"""

    repository = _datasource_repository(session, session.info["credential_encryption_key"])
    datasource = await repository.get(context, payload.datasource_id)
    if datasource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")

    result = await TextToSqlService(
        generator=session.info["sql_generator"],
        executor=session.info["sql_executor"],
    ).query(datasource, payload.question)
    return SqlQueryOutput.model_validate(result, from_attributes=True)


@router.post("/demo/session", response_model=DemoSessionOutput)
async def create_demo_session(request: Request) -> DemoSessionOutput:
    """仅在显式演示模式下签发固定租户的短期会话。"""

    settings = request.app.state.settings
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="演示模式未启用")

    roles = {"admin", "analyst", "employee"}
    token = create_access_token(
        settings,
        tenant_id="acme-demo",
        user_id="demo-admin",
        roles=roles,
    )
    return DemoSessionOutput(
        access_token=token,
        tenant_name="Acme 华东事业部",
        user_name="演示管理员",
        roles=sorted(roles),
    )
