"""Giao diện web SecRAG (Streamlit) — chat hỏi đáp có trích nguồn.

Chạy:  streamlit run ui/app.py     (nhớ đã activate .venv và có GROQ_API_KEY trong .env)

Sidebar cho phép LỌC theo metadata và BẬT/TẮT từng bước retrieval (hybrid/rerank/MMR)
ngay trên web — đúng các cờ đã đo ở Phase 5.
"""
import base64
from pathlib import Path

import streamlit as st

from config import settings
from retrieval.pipeline import retrieve
from generation.llm import answer

st.set_page_config(page_title="SecRAG", page_icon="🛡️", layout="centered")

# Ảnh nền (tối/chìm). Đọc 1 lần, nhúng base64 nên không cần serve file tĩnh.
# Chỉnh 2 số BG_DIM để ảnh mờ hơn (số lớn hơn = tối hơn) / rõ hơn (nhỏ hơn).
BG_DIM_TOP, BG_DIM_BOT = 0.80, 0.90


@st.cache_data
def _bg_data_uri() -> str:
    f = Path(__file__).parent / "assets" / "bg.jpg"
    if not f.exists():
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode()

# CSS: thẩm mỹ "terminal / hacker console" — nền gần đen, mono, accent teal-neon.
# Lưu ý: KHÔNG để dòng trống bên trong <style> (Streamlit chạy qua Markdown trước,
# dòng trống sẽ cắt khối và render CSS thành text).
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?'
    'family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600'
    '&display=swap" rel="stylesheet">'
    "<style>"
    ":root{--bg:#0a0e12;--bg2:#121820;--line:#1e2730;--accent:#2ee6d6;"
    "--accent-dim:#14343a;--text:#c9d1d9;--muted:#6b7a89;"
    "--mono:'JetBrains Mono',ui-monospace,monospace;}"
    ".stApp{background-color:var(--bg);"
    "background-image:repeating-linear-gradient(to bottom,rgba(46,230,214,0.04) 0px,"
    "rgba(46,230,214,0.04) 1px,transparent 1px,transparent 3px);}"
    ".block-container{max-width:860px;padding-top:2.2rem;}"
    "html,body{font-family:'Inter',sans-serif;}"
    "@keyframes blink{50%{opacity:0;}}"
    "h1{font-family:var(--mono);letter-spacing:-0.5px;font-weight:700;}"
    "h1::after{content:'\\2588';color:var(--accent);margin-left:8px;"
    "animation:blink 1.1s step-end infinite;}"
    "[data-testid='stCaptionContainer']{font-family:var(--mono);color:var(--muted);}"
    ".sys-line{font-family:var(--mono);font-size:0.8rem;color:var(--muted);"
    "margin:2px 0 10px;letter-spacing:0.3px;}"
    ".sys-line .dot{color:#3ddc84;}.sys-line b{color:var(--text);font-weight:500;}"
    ".hero-hint{font-family:var(--mono);color:var(--muted);font-size:0.85rem;margin:14px 0 10px;}"
    ".stButton button{font-family:var(--mono);background:var(--bg2);color:var(--muted);"
    "border:1px solid var(--line);border-radius:8px;font-size:0.82rem;"
    "transition:border-color .15s,color .15s,box-shadow .15s;}"
    ".stButton button:hover{border-color:var(--accent);color:var(--accent);"
    "box-shadow:0 0 16px rgba(46,230,214,0.12);}"
    ".stChatMessage{border-radius:12px;border:1px solid var(--line);background:var(--bg2);}"
    "[data-testid='stChatInput']{border:1px solid var(--accent-dim);border-radius:12px;"
    "box-shadow:0 0 0 1px rgba(46,230,214,0.08),0 0 24px rgba(46,230,214,0.06);}"
    "[data-testid='stChatInput']:focus-within{border-color:var(--accent);"
    "box-shadow:0 0 0 1px var(--accent),0 0 28px rgba(46,230,214,0.18);}"
    "[data-testid='stChatInput'] textarea{font-family:var(--mono);}"
    "section[data-testid='stSidebar']{border-right:1px solid var(--line);}"
    "section[data-testid='stSidebar'] h3{font-family:var(--mono);color:var(--accent);"
    "font-size:0.82rem;text-transform:uppercase;letter-spacing:1.5px;}"
    ".src-card{background:var(--bg2);border:1px solid var(--line);"
    "border-left:2px solid var(--accent);border-radius:8px;padding:9px 13px;"
    "margin:7px 0;font-size:0.88rem;font-family:var(--mono);}"
    ".src-card b{color:var(--text);}"
    ".tag{background:transparent;color:var(--accent);border:1px solid var(--accent-dim);"
    "border-radius:5px;padding:1px 7px;font-size:0.7rem;margin-left:6px;"
    "font-family:var(--mono);letter-spacing:0.5px;}"
    "[data-testid='stExpander'] summary{font-family:var(--mono);}"
    "</style>",
    unsafe_allow_html=True,
)

# Nền ảnh tối/chìm — ghi đè .stApp; 3 lớp từ trên xuống: scanline teal → lớp tối → ảnh.
_bg = _bg_data_uri()
if _bg:
    st.markdown(
        "<style>.stApp{background-color:#0a0e12;background-image:"
        "repeating-linear-gradient(to bottom,rgba(46,230,214,0.04) 0px,"
        "rgba(46,230,214,0.04) 1px,transparent 1px,transparent 3px),"
        f"linear-gradient(rgba(10,14,18,{BG_DIM_TOP}),rgba(10,14,18,{BG_DIM_BOT})),"
        f"url('{_bg}');"
        "background-size:auto,auto,cover;"
        "background-position:center,center,center;"
        "background-repeat:repeat,no-repeat,no-repeat;}"
        "</style>",
        unsafe_allow_html=True,
    )

st.title("SecRAG")
st.caption("// Trợ lý kiến thức pentest — hỏi đáp trên OWASP + MITRE ATT&CK, luôn kèm trích nguồn.")
st.markdown(
    "<div class='sys-line'><span class='dot'>●</span> online"
    f"&nbsp;&nbsp;·&nbsp;&nbsp;model: <b>{settings.GROQ_MODEL}</b>"
    "&nbsp;&nbsp;·&nbsp;&nbsp;corpus: <b>OWASP · MITRE ATT&CK</b></div>",
    unsafe_allow_html=True,
)

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


# Màu badge theo chủ đề — mỗi category một sắc để quét nhanh bằng mắt
CAT_COLORS = {
    "web": "#2ee6d6", "auth": "#ffb454", "crypto": "#c792ea", "mobile": "#7ee787",
    "api": "#56b6c2", "infra": "#ff7b72", "framework": "#79c0ff",
    "attack": "#ff6b9d", "general": "#8b949e",
}


def _tag(text: str, color: str) -> str:
    return (f"<span class='tag' style='color:{color};border-color:{color}55'>"
            f"{text}</span>")


def render_sources(chunks: list[dict], info: dict) -> None:
    label = f"🔎 {len(chunks)} nguồn tham chiếu"
    if info.get("rewritten"):
        label += f"  ·  truy vấn: {info['rewritten']}"
    with st.expander(label):
        for i, c in enumerate(chunks, 1):
            m = c["metadata"]
            cat = m.get("category", "")
            tags = _tag(cat, CAT_COLORS.get(cat, "#8b949e")) if cat else ""
            vc = ", ".join(m.get("vuln_class", []))
            if vc:
                tags += _tag(vc, "#2ee6d6")
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

# Empty-state: gợi ý câu hỏi mẫu (bấm để hỏi nhanh), lấp khoảng trống khi chưa chat
EXAMPLES = [
    "Cách phòng chống SQL injection?",
    "OWASP Top 10 gồm những gì?",
    "Lateral movement trong MITRE ATT&CK?",
]
if not st.session_state.messages:
    st.markdown("<div class='hero-hint'>// thử một câu hỏi mẫu:</div>",
                unsafe_allow_html=True)
    for col, ex in zip(st.columns(len(EXAMPLES)), EXAMPLES):
        if col.button(ex, use_container_width=True, key=f"ex_{ex}"):
            q = ex

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
