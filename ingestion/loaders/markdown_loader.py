"""Đọc tất cả file Markdown trong data/raw thành danh sách document.

Mỗi document = {text, metadata}. Nguồn khởi đầu (OWASP, HackTricks...) đều là
Markdown nên một loader chung là đủ. Sau này thêm loader riêng cho ATT&CK (JSON),
CVE (JSON feed)... trong cùng thư mục này.
"""
from pathlib import Path
import re
from config import settings


_MAX_CODE = 1500   # cắt block code cực dài để đỡ nhiễu, vẫn giữ phần đầu


def _keep_code(m: re.Match) -> str:
    """Giữ nội dung code/payload (quan trọng với corpus pentest), chỉ bỏ fence +
    nhãn ngôn ngữ. Trước đây thay bằng '[code block]' -> vứt mất payload/lệnh."""
    body = re.sub(r"^\w*\n", "", m.group(1), count=1)   # bỏ dòng nhãn ngôn ngữ/dòng trống đầu
    body = body.strip()
    if len(body) > _MAX_CODE:
        body = body[:_MAX_CODE]
    return "\n" + body + "\n"


def _clean(text: str) -> str:
    text = re.sub(r"```(.*?)```", _keep_code, text, flags=re.DOTALL)  # GIỮ code/payload
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)      # bỏ ảnh
    text = re.sub(r"\n{3,}", "\n\n", text)           # gộp dòng trống thừa
    return text.strip()


def load_markdown(raw_dir: Path = settings.DATA_RAW) -> list[dict]:
    """Trả về list[{'text', 'metadata'}] từ mọi .md/.mdx dưới raw_dir."""
    docs: list[dict] = []
    files = list(raw_dir.rglob("*.md")) + list(raw_dir.rglob("*.mdx"))
    for fp in files:
        try:
            text = _clean(fp.read_text(encoding="utf-8", errors="ignore"))
        except Exception as e:  # noqa: BLE001
            print(f"  [bỏ qua] {fp}: {e}")
            continue
        if len(text) < 50:      # bỏ file rỗng/quá ngắn
            continue
        rel = fp.relative_to(raw_dir)
        source = rel.parts[0] if len(rel.parts) > 1 else "misc"   # thư mục con = tên nguồn
        docs.append({
            "text": text,
            "metadata": {
                "source": source,             # vd: owasp / hacktricks
                "title": fp.stem,
                "path": str(rel).replace("\\", "/"),
            },
        })
    return docs
