"""Gắn nhãn metadata cho chunk bằng LUẬT TỪ KHÓA (không dùng LLM).

Vì sao dùng luật, không dùng LLM: gắn nhãn 3367 chunk qua Groq sẽ tốn quá nhiều
lời gọi + dính rate limit; luật thì miễn phí, tức thì, minh bạch và đủ tốt để bật
tính năng LỌC theo metadata (mục tiêu chính). Sau này có thể thay bằng LLM nếu cần.

Thêm 3 trường vào metadata:
- category: nhóm chủ đề (web/auth/crypto/mobile/api/infra/framework/general)
- vuln_class: danh sách lớp lỗ hổng phát hiện trong chunk (sqli, xss, ...)
- doc_type: loại tài liệu, suy từ 'source' (owasp -> cheatsheet)
"""
import re

# Ưu tiên theo thứ tự: khớp đầu tiên trong title thắng.
_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("mobile",    ("mobile", "android", "ios")),
    ("crypto",    ("cryptographic", "cryptography", "key_management", "secrets",
                   "transport_layer", "tls", "certificate", "pinning")),
    ("auth",      ("authentication", "authorization", "session", "password",
                   "jwt", "json_web_token", "saml", "oauth", "access_control",
                   "forgot", "credential", "multifactor", "multi_factor")),
    ("api",       ("rest", "graphql", "grpc", "web_service", "microservices", "api")),
    ("infra",     ("docker", "kubernetes", "network", "ci_cd", "infrastructure",
                   "hardening", "virtual_patching", "attack_surface")),
    ("framework", ("laravel", "symfony", "django", "ruby_on_rails", "rails",
                   "nodejs", "dotnet", "java", "php", "spring", "vue", "react",
                   "angular")),
    ("web",       ("xss", "cross_site", "sql", "injection", "csrf", "ssrf",
                   "clickjack", "cookie", "cors", "content_security", "http",
                   "dom", "request_forgery", "file_upload", "web")),
]

# vuln_class: (nhãn, các cụm từ nhận biết trong nội dung, đã lowercase)
_VULN_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("sqli",            ("sql injection", "sqli")),
    ("xss",             ("cross-site scripting", "cross site scripting", "xss")),
    ("csrf",            ("cross-site request forgery", "csrf")),
    ("ssrf",            ("server-side request forgery", "ssrf")),
    ("xxe",             ("xml external entity", "xxe")),
    ("idor",            ("insecure direct object", "idor")),
    ("rce",             ("remote code execution", "command injection", "rce")),
    ("deserialization", ("deserialization", "deserialisation")),
    ("path_traversal",  ("path traversal", "directory traversal")),
    ("open_redirect",   ("open redirect",)),
    ("clickjacking",    ("clickjacking",)),
    ("injection",       ("injection",)),   # tổng quát, xếp cuối
]

_DOC_TYPE = {"owasp": "cheatsheet"}


def _category(title: str, text: str) -> str:
    # Xét theo TITLE (category là thuộc tính của tài liệu, ổn định hơn nội dung
    # từng chunk — tránh gán nhầm khi một chunk lỡ nhắc 'mobile'/'ios'...).
    hay = title.lower()
    for cat, kws in _CATEGORY_RULES:
        if any(kw in hay for kw in kws):
            return cat
    return "general"


def _has_word(low: str, phrase: str) -> bool:
    # Khớp theo ranh giới từ -> tránh 'rce' dính trong 'resource', 'source', 'force'
    return re.search(r"\b" + re.escape(phrase) + r"\b", low) is not None


def _vuln_classes(text: str) -> list[str]:
    low = text.lower()
    found = [name for name, kws in _VULN_RULES if any(_has_word(low, k) for k in kws)]
    # Nếu đã có lớp cụ thể thì bỏ nhãn 'injection' tổng quát cho gọn
    if len(found) > 1 and "injection" in found:
        found.remove("injection")
    return found


def enrich_chunk(chunk: dict) -> dict:
    """Bổ sung metadata tại chỗ và trả về chunk.
    Tôn trọng nhãn loader đã đặt sẵn (vd ATT&CK tự set category='attack')."""
    m = chunk["metadata"]
    m.setdefault("category", _category(m.get("title", ""), chunk["text"]))
    m.setdefault("doc_type", _DOC_TYPE.get(m.get("source", ""), "reference"))
    m["vuln_class"] = _vuln_classes(chunk["text"])   # luôn tính theo nội dung
    return chunk
