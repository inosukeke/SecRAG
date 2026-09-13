"""Đọc Markdown -> chunk -> embed (local) -> ghi vector store NumPy.
Chạy: python -m ingestion.indexer"""
from config import settings
from ingestion.loaders.markdown_loader import load_markdown
from ingestion.loaders.attack_loader import load_attack
from ingestion.chunker import chunk_documents
from ingestion.enrich import enrich_chunk
from retrieval import store


def build_index() -> None:
    print(f"[1/4] Đọc nguồn từ {settings.DATA_RAW} ...")
    md = load_markdown()
    attack = load_attack()
    docs = md + attack
    if not docs:
        print("  Không thấy nguồn nào. Xem README mục 'Chuẩn bị dữ liệu'.")
        return
    print(f"      -> {len(docs)} tài liệu (markdown {len(md)}, attack {len(attack)})")

    print("[2/4] Cắt chunk ...")
    chunks = chunk_documents(docs)
    print(f"      -> {len(chunks)} chunk")

    print("[3/4] Gắn nhãn metadata (category / vuln_class / doc_type) ...")
    for c in chunks:
        enrich_chunk(c)

    print(f"[4/4] Embed + ghi store (model: {settings.EMBED_MODEL}) ...")
    ids = [f"c{c['metadata']['chunk_id']}" for c in chunks]
    texts = [c["text"] for c in chunks]
    metas = [c["metadata"] for c in chunks]
    n = store.save(ids, texts, metas)
    print(f"Xong. Tổng vector trong store: {n}  ->  {settings.STORE_PATH}")


if __name__ == "__main__":
    build_index()
