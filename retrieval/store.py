"""Vector store tối giản bằng NumPy — thay cho Chroma.

Vì sao tự viết: bản Chroma có wheel sẵn (1.x) lỗi đọc lại index trên Windows,
còn bản ổn định (0.5.x) đòi trình biên dịch C++. Với quy mô vài nghìn–vài trăm
nghìn chunk, cosine brute-force chạy mili-giây nên NumPy là đủ, lại minh bạch.

Lưu trữ: một file pickle {ids, docs, metas, emb(float32, đã chuẩn hoá)}.
Vì embedding đã chuẩn hoá L2 nên tích vô hướng = cosine similarity.

Hỗ trợ LỌC theo metadata (where) và lấy embedding theo id (cho MMR).
"""
import pickle
import numpy as np

from config import settings

_model = None
_cache: dict | None = None
_id2idx: dict[str, int] = {}


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # import trễ
        _model = SentenceTransformer(settings.EMBED_MODEL)
    return _model


def embed(texts: list[str], show_progress: bool = False) -> np.ndarray:
    """Nhúng + chuẩn hoá L2. Trả về ndarray float32 (N, d)."""
    vecs = _get_model().encode(
        texts, normalize_embeddings=True, show_progress_bar=show_progress
    )
    return np.asarray(vecs, dtype="float32")


def save(ids: list[str], docs: list[str], metas: list[dict]) -> int:
    """Nhúng toàn bộ docs rồi ghi store ra đĩa. Trả về số vector."""
    emb = embed(docs, show_progress=True)
    settings.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.STORE_PATH, "wb") as f:
        pickle.dump({"ids": ids, "docs": docs, "metas": metas, "emb": emb}, f)
    return len(ids)


def _load() -> dict:
    global _cache, _id2idx
    if _cache is None:
        if not settings.STORE_PATH.exists():
            raise FileNotFoundError("Chưa có store. Chạy: python -m ingestion.indexer")
        with open(settings.STORE_PATH, "rb") as f:
            _cache = pickle.load(f)
        _id2idx = {id_: i for i, id_ in enumerate(_cache["ids"])}
    return _cache


def count() -> int:
    return len(_load()["ids"])


# --- Lọc metadata ---------------------------------------------------------

def _match(meta_val, allowed) -> bool:
    """meta_val có thể là scalar hoặc list; allowed là scalar hoặc list.
    Khớp nếu có phần giao (list) hoặc bằng nhau (scalar)."""
    allowed_set = set(allowed) if isinstance(allowed, (list, tuple, set)) else {allowed}
    if isinstance(meta_val, (list, tuple, set)):
        return bool(set(meta_val) & allowed_set)
    return meta_val in allowed_set


def _matching_index_mask(where: dict | None) -> np.ndarray | None:
    """Trả về mask boolean (N,) các chunk thoả where; None nếu không lọc."""
    if not where:
        return None
    metas = _load()["metas"]
    mask = np.array(
        [all(_match(m.get(k), v) for k, v in where.items()) for m in metas],
        dtype=bool,
    )
    return mask


def matching_ids(where: dict | None) -> set[str] | None:
    """Tập id thoả where (cho BM25 lọc); None nếu không lọc."""
    mask = _matching_index_mask(where)
    if mask is None:
        return None
    ids = _load()["ids"]
    return {ids[i] for i in np.nonzero(mask)[0]}


# --- Truy vấn -------------------------------------------------------------

def search(query: str, k: int, where: dict | None = None) -> list[dict]:
    """Top-k theo cosine, có thể lọc theo metadata (where)."""
    d = _load()
    q = embed([query])[0]                 # (d,), đã chuẩn hoá
    sims = d["emb"] @ q                    # (N,) cosine
    mask = _matching_index_mask(where)
    if mask is not None:
        sims = np.where(mask, sims, -np.inf)   # loại chunk không thoả điều kiện
    top = np.argsort(-sims)[:k]
    out = []
    for i in top:
        if sims[i] == -np.inf:
            break
        out.append({
            "id": d["ids"][i],
            "text": d["docs"][i],
            "metadata": d["metas"][i],
            "distance": float(1.0 - d["emb"][i] @ q),
        })
    return out


def corpus() -> tuple[list[str], list[str], list[dict]]:
    """(ids, docs, metas) cho BM25 dùng lại — không phải nhúng gì thêm."""
    d = _load()
    return d["ids"], d["docs"], d["metas"]


def embeddings_for(ids: list[str]) -> np.ndarray:
    """Lấy ma trận embedding (đã chuẩn hoá) theo danh sách id — dùng cho MMR."""
    d = _load()
    return np.stack([d["emb"][_id2idx[i]] for i in ids])
