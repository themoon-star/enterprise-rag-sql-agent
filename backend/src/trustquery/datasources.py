"""只读数据源配置、凭证加密与租户隔离。"""

from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from trustquery.models import Datasource, Tenant
from trustquery.security import TenantContext


class DatasourceConfigurationError(ValueError):
    """数据源配置格式或凭证不符合安全约束。"""


class CredentialCipher:
    """使用 Fernet 对数据源连接串执行认证加密。"""

    def __init__(self, key: str) -> None:
        try:
            self.fernet = Fernet(key.encode())
        except (TypeError, ValueError) as exc:
            message = "APP_CREDENTIAL_ENCRYPTION_KEY 必须是有效 Fernet 密钥"
            raise DatasourceConfigurationError(message) from exc

    def encrypt(self, value: str) -> str:
        """加密包含数据库凭证的连接串。"""

        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        """仅在连接数据库前解密连接串。"""

        try:
            return self.fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise DatasourceConfigurationError("无法解密数据源凭证") from exc


def validate_postgres_url(database_url: str) -> str:
    """仅接受包含完整身份信息的 PostgreSQL 连接串。"""

    try:
        url = make_url(database_url)
    except Exception as exc:
        raise DatasourceConfigurationError("数据库连接串格式无效") from exc

    if url.get_backend_name() != "postgresql":
        raise DatasourceConfigurationError("当前仅支持 PostgreSQL 数据源")
    if not all((url.username, url.password, url.host, url.database)):
        raise DatasourceConfigurationError("PostgreSQL 连接串必须包含用户、密码、主机和数据库名")
    return url.render_as_string(hide_password=False)


@dataclass(frozen=True, slots=True)
class DatasourceRecord:
    """供安全问数内部使用的数据源快照，不直接序列化到 API。"""

    id: str
    tenant_id: str
    name: str
    encrypted_url: str
    allowed_tables: frozenset[str]
    row_limit: int
    statement_timeout_ms: int


def _to_record(datasource: Datasource) -> DatasourceRecord:
    return DatasourceRecord(
        id=datasource.id,
        tenant_id=datasource.tenant_id,
        name=datasource.name,
        encrypted_url=datasource.encrypted_url,
        allowed_tables=frozenset(datasource.allowed_tables),
        row_limit=datasource.row_limit,
        statement_timeout_ms=datasource.statement_timeout_ms,
    )


class DatasourceRepository:
    """在可信租户边界内管理加密数据源配置。"""

    def __init__(self, session: AsyncSession, cipher: CredentialCipher) -> None:
        self.session = session
        self.cipher = cipher

    async def create(
        self,
        context: TenantContext,
        *,
        name: str,
        database_url: str,
        allowed_tables: list[str],
        row_limit: int,
        statement_timeout_ms: int,
    ) -> DatasourceRecord:
        """验证并加密保存当前租户的数据源凭证。"""

        if await self.session.get(Tenant, context.tenant_id) is None:
            self.session.add(Tenant(id=context.tenant_id, name=context.tenant_id))

        datasource = Datasource(
            tenant_id=context.tenant_id,
            name=name,
            encrypted_url=self.cipher.encrypt(validate_postgres_url(database_url)),
            allowed_tables=sorted(set(allowed_tables)),
            row_limit=row_limit,
            statement_timeout_ms=statement_timeout_ms,
        )
        self.session.add(datasource)
        await self.session.commit()
        await self.session.refresh(datasource)
        return _to_record(datasource)

    async def get(self, context: TenantContext, datasource_id: str) -> DatasourceRecord | None:
        """获取当前租户的数据源；跨租户访问统一表现为不存在。"""

        datasource = await self.session.scalar(
            select(Datasource).where(
                Datasource.id == datasource_id,
                Datasource.tenant_id == context.tenant_id,
            )
        )
        return _to_record(datasource) if datasource else None

    async def list(self, context: TenantContext) -> list[DatasourceRecord]:
        """列出当前租户数据源，但不解密凭证。"""

        result = await self.session.scalars(
            select(Datasource).where(Datasource.tenant_id == context.tenant_id).order_by(Datasource.name)
        )
        return [_to_record(datasource) for datasource in result]
