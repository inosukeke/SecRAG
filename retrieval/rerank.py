"""Rerank ứng viên bằng cross-encoder (local).

Bi-encoder (embedding) nhanh nhưng thô; cross-encoder đọc CẶP (câu hỏi, đoạn) cùng
lúc nên chấm độ liên quan chính xác hơn nhiều. Chỉ chạy trên ~30 ứng viên nên đủ nhanh.
"""
from config import settings

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder  # import trễ để khởi động nhanh
        _model = CrossEncoder(settings.RERANK_MODEL)
    return _model


def rerank(query: str, candidates: list[dict], top_k: int | None = None) -> list[dict]:
    """Chấm lại toàn bộ ứng viên, trả về đã sắp giảm dần theo rerank_score.
    top_k=None: trả hết (để bước MMR chọn tiếp); đặt số để cắt luôn."""
    if not candidates:
        return []
    scores = _get_model().predict([(query, c["text"]) for c in candidates])
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)
    ranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
    return ranked[:top_k] if top_k else ranked
