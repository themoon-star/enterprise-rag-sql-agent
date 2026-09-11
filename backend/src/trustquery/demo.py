"""仅用于本地作品演示的确定性租户数据。"""

from sqlalchemy.ext.asyncio import AsyncSession

from trustquery.config import Settings
from trustquery.datasources import CredentialCipher, DatasourceRepository
from trustquery.repositories import DocumentRepository
from trustquery.security import TenantContext

DEMO_CONTEXT = TenantContext(
    tenant_id="acme-demo",
    user_id="demo-admin",
    roles=frozenset({"admin", "analyst", "employee"}),
)

DEMO_DOCUMENTS = (
    {
        "title": "差旅报销制度",
        "content": "员工应提交电子发票、出差审批单和行程凭证。财务将在五个工作日内完成审核。",
        "source_uri": "policy://finance/travel-v3",
        "allowed_roles": [],
    },
    {
        "title": "远程接入安全规范",
        "content": "公司 VPN 必须启用多因素认证。连续五次登录失败后，账号将锁定三十分钟。",
        "source_uri": "policy://security/remote-access-v2",
        "allowed_roles": [],
    },
    {
        "title": "季度经营复盘说明",
        "content": "经营复盘应核对已支付订单金额、区域客户数量与异常订单，数据以只读分析库为准。",
        "source_uri": "policy://finance/quarterly-review-v1",
        "allowed_roles": ["analyst"],
    },
)


async def bootstrap_demo(session: AsyncSession, settings: Settings, cipher: CredentialCipher) -> None:
    """幂等写入演示租户的知识与只读数据源。"""

    documents = DocumentRepository(session)
    if not await documents.list_accessible(DEMO_CONTEXT):
        for document in DEMO_DOCUMENTS:
            await documents.create(DEMO_CONTEXT, **document)

    datasource_url = settings.demo_datasource_url
    if datasource_url is None:
        return

    datasources = DatasourceRepository(session, cipher)
    if not await datasources.list(DEMO_CONTEXT):
        await datasources.create(
            DEMO_CONTEXT,
            name="经营分析只读库",
            database_url=datasource_url.get_secret_value(),
            allowed_tables=["customers", "sales_orders"],
            row_limit=100,
            statement_timeout_ms=2_000,
        )
