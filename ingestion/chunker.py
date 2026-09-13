"""Cắt document thành chunk. Ưu tiên cắt theo heading Markdown (giữ ngữ cảnh
theo mục), sau đó cắt tiếp theo số từ nếu một mục quá dài, có overlap.

Chunking quyết định phần lớn chất lượng RAG -> đây là file đáng để tinh chỉnh.
"""
import re
from config import settings

_HEADING = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)


def _split_by_words(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if len(words) <= size:
        return [text]
    out, start = [], 0
    while start < len(words):
        out.append(" ".join(words[start:start + size]))
        start += size - overlap
    return out


def chunk_documents(docs: list[dict]) -> list[dict]:
    """Nhận list document -> trả list chunk {'text', 'metadata'} kèm chunk_id."""
    chunks: list[dict] = []
    for doc in docs:
        text = doc["text"]
        # Tách theo heading: giữ heading đứng đầu mỗi khối
        positions = [m.start() for m in _HEADING.finditer(text)]
        sections = []
        if positions:
            positions = [0] + positions if positions[0] != 0 else positions
            for i, p in enumerate(positions):
                end = positions[i + 1] if i + 1 < len(positions) else len(text)
                sec = text[p:end].strip()
                if sec:
                    sections.append(sec)
        else:
            sections = [text]

        for sec in sections:
            for piece in _split_by_words(sec, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP):
                if len(piece.split()) < 10:      # bỏ mẩu quá ngắn
                    continue
                idx = len(chunks)
                chunks.append({
                    "text": piece,
                    "metadata": {**doc["metadata"], "chunk_id": idx},
                })
    return chunks
