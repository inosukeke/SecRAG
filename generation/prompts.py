"""Prompt template. Rule quan trọng nhất: BÁM ngữ cảnh, có TRÍCH NGUỒN,
không biết thì nói không biết -> chống bịa (hallucination)."""

SYSTEM = """Bạn là trợ lý kiến thức an ninh mạng (SecRAG) phục vụ HỌC TẬP và \
pentest có phép. Trả lời dựa TRÊN NGỮ CẢNH được cung cấp.

Quy tắc:
- Chỉ dùng thông tin trong NGỮ CẢNH. Nếu ngữ cảnh không đủ, nói rõ \
"Tôi không tìm thấy thông tin này trong tài liệu" thay vì bịa.
- Luôn trích nguồn dạng [nguồn: <source>/<title>] cho các ý chính.
- Giải thích ở mức hiểu bản chất & phương pháp; định hướng học tập và \
kiểm thử có phép, không hướng dẫn tấn công hệ thống thật của người khác.
- Trả lời bằng ngôn ngữ của câu hỏi (Việt hỏi -> Việt trả lời)."""


def build_user_prompt(question: str, chunks: list[dict]) -> str:
    ctx_parts = []
    for i, c in enumerate(chunks, 1):
        m = c["metadata"]
        tag = f"{m.get('source', '?')}/{m.get('title', '?')}"
        ctx_parts.append(f"[{i}] (nguồn: {tag})\n{c['text']}")
    context = "\n\n---\n\n".join(ctx_parts)
    return f"""NGỮ CẢNH:
{context}

CÂU HỎI: {question}

Trả lời dựa trên ngữ cảnh trên, kèm trích nguồn."""
