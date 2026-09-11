"""JWT 租户身份边界测试。"""

from datetime import timedelta

import pytest
from trustquery.config import Settings
from trustquery.security import create_access_token, decode_access_token


def make_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        secret_key="unit-test-secret-key-with-32-characters",
    )


def test_verified_token_derives_tenant_context() -> None:
    settings = make_settings()
    token = create_access_token(
        settings,
        tenant_id="tenant-a",
        user_id="alice",
        roles={"employee", "finance"},
    )

    context = decode_access_token(settings, token)

    assert context.tenant_id == "tenant-a"
    assert context.user_id == "alice"
    assert context.roles == {"employee", "finance"}


def test_tampered_token_is_rejected() -> None:
    settings = make_settings()
    token = create_access_token(settings, tenant_id="tenant-a", user_id="alice", roles={"employee"})
    tampered_token = f"{token[:-1]}{'a' if token[-1] != 'a' else 'b'}"

    with pytest.raises(ValueError, match="访问令牌无效"):
        decode_access_token(settings, tampered_token)


def test_expired_token_is_rejected() -> None:
    settings = make_settings()
    token = create_access_token(
        settings,
        tenant_id="tenant-a",
        user_id="alice",
        roles={"employee"},
        expires_in=timedelta(seconds=-1),
    )

    with pytest.raises(ValueError, match="访问令牌无效"):
        decode_access_token(settings, token)
