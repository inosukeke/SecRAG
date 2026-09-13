"""Eval RETRIEVAL — Phase 5. Đo Hit@k, MRR, thời gian cho từng cấu hình (preset).

Ý tưởng: chạy CÙNG bộ câu hỏi qua các cấu hình bật/tắt khác nhau (vector-only,
+hybrid, +rerank, +mmr) rồi so số liệu -> thấy mỗi bước đáng giá bao nhiêu, thay
vì đoán. Không gọi Groq (câu hỏi tiếng Anh, tắt query-rewrite) nên miễn phí & tất định.

Chỉ số:
- Hit@k : tỉ lệ câu có ÍT NHẤT một tài liệu đúng trong top-k (càng cao càng tốt).
- MRR   : trung bình 1/thứ_hạng của tài liệu đúng ĐẦU TIÊN (thưởng cho việc xếp đúng lên đầu).

Chạy: python -m eval.run_eval
"""
import json
import time

from config import settings

_TESTSET = settings.ROOT / "eval" / "testset.jsonl"

# Mỗi preset là tập override cờ trong settings. Query-rewrite luôn tắt để tất định.
PRESETS: dict[str, dict] = {
    "vector":        dict(USE_HYBRID=False, USE_RERANK=False, USE_MMR=False),
    "hybrid":        dict(USE_HYBRID=True,  USE_RERANK=False, USE_MMR=False),
    "hybrid+rerank": dict(USE_HYBRID=True,  USE_RERANK=True,  USE_MMR=False),
    "full (+mmr)":   dict(USE_HYBRID=True,  USE_RERANK=True,  USE_MMR=True),
}


def _load_testset() -> list[dict]:
    items = []
    for line in _TESTSET.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            items.append(json.loads(line))
    return items


def _is_relevant(chunk: dict, rels: list[str]) -> bool:
    title = chunk["metadata"].get("title", "").lower()
    return any(r.lower() in title for r in rels)


def _apply(preset: dict) -> None:
    settings.USE_QUERY_REWRITE = False          # tất định, không gọi Groq
    for k, v in preset.items():
        setattr(settings, k, v)


def _validate(items: list[dict]) -> None:
    """Cảnh báo nếu 'relevant' của câu nào không khớp title nào trong store
    (test item hỏng sẽ luôn bị tính là trượt -> sai lệch số liệu)."""
    from retrieval import store
    titles = [m.get("title", "").lower() for m in store.corpus()[2]]
    for it in items:
        if not any(any(r.lower() in t for t in titles) for r in it["relevant"]):
            print(f"  ⚠ Không title nào khớp {it['relevant']} — câu: {it['q']!r}")


def _eval_preset(items: list[dict]) -> tuple[float, float, float]:
    from retrieval.pipeline import retrieve
    hits, rr, t0 = 0, 0.0, time.time()
    for it in items:
        chunks, _ = retrieve(it["q"])
        ranks = [i for i, c in enumerate(chunks, 1) if _is_relevant(c, it["relevant"])]
        if ranks:
            hits += 1
            rr += 1.0 / ranks[0]
    n = len(items)
    return hits / n, rr / n, (time.time() - t0) / n


def main() -> None:
    items = _load_testset()
    print(f"Testset: {len(items)} câu | TOP_K={settings.TOP_K}")
    print("Kiểm tra tính hợp lệ của test set ...")
    _validate(items)

    # Warm-up: nạp sẵn model (embedding + rerank) để không tính vào thời gian preset
    _apply(PRESETS["full (+mmr)"])
    from retrieval.pipeline import retrieve
    retrieve("warm up the models")

    print(f"\n{'preset':16}{'Hit@'+str(settings.TOP_K):>8}{'MRR':>7}{'s/câu':>8}")
    print("-" * 39)
    for name, preset in PRESETS.items():
        _apply(preset)
        hit, mrr, spq = _eval_preset(items)
        print(f"{name:16}{hit:8.2f}{mrr:7.2f}{spq:8.2f}")
    print("\nHit@k, MRR: càng cao càng tốt. So dòng để thấy mỗi bước thêm bao nhiêu.")


if __name__ == "__main__":
    main()
