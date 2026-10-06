# SecRAG — Kế hoạch triển khai

> Tài liệu tham chiếu cho dự án. Đọc file này để nắm bối cảnh trước khi làm.
> Cập nhật gần nhất: 2026-10-06. Trạng thái: **P0–P5 xong**. Pipeline đầy đủ
> (query-rewrite + hybrid + rerank + metadata filter + MMR + loader ATT&CK), web UI Streamlit,
> eval retrieval — tất cả chạy thật trên GPU. **Nâng cấp embedding → `BAAI/bge-m3`** + chunker
> giữ code/payload → re-index: Corpus OWASP + MITRE ATT&CK = **4203 chunk**. Eval xác nhận cải
> thiện (xem Phase 5). Còn lại (tùy chọn): loader CVE/KEV, eval chất lượng câu trả lời, FastAPI SSE.

## 1. Phạm vi & nguyên tắc

**Mục tiêu**: học cách ứng dụng RAG vào sản phẩm thực tế, qua một trợ lý hỏi đáp
kiến thức an ninh mạng.

**Định hướng nội dung**: Offensive / Pentest — index tài liệu bảo mật công khai
để **hiểu bản chất & tra cứu** phục vụ học tập và kiểm thử **có phép**.

**Nguyên tắc**:
- Chạy **local/free**: không phụ thuộc dịch vụ trả phí bắt buộc.
  - LLM sinh câu trả lời → **Groq API** (cloud, free tier, không tốn RAM/CPU máy).
  - Embedding + vector DB → chạy **local nhẹ** (sentence-transformers + Chroma).
- **Chống bịa (hallucination)**: LLM chỉ trả lời dựa trên ngữ cảnh truy xuất được;
  không đủ dữ liệu thì nói "không tìm thấy trong tài liệu".
- **Luôn trích nguồn** để kiểm chứng và học đúng.
- Nội dung ở mức giáo dục/phòng thủ; không hướng dẫn tấn công hệ thống người khác.
- **Đo lường sớm**: đánh giá chất lượng bằng số liệu (Phase 5), không cảm tính.

## 2. Nguồn dữ liệu (công khai, miễn phí)

Bỏ tài liệu vào `data/raw/<tên-nguồn>/`. Tên thư mục con = nhãn "nguồn" khi trích dẫn.
Chia theo độ khó tích hợp để nạp dần.

### Nhóm 1 — Markdown, dễ, chất lượng cao (nạp trước)
Xương sống. `markdown_loader.py` hiện tại nạp được ngay, chỉ cần clone vào `data/raw/`.

| Nguồn | Nội dung | Giấy phép |
|-------|----------|-----------|
| OWASP Cheat Sheet Series | Phòng chống theo chủ đề | CC BY-SA |
| OWASP WSTG | Phương pháp test web (chuẩn) | CC BY-SA |
| OWASP MASTG | Phương pháp test mobile | CC BY-SA |
| PayloadsAllTheThings | Payload + methodology theo lớp lỗ hổng | MIT |
| HackTricks | Wiki offensive lớn (web/AD/linux/win) | CC BY-NC |
| GTFOBins | Lạm dụng binary Unix (privesc) — YAML+MD | MIT/GPL |
| LOLBAS | Living-off-the-land binaries Windows — YAML | MIT |

### Nhóm 2 — Có cấu trúc (JSON/CSV/YAML), cần loader riêng
Dữ liệu chuẩn hoá, giá trị cao; viết loader chuyển sang text + metadata (bài học Phase 3).

| Nguồn | Định dạng | Giá trị |
|-------|-----------|---------|
| MITRE ATT&CK | STIX JSON | Kỹ thuật/tactic/mitigation, khung tham chiếu chung |
| MITRE CAPEC | XML/JSON | Mẫu tấn công |
| CWE | XML/CSV | Phân loại điểm yếu phần mềm |
| NVD / CVE | JSON feed | Lỗ hổng + điểm CVSS |
| CISA KEV | JSON/CSV | Lỗ hổng đang bị khai thác thực tế (ưu tiên cao) |
| ExploitDB | CSV + file | Index exploit công khai (tra cứu, không chạy) |
| Nuclei templates | YAML | Mẫu phát hiện lỗ hổng (ProjectDiscovery) |

### Nhóm 3 — Docs công cụ & chuẩn ngành (sau)

| Nguồn | Nội dung |
|-------|----------|
| Docs công cụ: nmap NSE, sqlmap, ffuf, Hydra, Impacket, Metasploit | Cách dùng công cụ |
| NIST SP 800-115 | Chuẩn kiểm thử bảo mật (public domain) |
| PTES / OSSTMM | Quy trình pentest chuẩn |

### Lộ trình nạp
- **Bây giờ (Nhóm 1)**: clone toàn bộ, loader hiện tại chạy luôn.
- **Phase 3 (Nhóm 2)**: MITRE ATT&CK + CVE/KEV → học viết loader dữ liệu có cấu trúc.
- **Sau**: Nhóm 3.

```bash
git clone --depth 1 https://github.com/OWASP/CheatSheetSeries        data/raw/owasp
git clone --depth 1 https://github.com/OWASP/wstg                    data/raw/wstg
git clone --depth 1 https://github.com/swisskyrepo/PayloadsAllTheThings data/raw/payloads
git clone --depth 1 https://github.com/GTFOBins/GTFOBins.github.io   data/raw/gtfobins
git clone --depth 1 https://github.com/LOLBAS-Project/LOLBAS         data/raw/lolbas
git clone --depth 1 https://github.com/HackTricks-wiki/hacktricks    data/raw/hacktricks   # lớn, tuỳ chọn
```

### Giấy phép
Đa số MIT/CC. **HackTricks là CC BY-NC** (phi thương mại) — học tập thì ổn, thương
mại hoá cần cân nhắc. Tránh scrape trang có ToS cấm (PortSwigger Academy, blog);
ưu tiên repo/feed công khai chính chủ.

## 3. Tech stack (local/free)

| Lớp | Lựa chọn | Ghi chú |
|-----|----------|---------|
| Ngôn ngữ | Python 3.11+ | Hệ sinh thái RAG mạnh nhất |
| LLM | **Groq API** — `llama-3.3-70b-versatile` | Cloud, free; nhẹ hơn: `llama-3.1-8b-instant` |
| Embedding | **`BAAI/bge-m3`** (local, GPU) | 1024-dim, 2024; nhẹ cho CPU: `paraphrase-multilingual-MiniLM-L12-v2` |
| Vector store | **NumPy tự viết** (`retrieval/store.py`) | Cosine brute-force; thay Chroma (xem ghi chú dưới) |
| Keyword search | `rank-bm25` | Cho hybrid (Phase 3) |
| Reranker | `BAAI/bge-reranker-base` (cross-encoder, local) | Chạy GPU ~1.6s/câu; CPU dùng `ms-marco-MiniLM-L-6-v2` |
| Tăng tốc | **torch CUDA (cu124)** trên RTX 3060 | Bản CPU chậm; xem README |

> **Vì sao không dùng Chroma**: bản có wheel sẵn (1.x, rust) lỗi đọc lại index trên
> Windows; bản 0.5.x cần trình biên dịch C++ (không có sẵn). Vector store NumPy đủ
> nhanh cho quy mô này (vài nghìn–vài trăm nghìn chunk), minh bạch và không phụ thuộc nền tảng.
| Backend | FastAPI | Streaming SSE (Phase 4) |
| UI | Streamlit | Chat UI nhanh (Phase 4) |
| Eval | RAGAS + testset tự soạn | Phase 5 |

**Tài nguyên máy**: chỉ embedding + Chroma chạy local (nhẹ). Phần "nặng" (LLM)
để Groq lo trên cloud → máy cá nhân không bị ngốn RAM/CPU.

## 4. Cấu trúc thư mục

```
RAG/
├── config/
│   └── settings.py          # cấu hình tập trung: model, chunk size, top_k
├── ingestion/
│   ├── loaders/
│   │   ├── markdown_loader.py   # đọc .md/.mdx trong data/raw
│   │   └── attack_loader.py     # MITRE ATT&CK STIX JSON → technique docs
│   ├── chunker.py           # cắt theo heading + overlap (nơi ăn tiền nhất)
│   ├── enrich.py            # gắn nhãn metadata: category / vuln_class / doc_type
│   └── indexer.py           # chunk → enrich → embed (local) → ghi store
├── retrieval/
│   ├── store.py             # vector store NumPy (embed + cosine + corpus cho BM25)
│   ├── vector.py            # tìm kiếm ngữ nghĩa (ủy quyền cho store)
│   ├── query_transform.py   # viết lại/dịch câu hỏi (VN→EN) trước khi search
│   ├── hybrid.py            # gộp vector + BM25 (RRF), hỗ trợ lọc where
│   ├── rerank.py            # cross-encoder chấm lại ứng viên
│   ├── mmr.py               # đa dạng hoá kết quả cuối (khử gần trùng)
│   └── pipeline.py          # gộp: rewrite → hybrid(+lọc) → rerank → MMR → top_k
├── generation/
│   ├── prompts.py           # template + rule chống bịa + citation
│   └── llm.py               # client Groq (có streaming)
├── api/
│   └── main.py              # [P4] FastAPI: /ingest, /chat
├── ui/
│   └── app.py               # Streamlit chat + lọc + bật/tắt cấu hình + hiện nguồn
├── eval/
│   ├── testset.jsonl        # [P5] câu hỏi + đáp án tham chiếu
│   └── run_eval.py          # [P5] RAGAS metrics
├── data/
│   ├── raw/                 # tài liệu nguồn (.md) — không commit
│   └── store.pkl            # vector store NumPy — không commit
├── app_cli.py               # pipeline hỏi đáp end-to-end trên CLI
├── requirements.txt
├── .env                     # GROQ_API_KEY (không commit)
└── README.md
```

## 5. Roadmap

Ký hiệu: `[x]` xong · `[ ]` chưa · "Xong khi" = tiêu chí nghiệm thu.

### [x] Phase 0 — Setup (0.5 ngày)
venv, requirements, cấu trúc thư mục, `settings.py`, `.env` với Groq key.
**Xong khi**: import được thư viện, gọi Groq trả lời 1 prompt.

### [x] Phase 1 — Ingestion tối thiểu (1–2 ngày)
Loader Markdown → chunker (cắt theo heading, ~500 từ, overlap ~15%, giữ metadata
`{source, title, path, chunk_id}`) → indexer embed + ghi Chroma.
**Xong khi**: index OWASP xong, `collection.count()` hợp lý, query vector ra đúng chủ đề.

### [x] Phase 2 — Retrieve + Generate cơ bản (2 ngày)
Vector search top-k → build prompt (bám ngữ cảnh + citation) → Groq sinh câu trả lời.
CLI hỏi đáp (`app_cli.py`).
**Xong khi**: hỏi "OWASP Top 10 gồm gì?" ra câu trả lời đúng + trích nguồn.

### [~] Phase 3 — Nâng chất lượng retrieval + làm giàu dữ liệu (2–3 ngày) ⬅ **đang làm**
- [x] `retrieval/query_transform.py`: viết lại/dịch câu hỏi (VN→EN) trước khi search.
- [x] `retrieval/hybrid.py`: BM25 + vector, gộp điểm bằng RRF.
- [x] `retrieval/rerank.py`: cross-encoder chấm lại ứng viên → giữ top-K.
- [x] `retrieval/pipeline.py`: gộp các bước, bật/tắt qua config; nối vào `app_cli.py`.
- [x] **Làm giàu metadata** (`ingestion/enrich.py`, gắn nhãn theo luật):
  - `category` (web/auth/crypto/mobile/api/infra/framework/general) theo title.
  - `vuln_class` (sqli/xss/csrf/ssrf/xxe/idor/rce...) theo nội dung, khớp ranh giới từ.
  - `doc_type` (owasp→cheatsheet).
- [x] **Lọc khi truy xuất** theo metadata, xuyên suốt hybrid (`store.matching_ids` +
  `where` trong search/hybrid/pipeline). CLI: `category=web <câu hỏi>`.
- [x] **MMR** (`retrieval/mmr.py`) đa dạng hoá kết quả cuối, khử chunk gần trùng.
- [x] Loader dữ liệu có cấu trúc: **MITRE ATT&CK** (`attack_loader.py`, STIX JSON →
  697 kỹ thuật, metadata `technique_id`/`tactics`/`platforms`). Lọc `source=attack`.
- [ ] Loader CVE/KEV (JSON feed) — bước mở rộng tiếp theo. ⬅ **tiếp theo**
- [ ] Cross-link mã chuẩn: CVE ↔ CWE ↔ CAPEC ↔ ATT&CK (cần CVE/CWE trước).
- [ ] Giữ nguyên bảng payload & lệnh mẫu khi chunk (khi thêm PayloadsAllTheThings).
**Xong khi**: lọc `category`/`source` hoạt động ✅; MMR bật/tắt ✅; ATT&CK trả lời có
trích dẫn technique_id ✅.

### [x] Phase 4 — Giao diện web (Streamlit)
`ui/app.py` + `.streamlit/config.toml` (theme sáng, accent teal). Chat streaming, hiện
nguồn kèm nhãn category/vuln_class, sidebar **lọc** (category/source) và **bật/tắt**
hybrid/rerank/MMR + slider TOP_K ngay trên web. Chạy: `streamlit run ui/app.py`.
Đã test end-to-end trên trình duyệt (câu trả lời có trích dẫn + expander nguồn).
**Xong khi**: chat qua trình duyệt, stream + list nguồn ✅. (FastAPI SSE để sau nếu cần.)

### [x] Phase 5 — Đánh giá retrieval ⭐ học được nhiều nhất
`eval/testset.jsonl` (20 câu EN, kèm mảnh title đúng) + `eval/run_eval.py` đo
**Hit@k** và **MRR** cho từng preset (vector / +hybrid / +rerank / +mmr). Không gọi
Groq → tất định, miễn phí. Chạy: `python -m eval.run_eval`.

Kết quả trước/sau nâng cấp embedding (TOP_K=5, corpus OWASP+ATT&CK):

| preset | MiniLM (cũ) | bge-m3 + giữ code (mới) |
|--------|:----:|:----:|
| vector | 0.80 / 0.58 | **0.90 / 0.78** |
| +hybrid | 0.85 / 0.65 | **1.00 / 0.75** |
| +rerank | 0.95 / 0.76 | 0.95 / 0.74 |
| +mmr | 0.90 / 0.74 | 0.95 / 0.73 |

*(Hit@5 / MRR; MMR mặc định đã tắt)*

**Kết luận (đo bằng eval):**
- Đổi embedding sang **bge-m3** cải thiện truy xuất nền rõ rệt (vector 0.80→0.90, hybrid→1.00).
- Với bge-m3, **rerank hết tác dụng** (hybrid 1.00 > +rerank 0.95) → có thể tắt để nhanh ~7.5×.
  Lưu ý testset nhỏ (20 câu), chênh 0.05 ~ nhiễu; cần testset lớn hơn để chốt.
- MMR vẫn làm giảm nhẹ cho tra cứu factual → giữ tắt.
- (Chưa làm: eval chất lượng câu trả lời kiểu RAGAS — cần nhiều lời gọi LLM.)

### [ ] Phase 6 — Hoàn thiện (tùy chọn)
Query rewriting, lọc theo metadata (vd chỉ CVE năm X), cache, xử lý "không biết",
viết README + tổng kết bài học.

**Ước lượng tổng**: ~10–14 ngày bán thời gian cho bản đủ pipeline + eval.

## 6. Bản đồ học (kỹ thuật RAG theo từng phase)

| Phase | Nắm được |
|-------|----------|
| 1 | Chunking chiến lược, thiết kế metadata |
| 2 | Prompt grounding, chống hallucination, citation |
| 3 | Hybrid search + reranking (2 kỹ thuật cải thiện mạnh nhất) |
| 5 | Đo lường RAG khách quan (điểm mù của người mới) |

## 7. Rủi ro & lưu ý

- **Groq free tier có rate limit** (requests/phút, tokens/ngày) → đủ để học, nhưng
  tránh vòng lặp gọi dày; bắt lỗi 429 và chờ.
- **Model embedding nhỏ** có thể yếu với thuật ngữ chuyên ngành → cân nhắc `bge-m3`
  khi cần, đánh đổi RAM.
- **Chunk MITRE ATT&CK (JSON lồng nhau)** khó hơn Markdown → làm OWASP trước cho quen.
- **Chunking quyết định ~50% chất lượng** → `ingestion/chunker.py` là nơi tinh chỉnh chính.
- Lọc theo metadata quyền/nguồn *trước* khi đưa vào ngữ cảnh nếu sau này có dữ liệu nhạy cảm.

## 8. Lệnh nhanh

```bash
# Cài đặt
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt

# Chuẩn bị dữ liệu
git clone --depth 1 https://github.com/OWASP/CheatSheetSeries data/raw/owasp

# Index (chạy lại mỗi khi thêm dữ liệu)
python -m ingestion.indexer

# Hỏi đáp
python app_cli.py
```
