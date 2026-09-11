"""RAG 回答生成器接口与实现。"""

from dataclasses import dataclass
from typing import Protocol

from trustquery.llm import ModelAdapterError, OpenAICompatibleClient


class AnswerGenerationError(RuntimeError):
    """模型无法基于给定证据生成回答。"""


@dataclass(frozen=True, slots=True)
class AnswerEvidence:
    """允许传入回答生成器的最小证据字段。"""

    title: str
    excerpt: str
    source_uri: str


class RagAnswerGenerator(Protocol):
    """可替换的证据回答生成接口。"""

    async def generate(self, question: str, evidence: tuple[AnswerEvidence, ...]) -> str:
        """仅基于已经完成权限过滤的证据生成回答。"""


class ExtractiveAnswerGenerator:
    """用于离线验收的确定性摘录式回答生成器。"""

    async def generate(self, question: str, evidence: tuple[AnswerEvidence, ...]) -> str:
        """返回首条证据的可复现摘要。"""

        _ = question
        primary = evidence[0]
        return f"根据《{primary.title}》：{primary.excerpt}"


class OpenAIAnswerGenerator:
    """通过 OpenAI-compatible 接口生成受证据约束的回答。"""

    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

    async def generate(self, question: str, evidence: tuple[AnswerEvidence, ...]) -> str:
        """只把已授权证据发送给模型，并要求返回结构化回答。"""

        evidence_text = "\n\n".join(
            f"[{index}] {item.title}\n{item.excerpt}\n来源: {item.source_uri}"
            for index, item in enumerate(evidence, start=1)
        )
        try:
            payload = await self.client.complete_json(
                system_prompt=(
                    "你是企业知识问答助手。只能使用提供的证据回答，不得补充外部事实；"
                    "证据不足时回答无法确认。返回 JSON 对象，唯一字段为 answer。"
                ),
                user_prompt=f"问题：{question}\n\n证据：\n{evidence_text}",
            )
        except ModelAdapterError as error:
            raise AnswerGenerationError("回答模型调用失败") from error

        answer = payload.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise AnswerGenerationError("回答模型缺少 answer 字段")
        return answer.strip()[:2_000]
