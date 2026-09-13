"""Truy vấn ngữ nghĩa. Mỏng — chỉ ủy quyền cho vector store NumPy (retrieval.store)."""
from config import settings
from retrieval import store


def search(query: str, top_k: int = settings.TOP_K,
           where: dict | None = None) -> list[dict]:
    """Trả về top_k chunk liên quan: [{'id','text','metadata','distance'}]."""
    return store.search(query, k=top_k, where=where)
