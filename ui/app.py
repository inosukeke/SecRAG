"""Giao diện web SecRAG (Streamlit) — chat hỏi đáp có trích nguồn.

Chạy:  streamlit run ui/app.py     (nhớ đã activate .venv và có GROQ_API_KEY trong .env)

Sidebar cho phép LỌC theo metadata và BẬT/TẮT từng bước retrieval (hybrid/rerank/MMR)
ngay trên web — đúng các cờ đã đo ở Phase 5.
"""
import streamlit as st

from config import settings
from retrieval.pipeline import retrieve
from generation.llm import answer

st.set_page_config(page_title="SecRAG", page_icon="🛡️", layout="centered")

# CSS nhẹ: gọn gàng, dịu mắt
st.markdown("""
<style>
  .block-container {max-width: 820px; padding-top: 2.2rem;}
  .stChatMessage {border-radius: 12px;}
  .src-card {background:#f4f7f7; border:1px solid #e2e9e9; border-radius:10px;
             padding:8px 12px; margin:6px 0; font-size:0.9rem;}
  .tag {background:#0d7d84; color:#fff; border-radius:6px; padding:1px 7px;
        font-size:0.72rem; margin-left:6px;}
</style>
""", unsafe_allow_html=True)

st.title("🛡️ SecRAG")
st.caption("Trợ lý kiến thức pentest — hỏi đáp trên OWASP + MITRE ATT&CK, luôn kèm trích nguồn.")

# ---------------- Sidebar: lọc + cấu hình ----------------
with st.sidebar:
    st.subheader("Bộ lọc")
    cat = st.selectbox("Chủ đề (category)",
                       ["(tất cả)", "web", "auth", "crypto", "mobile", "api",
                        "infra", "framework", "general", "attack"])
    src = st.selectbox("Nguồn", ["(tất cả)", "owasp", "attack"])

    st.subheader("Cấu hình retrieval")
    settings.USE_QUERY_REWRITE = st.checkbox("Query rewrite (VN→EN)",
                                             value=settings.USE_QUERY_REWRITE)
    settings.USE_HYBRID = st.checkbox("Hybrid (BM25 + vector)", value=settings.USE_HYBRID)
    settings.USE_RERANK = st.checkbox("Rerank (cross-encoder)", value=settings.USE_RERANK)
    settings.USE_MMR = st.checkbox("MMR (đa dạng hoá)", value=settings.USE_MMR)
    settings.TOP_K = st.slider("Số chunk (TOP_K)", 3, 10, settings.TOP_K)
    st.caption(f"Model: `{settings.GROQ_MODEL}`")

where = {}
if cat != "(tất cả)":
    where["category"] = cat
if src != "(tất cả)":
    where["source"] = src


def render_sources(chunks: list[dict], info: dict) -> None:
    label = f"🔎 {len(chunks)} nguồn tham chiếu"
    if info.get("rewritten"):
        label += f"  ·  truy vấn: {info['rewritten']}"
    with st.expander(label):
        for i, c in enumerate(chunks, 1):
            m = c["metadata"]
            vc = ", ".join(m.get("vuln_class", []))
            tags = f"<span class='tag'>{m.get('category', '')}</span>"
            if vc:
                tags += f"<span class='tag'>{vc}</span>"
            st.markdown(
                f"<div class='src-card'><b>[{i}] {m.get('source')}/{m.get('title')}</b>"
                f"{tags}</div>", unsafe_allow_html=True)


# ---------------- Lịch sử hội thoại ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("chunks"):
            render_sources(msg["chunks"], msg.get("info", {}))

# ---------------- Ô nhập ----------------
q = st.chat_input("Hỏi về bảo mật… (vd: cách phòng chống SQL injection)")
if q:
    st.session_state.messages.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        with st.spinner("Đang truy xuất tài liệu… (lần đầu sẽ nạp model, hơi lâu)"):
            chunks, info = retrieve(q, where=where or None)

        if not chunks:
            txt = "Không tìm thấy tài liệu phù hợp với bộ lọc hiện tại."
            st.warning(txt)
            st.session_state.messages.append({"role": "assistant", "content": txt})
        else:
            full = st.write_stream(answer(q, chunks, stream=True))
            render_sources(chunks, info)
            st.session_state.messages.append(
                {"role": "assistant", "content": full, "chunks": chunks, "info": info})
