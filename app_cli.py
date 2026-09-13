"""SecRAG - hỏi đáp trên dòng lệnh (pipeline end-to-end).

Chạy:  python app_cli.py
Trước đó phải index dữ liệu:  python -m ingestion.indexer
"""
from retrieval.pipeline import retrieve
from generation.llm import answer

_FILTER_KEYS = {"category", "vuln_class", "source", "doc_type"}


def _parse_filters(question: str) -> tuple[dict, str]:
    """Tách các token đầu dạng key=value thành bộ lọc metadata.
    Ví dụ: 'category=web dạy tôi tìm xss' -> ({'category':'web'}, 'dạy tôi tìm xss')."""
    where, tokens = {}, question.split()
    while tokens and "=" in tokens[0]:
        k, v = tokens[0].split("=", 1)
        if k in _FILTER_KEYS:
            where[k] = v
            tokens = tokens[1:]
        else:
            break
    return where, " ".join(tokens)


def _score(c: dict) -> str:
    if "rerank_score" in c:
        return f"rerank={c['rerank_score']:.2f}"
    if "score" in c:
        return f"rrf={c['score']:.3f}"
    if "distance" in c:
        return f"dist={c['distance']:.3f}"
    return ""


def ask(question: str) -> None:
    where, question = _parse_filters(question)
    chunks, info = retrieve(question, where=where or None)
    if not chunks:
        msg = "Không có chunk nào khớp bộ lọc." if where else \
              "Chưa có dữ liệu trong index. Chạy: python -m ingestion.indexer"
        print(msg)
        return

    if where:
        print(f"\n⧩ Lọc: {where}")
    if info["rewritten"] != question:
        print(f"↻ Truy vấn đã dùng: {info['rewritten']}")

    print("\n🔎 Nguồn tham chiếu:")
    for i, c in enumerate(chunks, 1):
        m = c["metadata"]
        vc = ",".join(m.get("vuln_class", [])) or "-"
        print(f"   [{i}] {m.get('source')}/{m.get('title')}  "
              f"[{m.get('category')}|{vc}]  ({_score(c)})")

    print("\n🤖 Trả lời:\n")
    for piece in answer(question, chunks, stream=True):
        print(piece, end="", flush=True)
    print("\n")


def main() -> None:
    print("=" * 60)
    print(" SecRAG - trợ lý kiến thức pentest (gõ 'exit' để thoát)")
    print("=" * 60)
    while True:
        try:
            q = input("\n❓ Câu hỏi: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"exit", "quit", "q", ""}:
            break
        ask(q)
    print("Tạm biệt.")


if __name__ == "__main__":
    main()
