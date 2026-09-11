"""OpenAI-compatible 模型边界测试。"""

import json

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError
from trustquery.config import Settings
from trustquery.llm import ModelAdapterError, OpenAICompatibleClient
from trustquery.rag.generator import AnswerEvidence, OpenAIAnswerGenerator
from trustquery.sql.generator import OpenAISqlGenerator, SqlGenerationError


def settings_kwargs() -> dict[str, str]:
    """返回测试配置所需的非生产值。"""

    return {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "secret_key": "test-" + "l" * 40,
        "credential_encryption_key": Fernet.generate_key().decode(),
    }


def mock_client(content: str) -> tuple[OpenAICompatibleClient, list[httpx.Request]]:
    """构建记录请求且返回固定模型响应的客户端。"""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return (
        OpenAICompatibleClient(
            base_url="https://model.example/v1",
            api_key="test-" + "model-key",
            model="test-model",
            client=http_client,
        ),
        requests,
    )


def test_online_mode_requires_model_and_key() -> None:
    with pytest.raises(ValidationError, match="LLM_API_KEY"):
        Settings(**settings_kwargs(), llm_mode="openai")


@pytest.mark.asyncio
async def test_client_sends_openai_compatible_json_request() -> None:
    client, requests = mock_client('{"answer":"仅基于证据的回答"}')

    payload = await client.complete_json(system_prompt="system", user_prompt="user")

    request_payload = json.loads(requests[0].content)
    assert payload == {"answer": "仅基于证据的回答"}
    assert requests[0].url == "https://model.example/v1/chat/completions"
    assert requests[0].headers["authorization"] == "Bearer " + "test-" + "model-key"
    assert request_payload["model"] == "test-model"
    assert request_payload["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_client_rejects_non_json_content() -> None:
    client, _ = mock_client("not-json")

    with pytest.raises(ModelAdapterError, match="合法 JSON"):
        await client.complete_json(system_prompt="system", user_prompt="user")


@pytest.mark.asyncio
async def test_rag_adapter_only_sends_supplied_evidence() -> None:
    client, requests = mock_client('{"answer":"员工需要提交电子发票。"}')
    generator = OpenAIAnswerGenerator(client)
    evidence = (
        AnswerEvidence(
            title="差旅报销制度",
            excerpt="员工需要提交电子发票。",
            source_uri="policy://travel",
        ),
    )

    answer = await generator.generate("需要什么材料？", evidence)

    request_payload = json.loads(requests[0].content)
    assert answer == "员工需要提交电子发票。"
    assert "差旅报销制度" in request_payload["messages"][1]["content"]
    assert "authorized_schema" not in request_payload["messages"][1]["content"]


@pytest.mark.asyncio
async def test_sql_adapter_sends_only_authorized_schema() -> None:
    client, requests = mock_client('{"sql":"SELECT COUNT(*) FROM sales_orders"}')
    generator = OpenAISqlGenerator(client)

    sql = await generator.generate("订单数量", {"sales_orders": ("id", "total_amount")})

    request_payload = json.loads(requests[0].content)
    user_payload = json.loads(request_payload["messages"][1]["content"])
    assert sql == "SELECT COUNT(*) FROM sales_orders"
    assert user_payload["authorized_schema"] == {
        "sales_orders": ["id", "total_amount"],
    }


@pytest.mark.asyncio
async def test_sql_adapter_rejects_missing_sql_field() -> None:
    client, _ = mock_client('{"answer":"wrong shape"}')
    generator = OpenAISqlGenerator(client)

    with pytest.raises(SqlGenerationError, match="sql 字段"):
        await generator.generate("订单数量", {"sales_orders": ("id",)})
