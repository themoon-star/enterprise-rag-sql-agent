"""带 ACL、拒答、澄清和引用的 RAG 服务。"""

import re
from dataclasses import dataclass

from trustquery.rag.bm25 import rank, tokenize
from trustquery.repositories import DocumentRecord, DocumentRepository
from trustquery.security import TenantContext

SENTENCE_PATTERN = re.compile(r"[^。！？.!?\n]+[。！？.!?]?")


@dataclass(frozen=True, slots=True)
class Citation:
    """回答中可检查的来源证据。"""

    document_id: str
    title: str
    source_uri: str
    score: float
    excerpt: str


@dataclass(frozen=True, slots=True)
class RetrievalTrace:
    """不含敏感内容的检索决策摘要。"""

    accessible_candidates: int
    ranked_candidates: int
    decision: str


@dataclass(frozen=True, slots=True)
class RagResult:
    """RAG 主链路的结构化输出。"""

    status: str
    answer: str
    citations: tuple[Citation, ...]
    trace: RetrievalTrace


class RagService:
    """只在可访问知识范围内检索并生成证据化回答。"""

    def __init__(self, repository: DocumentRepository, *, minimum_score: float = 0.2) -> None:
        self.repository = repository
        self.minimum_score = minimum_score

    async def query(self, context: TenantContext, question: str, *, top_k: int = 3) -> RagResult:
        """执行 ACL 过滤、BM25 排序与证据化回答。"""

        normalized_question = question.strip()
        if len(normalized_question) <= 2:
            return RagResult(
                status="clarification",
                answer="请补充你要查询的制度、流程或具体场景。",
                citations=(),
                trace=RetrievalTrace(0, 0, "question_too_ambiguous"),
            )

        documents = await self.repository.list_accessible(context)
        ranked = rank(normalized_question, [self._search_text(document) for document in documents])
        accepted = [item for item in ranked if item.score >= self.minimum_score][:top_k]
        if not accepted:
            return RagResult(
                status="refused",
                answer="当前可访问知识中没有足够证据回答该问题。",
                citations=(),
                trace=RetrievalTrace(len(documents), len(ranked), "insufficient_evidence"),
            )

        citations = tuple(
            self._citation(documents[item.index], item.score, normalized_question) for item in accepted
        )
        primary = citations[0]
        return RagResult(
            status="answered",
            answer=f"根据《{primary.title}》：{primary.excerpt}",
            citations=citations,
            trace=RetrievalTrace(len(documents), len(ranked), "evidence_found"),
        )

    @staticmethod
    def _search_text(document: DocumentRecord) -> str:
        return f"{document.title}\n{document.content}"

    @staticmethod
    def _citation(document: DocumentRecord, score: float, question: str) -> Citation:
        query_terms = set(tokenize(question))
        sentences = [
            sentence.strip() for sentence in SENTENCE_PATTERN.findall(document.content) if sentence.strip()
        ]
        excerpt = max(
            sentences or [document.content],
            key=lambda sentence: len(query_terms.intersection(tokenize(sentence))),
        )
        return Citation(
            document_id=document.id,
            title=document.title,
            source_uri=document.source_uri,
            score=score,
            excerpt=excerpt[:240],
        )
