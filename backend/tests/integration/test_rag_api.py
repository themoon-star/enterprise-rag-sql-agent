"""RAG API 租户隔离与回答决策集成测试。"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from trustquery.app import create_app
from trustquery.config import Settings
from trustquery.security import create_access_token


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        secret_key="integration-test-secret-key-with-32-characters",
        credential_encryption_key=Fernet.generate_key().decode(),
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def authorization(settings: Settings, tenant_id: str, *roles: str) -> dict[str, str]:
    token = create_access_token(
        settings,
        tenant_id=tenant_id,
        user_id=f"{tenant_id}-user",
        roles=set(roles),
    )
    return {"Authorization": f"Bearer {token}"}


def create_document(
    client: TestClient,
    settings: Settings,
    tenant_id: str,
    *,
    title: str,
    content: str,
    allowed_roles: list[str] | None = None,
) -> dict[str, object]:
    response = client.post(
        "/api/documents",
        headers=authorization(settings, tenant_id, "admin"),
        json={"title": title, "content": content, "allowed_roles": allowed_roles or []},
    )
    assert response.status_code == 201
    return response.json()


def test_missing_and_tampered_tokens_are_rejected(client: TestClient, settings: Settings) -> None:
    assert client.post("/api/rag/query", json={"question": "差旅报销流程"}).status_code == 401

    headers = authorization(settings, "tenant-a", "employee")
    headers["Authorization"] = f"{headers['Authorization'][:-1]}x"
    assert (
        client.post("/api/rag/query", headers=headers, json={"question": "差旅报销流程"}).status_code == 401
    )


def test_answer_contains_accessible_citation(client: TestClient, settings: Settings) -> None:
    document = create_document(
        client,
        settings,
        "tenant-a",
        title="差旅报销制度",
        content="员工应提交电子发票、出差审批单和行程凭证。财务将在五个工作日内审核。",
    )

    response = client.post(
        "/api/rag/query",
        headers=authorization(settings, "tenant-a", "employee"),
        json={"question": "差旅报销需要提交哪些材料"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["citations"][0]["document_id"] == document["id"]
    assert "电子发票" in body["answer"]
    assert body["trace"]["decision"] == "evidence_found"


def test_acl_filter_happens_before_ranking(client: TestClient, settings: Settings) -> None:
    create_document(
        client,
        settings,
        "tenant-a",
        title="董事会薪酬规则",
        content="星云奖金仅董事会成员可查阅。",
        allowed_roles=["board"],
    )

    response = client.post(
        "/api/rag/query",
        headers=authorization(settings, "tenant-a", "employee"),
        json={"question": "星云奖金如何计算"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "refused"
    assert response.json()["trace"]["accessible_candidates"] == 0


def test_cross_tenant_document_is_hidden_as_404(client: TestClient, settings: Settings) -> None:
    document = create_document(
        client,
        settings,
        "tenant-b",
        title="租户 B 私有制度",
        content="量子鳄鱼项目预算仅租户 B 可见。",
    )

    lookup = client.get(
        f"/api/documents/{document['id']}",
        headers=authorization(settings, "tenant-a", "admin"),
    )
    query = client.post(
        "/api/rag/query",
        headers=authorization(settings, "tenant-a", "employee"),
        json={"question": "量子鳄鱼项目预算是多少"},
    )

    assert lookup.status_code == 404
    assert query.status_code == 200
    assert query.json()["status"] == "refused"


def test_short_question_requests_clarification(client: TestClient, settings: Settings) -> None:
    response = client.post(
        "/api/rag/query",
        headers=authorization(settings, "tenant-a", "employee"),
        json={"question": "费用"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "clarification"
    assert response.json()["citations"] == []
