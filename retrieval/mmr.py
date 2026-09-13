"""Maximal Marginal Relevance (MMR): chọn top-k vừa LIÊN QUAN vừa ĐA DẠNG.

Vấn đề: rerank chỉ theo độ liên quan -> dễ trả nhiều chunk gần trùng nhau (ví dụ
3 đoạn cùng một cheat sheet). MMR cân bằng:
    score(d) = λ·relevance(d) − (1−λ)·max(similarity(d, đã_chọn))
mỗi vòng chọn chunk điểm cao nhất, trừ hao phần trùng lặp với những chunk đã chọn.

relevance lấy từ rerank_score (nếu có), không thì điểm RRF của hybrid.
Độ trùng lặp = cosine giữa embedding các chunk (lấy từ store).
"""
import numpy as np

from config import settings
from retrieval import store


def _relevance(c: dict) -> float:
    if "rerank_score" in c:
        return c["rerank_score"]
    if "score" in c:
        return c["score"]
    return -c.get("distance", 0.0)


def mmr_select(candidates: list[dict], k: int,
               lambda_: float = settings.MMR_LAMBDA) -> list[dict]:
    if len(candidates) <= k:
        return candidates

    emb = store.embeddings_for([c["id"] for c in candidates])  # (M, d) chuẩn hoá
    sim = emb @ emb.T                                          # (M, M) cosine

    rel = np.array([_relevance(c) for c in candidates], dtype="float32")
    if rel.max() > rel.min():                                 # min-max về [0,1]
        rel = (rel - rel.min()) / (rel.max() - rel.min())

    selected: list[int] = []
    remaining = set(range(len(candidates)))
    while remaining and len(selected) < k:
        best_i, best_score = None, -1e9
        for i in remaining:
            diversity = max((sim[i][j] for j in selected), default=0.0)
            score = lambda_ * rel[i] - (1 - lambda_) * diversity
            if score > best_score:
                best_score, best_i = score, i
        selected.append(best_i)
        remaining.remove(best_i)
    return [candidates[i] for i in selected]
