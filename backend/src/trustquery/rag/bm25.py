"""无需外部服务的轻量 BM25 检索器。"""

import math
import re
from collections import Counter
from dataclasses import dataclass

TERM_PATTERN = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    """将英文词与中文二元词组转为统一检索词元。"""

    terms: list[str] = []
    for match in TERM_PATTERN.findall(text.lower()):
        if match.isascii():
            terms.append(match)
            continue
        if len(match) == 1:
            terms.append(match)
            continue
        terms.append(match)
        terms.extend(match[index : index + 2] for index in range(len(match) - 1))
    return terms


@dataclass(frozen=True, slots=True)
class RankedItem:
    """BM25 排序后的原始下标和相关性分数。"""

    index: int
    score: float


def rank(query: str, documents: list[str], *, k1: float = 1.5, b: float = 0.75) -> list[RankedItem]:
    """按 BM25 分数降序返回所有文档。"""

    if not documents:
        return []

    tokenized_documents = [tokenize(document) for document in documents]
    query_terms = set(tokenize(query))
    average_length = sum(map(len, tokenized_documents)) / len(tokenized_documents) or 1.0
    document_frequencies = {
        term: sum(term in tokens for tokens in tokenized_documents) for term in query_terms
    }

    ranked: list[RankedItem] = []
    for index, tokens in enumerate(tokenized_documents):
        frequencies = Counter(tokens)
        score = 0.0
        for term in query_terms:
            document_frequency = document_frequencies[term]
            inverse_frequency = math.log(
                1 + (len(documents) - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            frequency = frequencies[term]
            normalizer = frequency + k1 * (1 - b + b * len(tokens) / average_length)
            if frequency:
                score += inverse_frequency * frequency * (k1 + 1) / normalizer
        ranked.append(RankedItem(index=index, score=round(score, 6)))

    return sorted(ranked, key=lambda item: (-item.score, item.index))
