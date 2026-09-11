"""JWT 身份校验与 FastAPI 鉴权依赖。"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from trustquery.config import Settings


@dataclass(frozen=True, slots=True)
class TenantContext:
    """由服务端验签后的令牌派生出的租户身份。"""

    tenant_id: str
    user_id: str
    roles: frozenset[str]


def create_access_token(
    settings: Settings,
    *,
    tenant_id: str,
    user_id: str,
    roles: set[str],
    expires_in: timedelta | None = None,
) -> str:
    """签发用于本地演示和测试的短期访问令牌。"""

    now = datetime.now(UTC)
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": user_id,
        "tenant_id": tenant_id,
        "roles": sorted(roles),
        "iat": now,
        "exp": now + (expires_in or timedelta(minutes=settings.access_token_minutes)),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(settings: Settings, token: str) -> TenantContext:
    """验签令牌并返回不可由请求正文覆盖的租户上下文。"""

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "tenant_id", "roles"]},
        )
        tenant_id = str(payload["tenant_id"]).strip()
        user_id = str(payload["sub"]).strip()
        roles = payload["roles"]
        if not tenant_id or not user_id or not isinstance(roles, list):
            raise ValueError("令牌身份字段无效")
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("访问令牌无效或已过期") from exc

    return TenantContext(tenant_id=tenant_id, user_id=user_id, roles=frozenset(map(str, roles)))


bearer_scheme = HTTPBearer(auto_error=False)


async def get_tenant_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> TenantContext:
    """从 Bearer Token 构造可信租户上下文。"""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少访问令牌")

    try:
        return decode_access_token(request.app.state.settings, credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def require_roles(*required_roles: str):
    """生成要求至少一个指定角色的鉴权依赖。"""

    async def dependency(
        context: Annotated[TenantContext, Depends(get_tenant_context)],
    ) -> TenantContext:
        if context.roles.isdisjoint(required_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前角色无权执行此操作")
        return context

    return dependency
