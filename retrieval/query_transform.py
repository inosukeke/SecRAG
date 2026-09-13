"""Viết lại câu hỏi TRƯỚC khi truy xuất.

Corpus chủ yếu tiếng Anh, người dùng hay hỏi tiếng Việt -> dịch sang tiếng Anh và
mở rộng thuật ngữ giúp tăng recall (cả vector lẫn BM25 đều khớp tốt hơn).
Dùng chính Groq. Nếu lỗi/tắt -> trả về câu hỏi gốc (không chặn pipeline).
"""
from config import settings
from generation.llm import complete

_SYS = """You rewrite security questions into an English search query for a \
retrieval system over pentest/security docs (OWASP, HackTricks, MITRE ATT&CK).

Rules:
- Output ONLY the rewritten query, no explanation, no quotes.
- Translate to English if needed.
- Keep it concise; add 2-4 relevant technical synonyms/keywords \
(e.g. tool names, vuln class, CVE/technique ids) if helpful.
- Preserve any identifiers verbatim (CVE-xxxx-yyyy, T1059, function names)."""


def rewrite_query(question: str) -> str:
    if not settings.USE_QUERY_REWRITE:
        return question
    try:
        out = complete(_SYS, question, temperature=0.0)
        # Phòng model trả về nhiều dòng / rỗng
        out = out.splitlines()[0].strip() if out else ""
        return out or question
    except Exception as e:  # noqa: BLE001
        print(f"  [query-rewrite lỗi, dùng câu gốc] {e}")
        return question
