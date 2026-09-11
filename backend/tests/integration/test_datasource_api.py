"""数据源凭证加密与租户隔离 API 测试。"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from trustquery.app import create_app
from trustquery.config import Settings
from trustquery.datasources import CredentialCipher
from trustquery.security import create_access_token


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'metadata.db'}",
        secret_key="test-" + "d" * 40,
        credential_encryption_key=Fernet.generate_key().decode(),
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def headers(settings: Settings, tenant_id: str, role: str = "admin") -> dict[str, str]:
    token = create_access_token(settings, tenant_id=tenant_id, user_id="tester", roles={role})
    return {"Authorization": f"Bearer {token}"}


def create_datasource(client: TestClient, settings: Settings, tenant_id: str) -> dict[str, object]:
    response = client.post(
        "/api/datasources",
        headers=headers(settings, tenant_id),
        json={
            "name": "Sales Readonly",
            "database_url": f"postgresql://readonly_user:{'test-' + 'p' * 20}@database:5432/analytics",
            "allowed_tables": ["sales_orders"],
            "row_limit": 100,
            "statement_timeout_ms": 2000,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_datasource_response_and_storage_do_not_expose_plaintext_credentials(
    client: TestClient,
    settings: Settings,
    tmp_path: Path,
) -> None:
    body = create_datasource(client, settings, "tenant-a")

    assert "database_url" not in body
    assert "password" not in str(body).lower()

    with sqlite3.connect(tmp_path / "metadata.db") as connection:
        encrypted_url = connection.execute("SELECT encrypted_url FROM datasources").fetchone()[0]
    assert "test-" + "p" * 20 not in encrypted_url
    assert "test-" + "p" * 20 in CredentialCipher(settings.credential_encryption_key).decrypt(encrypted_url)


def test_cross_tenant_datasource_is_not_listed_or_queryable(client: TestClient, settings: Settings) -> None:
    datasource = create_datasource(client, settings, "tenant-b")

    listing = client.get("/api/datasources", headers=headers(settings, "tenant-a", "analyst"))
    query = client.post(
        "/api/sql/query",
        headers=headers(settings, "tenant-a", "analyst"),
        json={"datasource_id": datasource["id"], "question": "订单数量"},
    )

    assert listing.status_code == 200
    assert listing.json() == []
    assert query.status_code == 404
