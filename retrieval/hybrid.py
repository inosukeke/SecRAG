"""Hybrid retrieval: gộp BM25 (keyword) + vector (ngữ nghĩa) bằng RRF.

- Vector bắt tốt ý nghĩa/diễn đạt khác nhau.
- BM25 bắt tốt thuật ngữ chính xác (CVE-2021-44228, tên hàm, flag công cụ) mà
  vector hay trượt.
RRF (Reciprocal Rank Fusion): điểm = Σ 1/(k + rank) qua từng bảng xếp hạng -> gộp
hai nguồn mà không cần chuẩn hoá thang điểm khác nhau của chúng.

BM25 cần toàn corpus trong RAM: nạp 1 lần từ Chroma rồi cache.
"""
import re
from rank_bm25 import BM25Okapi

from config import settings
from retrieval import store

_bm25 = None
_ids: list[str] = []
_docs: list[str] = []
_metas: list[dict] = []
_id2idx: dict[str, int] = {}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _ensure_index() -> None:
    """Nạp toàn bộ chunk từ store, dựng BM25 (chỉ lần đầu)."""
    global _bm25, _ids, _docs, _metas, _id2idx
    if _bm25 is not None:
        return
    _ids, _docs, _metas = store.corpus()
    _id2idx = {id_: i for i, id_ in enumerate(_ids)}
    _bm25 = BM25Okapi([_tokenize(d) for d in _docs])


def _vector_rank(query: str, n: int, where: dict | None) -> list[str]:
    return [c["id"] for c in store.search(query, k=n, where=where)]


def _bm25_rank(query: str, n: int, allowed: set[str] | None) -> list[str]:
    scores = _bm25.get_scores(_tokenize(query))
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    out = []
    for i in order:
        if allowed is not None and _ids[i] not in allowed:
            continue
        out.append(_ids[i])
        if len(out) >= n:
            break
    return out


def hybrid_search(query: str, k: int = settings.CANDIDATES_K,
                  where: dict | None = None) -> list[dict]:
    """Trả về tối đa k ứng viên đã gộp: [{'id','text','metadata','score'}].
    where: lọc theo metadata (vd {'category': 'web'})."""
    _ensure_index()
    allowed = store.matching_ids(where)
    vec_ids = _vector_rank(query, k, where)
    bm25_ids = _bm25_rank(query, k, allowed)

    fused: dict[str, float] = {}
    for ranking in (vec_ids, bm25_ids):
        for rank, id_ in enumerate(ranking):
            fused[id_] = fused.get(id_, 0.0) + 1.0 / (settings.RRF_K + rank + 1)

    ranked = sorted(fused, key=fused.get, reverse=True)[:k]
    out = []
    for id_ in ranked:
        i = _id2idx[id_]
        out.append({"id": id_, "text": _docs[i], "metadata": _metas[i], "score": fused[id_]})
    return out
