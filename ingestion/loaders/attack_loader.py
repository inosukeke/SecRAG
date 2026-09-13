"""Loader MITRE ATT&CK (STIX 2.1 JSON) -> danh sách document.

Khác Markdown: dữ liệu là JSON lồng nhau. Việc của loader là LÀM PHẲNG mỗi
'attack-pattern' (kỹ thuật tấn công) thành một đoạn text mạch lạc + metadata giàu
(technique_id, tactics, platforms) để lọc/trích dẫn.

Chỉ lấy attack-pattern (technique) — phần giá trị nhất cho pentest. Bỏ object đã
revoked/deprecated. Có thể mở rộng sang course-of-action (mitigation), tool, group.
"""
import json
from pathlib import Path

from config import settings

_ATTACK_JSON = settings.DATA_RAW / "attack" / "enterprise-attack.json"


def _external_id(obj: dict) -> str:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack" and ref.get("external_id"):
            return ref["external_id"]                  # vd "T1059.001"
    return ""


def _tactics(obj: dict) -> list[str]:
    return [p["phase_name"] for p in obj.get("kill_chain_phases", [])
            if p.get("kill_chain_name") == "mitre-attack"]


def load_attack(path: Path = _ATTACK_JSON) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    docs: list[dict] = []
    for obj in data.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue

        tid = _external_id(obj)
        name = obj.get("name", "")
        tactics = _tactics(obj)
        platforms = obj.get("x_mitre_platforms", [])
        desc = obj.get("description", "").strip()
        detection = obj.get("x_mitre_detection", "").strip()

        # Làm phẳng thành text đọc được cho LLM
        parts = [f"{tid} {name}".strip()]
        if tactics:
            parts.append("Tactics: " + ", ".join(tactics))
        if platforms:
            parts.append("Platforms: " + ", ".join(platforms))
        if desc:
            parts.append("\n" + desc)
        if detection:
            parts.append("\nDetection:\n" + detection)
        text = "\n".join(parts)

        docs.append({
            "text": text,
            "metadata": {
                "source": "attack",
                "title": f"{tid} {name}".strip(),
                "path": f"attack/{tid}",
                "technique_id": tid,
                "tactics": tactics,
                "platforms": platforms,
                "category": "attack",       # để enrich không ghi đè
                "doc_type": "technique",
            },
        })
    return docs
