"""OpenAI-compatible 模型访问边界。"""

import json
from typing import Any

import httpx


class ModelAdapterError(RuntimeError):
    """模型请求失败或响应不符合约定。"""


class OpenAICompatibleClient:
    """以最小 Chat Completions 协议调用显式配置的模型服务。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """请求一个 JSON 对象，并拒绝非标准或空响应。"""

        try:
            response = await self._client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise ModelAdapterError("模型服务请求或响应解析失败") from error

        if not isinstance(content, str) or not content.strip():
            raise ModelAdapterError("模型返回了空内容")

        try:
            parsed = json.loads(content)
        except ValueError as error:
            raise ModelAdapterError("模型没有返回合法 JSON") from error
        if not isinstance(parsed, dict):
            raise ModelAdapterError("模型响应必须是 JSON 对象")
        return parsed

    async def close(self) -> None:
        """关闭由适配器创建的 HTTP 连接池。"""

        if self._owns_client:
            await self._client.aclose()
