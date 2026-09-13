"""Pipeline truy xuất Phase 3, gộp các bước theo cờ trong settings:

  câu hỏi -> [rewrite] -> [hybrid|vector] (+lọc metadata) -> [rerank] -> [MMR] -> top_k

Mỗi bước bật/tắt qua config để dễ so sánh chất lượng (A/B khi làm eval Phase 5).
"""
from config import settings
from retrieval.query_transform import rewrite_query
from retrieval.hybrid import hybrid_search
from retrieval.vector import search as vector_search
from retrieval.rerank import rerank
from retrieval.mmr import mmr_select


def retrieve(question: str, where: dict | None = None) -> tuple[list[dict], dict]:
    """Trả về (chunks, info).
    where: lọc theo metadata, vd {'category': 'web'} hoặc {'vuln_class': 'xss'}.
    info['rewritten'] = câu truy vấn thực sự đã dùng."""
    query = rewrite_query(question)

    if settings.USE_HYBRID:
        candidates = hybrid_search(query, k=settings.CANDIDATES_K, where=where)
    else:
        candidates = vector_search(query, top_k=settings.CANDIDATES_K, where=where)

    # rerank chấm điểm toàn bộ ứng viên (chưa cắt) để MMR còn nhiều lựa chọn
    if settings.USE_RERANK:
        candidates = rerank(query, candidates)

    if settings.USE_MMR:
        chunks = mmr_select(candidates, k=settings.TOP_K)
    else:
        chunks = candidates[: settings.TOP_K]

    return chunks, {"rewritten": query}
