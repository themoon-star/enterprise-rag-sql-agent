"""轻量 BM25 检索测试。"""

from trustquery.rag.bm25 import rank, tokenize


def test_tokenize_keeps_english_and_chinese_bigrams() -> None:
    terms = tokenize("VPN 报销流程")

    assert "vpn" in terms
    assert "报销" in terms
    assert "流程" in terms


def test_rank_prefers_document_with_query_terms() -> None:
    documents = ["差旅报销需要发票和审批单", "VPN 登录需要多因素认证"]

    ranked = rank("差旅报销材料", documents)

    assert ranked[0].index == 0
    assert ranked[0].score > ranked[1].score
