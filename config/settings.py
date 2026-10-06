"""Cấu hình tập trung cho SecRAG. Chỉnh ở đây, không rải hằng số khắp code."""
from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# Console Windows mặc định không phải UTF-8 -> in tiếng Việt sẽ lỗi charmap.
# Mọi module đều import settings nên ép UTF-8 ở đây là fix tập trung cho cả dự án.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

load_dotenv()

# --- Đường dẫn ---
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"          # tài liệu nguồn (.md) bỏ vào đây
STORE_PATH = ROOT / "data" / "store.pkl"  # vector store (NumPy) sau khi index

# --- Embedding (chạy LOCAL) ---
# Model embedding đa ngôn ngữ chất lượng cao (1024-dim, 2024), chạy GPU.
# Nhẹ hơn cho CPU (kém hơn): "paraphrase-multilingual-MiniLM-L12-v2" (~470MB, 384-dim)
EMBED_MODEL = "BAAI/bge-m3"   # ~2.2GB, không cần prefix query/passage

# --- Chunking ---
CHUNK_SIZE = 500          # số "từ" mỗi chunk (xấp xỉ token)
CHUNK_OVERLAP = 75        # ~15% overlap để không cắt đứt ngữ cảnh

# --- Retrieval ---
TOP_K = 5                 # số chunk CUỐI đưa vào ngữ cảnh cho LLM

# --- Retrieval nâng cao (Phase 3) ---
CANDIDATES_K = 30         # số ứng viên mỗi retriever lấy ra trước khi rerank
RRF_K = 60                # hằng số Reciprocal Rank Fusion khi gộp hybrid
USE_QUERY_REWRITE = True  # dịch/mở rộng câu hỏi (VN->EN) trước khi search
USE_HYBRID = True         # gộp BM25 (keyword) + vector (ngữ nghĩa)
USE_RERANK = True         # cross-encoder chấm lại ứng viên (tắt: USE_RERANK=False)
USE_MMR = False           # eval Phase 5 cho thấy MMR làm GIẢM nhẹ Hit@5 cho tra cứu
                          # factual -> tắt mặc định; bật cho câu hỏi mở/khám phá
MMR_LAMBDA = 0.7          # 1.0=chỉ liên quan; 0.0=chỉ đa dạng; 0.7 cân bằng
# Chạy trên GPU (RTX 3060) nên dùng model chất lượng cao.
RERANK_MODEL = "BAAI/bge-reranker-base"   # ~1GB, cần GPU cho mượt
# Nếu quay lại CPU: đổi sang "cross-encoder/ms-marco-MiniLM-L-6-v2" (~90MB, nhẹ)

# --- LLM (Groq, cloud free) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "qwen/qwen3.8-27b"   # tiếng Việt tốt + không từ chối câu hỏi bảo mật học tập
# gpt-oss-120b/20b mạnh nhưng TỪ CHỐI chủ đề offensive. Xem model: client.models.list()
LLM_TEMPERATURE = 0.1     # thấp = bám tài liệu, ít bịa

COLLECTION_NAME = "secrag"
