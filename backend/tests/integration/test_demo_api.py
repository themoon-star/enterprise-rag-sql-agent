"""演示模式会话与种子数据测试。"""

from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from trustquery.app import create_app
from trustquery.config import Settings


def settings(tmp_path: Path, *, demo_mode: bool) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'demo.db'}",
        secret_key="demo-api-test-secret-key-with-32-characters",
        credential_encryption_key=Fernet.generate_key().decode(),
        demo_mode=demo_mode,
    )


def test_demo_session_is_hidden_when_mode_is_disabled(tmp_path: Path) -> None:
    with TestClient(create_app(settings(tmp_path, demo_mode=False))) as client:
        assert client.post("/api/demo/session").status_code == 404


def test_demo_session_can_access_seeded_documents(tmp_path: Path) -> None:
    with TestClient(create_app(settings(tmp_path, demo_mode=True))) as client:
        session = client.post("/api/demo/session")
        assert session.status_code == 200

        headers = {"Authorization": f"Bearer {session.json()['access_token']}"}
        documents = client.get("/api/documents", headers=headers)

        assert documents.status_code == 200
        assert len(documents.json()) == 3
        assert session.json()["tenant_name"] == "Acme 华东事业部"
