# SecRAG — Trợ lý kiến thức Pentest (RAG, chạy local/free)

Hệ thống RAG hỏi đáp trên tài liệu an ninh mạng công khai, phục vụ **học tập &
pentest có phép**. LLM chạy trên **Groq** (cloud, free), phần embedding + vector
DB chạy **local nhẹ** nên không ngốn tài nguyên máy.

```
Câu hỏi ─► Embedding(local) ─► Chroma(local) ─► top-k chunk ─► Groq LLM ─► Trả lời + nguồn
```

## 1. Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows PowerShell
pip install -r requirements.txt
```

Lấy API key free tại https://console.groq.com/keys rồi:

```bash
copy .env.example .env
```

Mở `.env`, dán key vào `GROQ_API_KEY`.

### (Tùy chọn) Tăng tốc bằng GPU NVIDIA

`pip install torch` mặc định là bản **CPU** (embedding + reranker sẽ chậm). Nếu có
GPU NVIDIA, cài bản CUDA để chạy nhanh hơn nhiều (rerank ~1.6s/câu thay vì ~6s+):

```bash
.venv\Scripts\python.exe -m pip uninstall -y torch
.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu124
```

Kiểm tra: `python -c "import torch; print(torch.cuda.is_available())"` → `True`.
sentence-transformers tự dùng GPU, không cần sửa code. Máy chỉ có CPU thì bỏ qua
bước này và đổi `RERANK_MODEL` sang `cross-encoder/ms-marco-MiniLM-L-6-v2` trong
`config/settings.py` cho nhẹ.

## 2. Chuẩn bị dữ liệu

Bỏ file Markdown vào `data/raw/<tên-nguồn>/`. Tên thư mục con = nhãn "nguồn"
hiển thị khi trích dẫn. Gợi ý bắt đầu với **OWASP Cheat Sheets** (thuần Markdown,
kích thước vừa):

```bash
git clone --depth 1 https://github.com/OWASP/CheatSheetSeries data/raw/owasp
```

Muốn thêm (tùy chọn, HackTricks khá lớn):

```bash
git clone --depth 1 https://github.com/OWASP/wstg data/raw/wstg
git clone --depth 1 https://github.com/HackTricks-wiki/hacktricks data/raw/hacktricks
```

> Loader Markdown tự quét mọi file `.md`/`.mdx` bên dưới `data/raw/`, nên chỉ cần clone vào đó.

**MITRE ATT&CK** (dữ liệu JSON có cấu trúc, dùng loader riêng `attack_loader.py`):

```bash
mkdir -p data/raw/attack
curl -L -o data/raw/attack/enterprise-attack.json https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json
```

## 3. Index (chạy 1 lần, hoặc mỗi khi thêm dữ liệu)

```bash
python -m ingestion.indexer
```

Lần đầu sẽ tải model embedding (~470MB). Sau đó ghi vector vào `data/store.pkl`.

## 4. Hỏi đáp

**Giao diện web (khuyến nghị):**

```bash
streamlit run ui/app.py
```

Mở http://localhost:8501 — chat có trích nguồn; sidebar để lọc (category/nguồn) và
bật/tắt hybrid/rerank/MMR + chỉnh TOP_K.

**Dòng lệnh:**

```bash
python app_cli.py
```

Ví dụ câu hỏi: *"cách phòng chống SQL injection?"*, *"kỹ thuật Pass the Hash là gì?"*.
CLI hỗ trợ lọc: `source=attack lateral movement`, `category=web ...`.

## Cấu trúc

| Thư mục | Vai trò |
|---------|---------|
| `config/` | Cấu hình tập trung (model, chunk size, top_k) |
| `ingestion/` | loader → chunker → indexer |
| `retrieval/` | tìm kiếm vector (Phase 3: + hybrid, rerank) |
| `generation/` | prompt + Groq client |
| `app_cli.py` | pipeline end-to-end trên dòng lệnh |

## Roadmap

- [x] **P0–1** Setup + ingest Markdown + index (vector store NumPy)
- [x] **P2** Retrieve + generate (Groq) + citation
- [x] **P3** query-rewrite + hybrid + rerank + MMR + lọc metadata + loader ATT&CK
- [x] **P4** Giao diện web Streamlit: `streamlit run ui/app.py`
- [x] **P5** Eval retrieval: `python -m eval.run_eval` (Hit@k/MRR, A/B preset)

Tùy chọn còn lại: loader CVE/KEV, eval chất lượng câu trả lời (RAGAS), FastAPI SSE.

## Nguyên tắc nội dung
Chỉ dùng để **hiểu bản chất & tra cứu** phục vụ học tập/kiểm thử có phép.
Không dùng để tấn công hệ thống của người khác.
