"""
AI Text Processor — Streamlit frontend.

Sends user input (email + text or URL) to the FastAPI backend, which forwards
it to the n8n workflow for Gemini-powered summarisation, Google Sheets
logging, and email delivery.
"""

from __future__ import annotations

import os
from html import escape

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(
    page_title="AI Text Processor",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ---------- Layout ---------- */
    .block-container { max-width: 1080px; padding-top: 1.2rem; padding-bottom: 4rem; }
    header[data-testid="stHeader"] { background: transparent; }
    footer { visibility: hidden; }

    /* ---------- Hero ---------- */
    .hero {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #db2777 100%);
        border-radius: 18px;
        padding: 2.4rem 2.2rem;
        color: white;
        margin: 0 0 1.8rem 0;
        box-shadow: 0 12px 32px rgba(79, 70, 229, 0.28);
    }
    .hero h1 {
        font-size: 2.3rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: white;
        margin: 0;
        line-height: 1.15;
    }
    .hero .tagline {
        font-size: 1.05rem;
        opacity: 0.92;
        margin: 0.6rem 0 0 0;
        max-width: 640px;
    }
    .hero .badges { margin-top: 1.1rem; display: flex; gap: 8px; flex-wrap: wrap; }
    .badge {
        padding: 4px 12px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.25);
        font-size: 0.78rem;
        font-weight: 500;
        color: white;
        letter-spacing: 0.02em;
    }

    /* ---------- Sections ---------- */
    .section-title {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #94a3b8;
        font-weight: 700;
        margin: 1.5rem 0 0.6rem 0;
    }

    /* ---------- Summary card ---------- */
    .summary-card {
        background: linear-gradient(135deg, rgba(79, 70, 229, 0.12) 0%, rgba(6, 182, 212, 0.10) 100%);
        border: 1px solid rgba(79, 70, 229, 0.35);
        border-left: 4px solid #4f46e5;
        border-radius: 12px;
        padding: 1.4rem 1.5rem;
        margin: 0.4rem 0 1.2rem 0;
    }
    .summary-card .label {
        text-transform: uppercase;
        font-size: 0.72rem;
        letter-spacing: 0.14em;
        color: #818cf8;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .summary-card .body {
        font-size: 1.04rem;
        line-height: 1.65;
    }

    /* ---------- Key points ---------- */
    .kp-list { list-style: none; padding: 0; margin: 0.4rem 0 1.2rem 0; }
    .kp-list li {
        display: flex;
        gap: 0.85rem;
        align-items: flex-start;
        padding: 0.85rem 1rem;
        margin-bottom: 0.55rem;
        background: rgba(124, 58, 237, 0.08);
        border: 1px solid rgba(124, 58, 237, 0.22);
        border-left: 3px solid #7c3aed;
        border-radius: 8px;
        font-size: 0.98rem;
        line-height: 1.55;
    }
    .kp-num {
        flex-shrink: 0;
        width: 26px; height: 26px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 0.85rem;
    }

    /* ---------- Status pills ---------- */
    .status-row { display: flex; gap: 0.6rem; flex-wrap: wrap; margin: 0.6rem 0 1.2rem 0; }
    .pill {
        padding: 5px 13px;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        border: 1px solid;
    }
    .pill-ok    { background: rgba(34, 197, 94, 0.12); border-color: rgba(34, 197, 94, 0.4); color: #4ade80; }
    .pill-warn  { background: rgba(234, 179, 8, 0.12); border-color: rgba(234, 179, 8, 0.4); color: #facc15; }
    .pill-err   { background: rgba(239, 68, 68, 0.12); border-color: rgba(239, 68, 68, 0.4); color: #f87171; }
    .pill .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
    .pill-ok   .dot { background: #4ade80; }
    .pill-warn .dot { background: #facc15; }
    .pill-err  .dot { background: #f87171; }

    /* ---------- Buttons ---------- */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        border: none;
        color: white;
        font-weight: 600;
        padding: 0.7rem 1.4rem;
        border-radius: 10px;
        font-size: 0.98rem;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
        transition: transform 0.08s ease, box-shadow 0.18s ease;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 22px rgba(79, 70, 229, 0.55);
    }
    div.stButton > button[kind="secondary"] {
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.18);
        font-weight: 500;
    }

    /* ---------- Metric cards ---------- */
    [data-testid="stMetric"] {
        background: rgba(148, 163, 184, 0.06);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 12px;
        padding: 1rem 1.2rem;
    }
    [data-testid="stMetricLabel"] { font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; }

    /* ---------- Inputs ---------- */
    .stTextInput input, .stTextArea textarea {
        border-radius: 8px !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
    }
    .stTextArea textarea { font-size: 0.95rem !important; line-height: 1.55; }

    /* ---------- Tabs ---------- */
    button[role="tab"] { font-weight: 600; padding: 0.5rem 1rem; }
    button[role="tab"][aria-selected="true"] { color: #818cf8; }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); }
    [data-testid="stSidebar"] * { color: rgba(255, 255, 255, 0.86); }
    [data-testid="stSidebar"] .stMarkdown code {
        background: rgba(255,255,255,0.08);
        color: #c4b5fd;
        padding: 2px 6px; border-radius: 4px;
    }

    /* ---------- Misc ---------- */
    hr { margin: 1.5rem 0; opacity: 0.15; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <h1>AI Text Processor</h1>
      <p class="tagline">Paste any text or article URL and get a polished summary, three key takeaways,
      a logged row in Google Sheets, and an email delivered to your inbox — powered by Google Gemini.</p>
      <div class="badges">
        <span class="badge">Streamlit</span>
        <span class="badge">FastAPI</span>
        <span class="badge">n8n AI Agent</span>
        <span class="badge">Google Gemini</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Service")
    st.markdown(f"`{BACKEND_URL}`")

    if st.button("Run health check", use_container_width=True):
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=5)
            if r.ok:
                st.success("Backend online")
            else:
                st.error(f"Status {r.status_code}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Unreachable: {exc}")

    st.markdown("---")
    st.markdown("### Workflow")
    st.markdown(
        """
        1. Submit email + text or URL  
        2. Backend issues a unique `session_id`  
        3. n8n routes through the Gemini AI Agent  
        4. Result is appended to Google Sheets  
        5. Summary is emailed to you
        """
    )

    st.markdown("---")
    st.markdown("### Tips")
    st.caption(
        "Use text **200–2,000 words** for the most natural summaries. "
        "URLs work best on static HTML pages (e.g. Wikipedia)."
    )

# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">1 · Choose input</div>', unsafe_allow_html=True)

tab_text, tab_url = st.tabs(["Paste text", "From URL (bonus)"])

with tab_text:
    text_input = st.text_area(
        "Your text",
        height=260,
        placeholder="Paste an article, blog post, or any text you want summarised...",
        label_visibility="collapsed",
    )

with tab_url:
    url_input = st.text_input(
        "Article URL",
        placeholder="https://example.com/some-article",
        label_visibility="collapsed",
    )
    st.caption("The backend will fetch the page and extract its visible content.")

st.markdown('<div class="section-title">2 · Recipient &amp; submit</div>', unsafe_allow_html=True)

with st.form("processor_form", clear_on_submit=False):
    col_email, col_btn = st.columns([3, 1], gap="medium")
    with col_email:
        email = st.text_input(
            "Email",
            placeholder="you@example.com",
            label_visibility="collapsed",
        )
    with col_btn:
        submitted = st.form_submit_button(
            "Process",
            type="primary",
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# Submit handler
# ---------------------------------------------------------------------------
if submitted:
    if not email:
        st.error("Email is required.")
        st.stop()

    text_value = (text_input or "").strip()
    url_value = (url_input or "").strip()

    if not text_value and not url_value:
        st.error("Provide some text or a URL.")
        st.stop()

    payload: dict[str, str] = {"email": email}
    if url_value:
        payload["url"] = url_value
    else:
        payload["text"] = text_value

    with st.spinner("Running through n8n + Gemini…"):
        try:
            resp = requests.post(f"{BACKEND_URL}/process", json=payload, timeout=120)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to reach backend: {exc}")
            st.stop()

    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:  # noqa: BLE001
            detail = resp.text
        st.error(f"Backend error ({resp.status_code}): {detail}")
        st.stop()

    data = resp.json()

    # ---- Result ----
    st.markdown("---")
    st.markdown('<div class="section-title">Result</div>', unsafe_allow_html=True)

    # Quick stats row
    c1, c2, c3 = st.columns(3)
    c1.metric("Session ID", data.get("session_id", "—"))
    c2.metric("Source", (data.get("source") or "—").upper())
    c3.metric("Characters", f"{data.get('chars_sent', 0):,}")

    # Pull summary / key points
    n8n_body = data.get("n8n_response")
    summary, key_points = "", []
    if isinstance(n8n_body, dict):
        summary = (n8n_body.get("summary") or "").strip()
        kp = n8n_body.get("key_points")
        if isinstance(kp, list):
            key_points = [str(p) for p in kp if p]

    # Status pills — adjust based on what actually returned
    sheet_pill = '<span class="pill pill-ok"><span class="dot"></span>Logged to Sheets</span>'
    if summary:
        ai_pill = '<span class="pill pill-ok"><span class="dot"></span>AI completed</span>'
    else:
        ai_pill = '<span class="pill pill-warn"><span class="dot"></span>AI response missing</span>'
    if summary and key_points:
        email_pill = '<span class="pill pill-ok"><span class="dot"></span>Email sent</span>'
    else:
        email_pill = '<span class="pill pill-warn"><span class="dot"></span>Email status unknown</span>'

    st.markdown(
        f'<div class="status-row">{ai_pill}{sheet_pill}{email_pill}</div>',
        unsafe_allow_html=True,
    )

    # Summary
    if summary:
        st.markdown(
            f"""
            <div class="summary-card">
              <div class="label">Summary</div>
              <div class="body">{escape(summary)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Key points
    if key_points:
        st.markdown('<div class="section-title">Key points</div>', unsafe_allow_html=True)
        items_html = "".join(
            f'<li><span class="kp-num">{i + 1}</span><span>{escape(p)}</span></li>'
            for i, p in enumerate(key_points)
        )
        st.markdown(f'<ul class="kp-list">{items_html}</ul>', unsafe_allow_html=True)

    if not summary and not key_points:
        st.warning(
            "The workflow accepted your request but didn't return summary content. "
            "Check the n8n Executions tab — most likely the email step failed before "
            "the response was sent back."
        )

    with st.expander("Inspect raw n8n response"):
        st.json(n8n_body if n8n_body else {"info": "n8n did not return a JSON body"})

    if summary:
        st.success(
            "Done. A copy of the summary and key points has also been emailed to you "
            "(check spam if it doesn't appear)."
        )
