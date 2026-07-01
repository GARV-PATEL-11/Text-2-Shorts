"""Text-2-Shorts — AI Workflow Dashboard v3.0"""
from __future__ import annotations

import datetime as _dt
import html as _html_mod
import json
import time
from typing import Any

import requests

import streamlit as st


# ── Constants ─────────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000"
POLL_INTERVAL_S = 3.0
VERSION = "3.0"

PIPELINE_STAGES: list[tuple[str, str]] = [
    ("validate_input", "Validate"),
    ("generate_outline", "Outline"),
    ("outline_critique", "Critique"),
    ("visual_planning", "Visual Plan"),
    ("visual_plan_critique", "Plan Review"),
    ("manim_code_generation", "Code Gen"),
    ("scene_rendering", "Render"),
    ("video_assembly", "Assemble"),
    ]

APPROACHES = [
    "Classic Linear Narrative",
    "Conceptual Zoom",
    "Problem-Solution Arc",
    ]

NAV_PAGES = ["Generate", "Sessions", "Pipeline", "Logs"]

STATUS_DOT_CLS = {
    "completed": "success", "running": "running", "failed": "failed",
    "pending": "pending", "queued": "queued", "skipped": "skipped",
    "idle": "pending",
    }
STATUS_LABEL = {
    "completed": "SUCCESS", "running": "RUNNING", "failed": "FAILED",
    "pending": "PENDING", "queued": "QUEUED", "skipped": "SKIPPED",
    "idle": "IDLE",
    }

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Text-2-Shorts",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
    )

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Inter:wght@400;500;600
;700&display=swap');

/* ── Reset ── */
#MainMenu, footer { visibility: hidden; }
.stApp > header { display: none !important; }
*, *::before, *::after { box-sizing: border-box; }
html, body { font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important; }
.stApp { background: #F5F9FF !important; font-family: 'Inter', sans-serif !important; }
.main .block-container { padding: 0 0 2rem 0 !important; max-width: 100% !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #06162B !important;
    border-right: 1px solid #0F2745 !important;
}
[data-testid="stSidebar"] * { color: #94A3B8 !important; font-family: 'Inter', sans-serif !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; }
[data-testid="stSidebar"] button {
    background: transparent !important;
    border: none !important;
    color: #94A3B8 !important;
    text-align: left !important;
    padding: 9px 14px !important;
    font-size: 0.84rem !important;
    font-family: 'Inter', sans-serif !important;
    border-radius: 6px !important;
    margin: 1px 8px !important;
    justify-content: flex-start !important;
    font-weight: 500 !important;
    width: calc(100% - 16px) !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(255,255,255,0.06) !important;
    color: #E2E8F0 !important;
}
[data-testid="stSidebar"] button[kind="primary"] {
    background: rgba(45,109,178,0.18) !important;
    color: #FFFFFF !important;
    border-left: 3px solid #2D6DB2 !important;
    border-radius: 0 6px 6px 0 !important;
    padding-left: 11px !important;
}

/* ── App header ── */
.app-header {
    background: #FFFFFF;
    border-bottom: 1px solid #EAF3FF;
    padding: 0 32px;
    height: 58px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 1px 6px rgba(6,22,43,0.05);
}
.app-logo {
    font-family: 'Poppins', sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: #06162B !important;
    letter-spacing: -0.3px;
}
.app-badge {
    font-size: 0.65rem;
    color: #64748B !important;
    background: #F5F9FF;
    border: 1px solid #C9E0FF;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 10px;
    font-family: 'Inter', sans-serif;
}
.session-chip {
    font-family: 'Courier New', monospace;
    font-size: 0.76rem;
    color: #1E4F85 !important;
    background: #EAF3FF;
    border: 1px solid #C9E0FF;
    padding: 4px 12px;
    border-radius: 6px;
}

/* ── Status dots ── */
.dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
    vertical-align: middle;
}
.dot.success   { background: #22C55E; }
.dot.running   { background: #3B82F6; }
.dot.failed    { background: #EF4444; }
.dot.pending   { background: #9CA3AF; }
.dot.queued    { background: #F59E0B; }
.dot.skipped   { background: #D1D5DB; }
.dot.critic    { background: #F97316; }
.dot.refactor  { background: #A855F7; }
.dot.bugfix    { background: #EAB308; }
.dot.validated { background: #10B981; }
.dot.retry     { background: #06B6D4; }
.dot.action    { background: #EC4899; }
.dot.warning   { background: #F59E0B; }


/* ── Status indicator (dot + label inline) ── */
.status-ind {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.71rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    font-family: 'Inter', sans-serif;
}
.status-ind.success  { color: #16A34A !important; }
.status-ind.running  { color: #2563EB !important; }
.status-ind.failed   { color: #DC2626 !important; }
.status-ind.pending  { color: #6B7280 !important; }
.status-ind.queued   { color: #D97706 !important; }
.status-ind.skipped  { color: #9CA3AF !important; }
.status-ind.critic   { color: #EA580C !important; }
.status-ind.refactor { color: #9333EA !important; }

/* ── Cards ── */
.card {
    background: #FFFFFF;
    border: 1px solid #EAF3FF;
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(6,22,43,0.04);
}
.card-hover:hover { box-shadow: 0 4px 16px rgba(6,22,43,0.08); }

/* ── Section heading ── */
.section-hd {
    font-family: 'Poppins', sans-serif;
    font-size: 0.9rem;
    font-weight: 700;
    color: #06162B !important;
    margin: 20px 0 10px;
    padding-bottom: 8px;
    border-bottom: 2px solid #EAF3FF;
}

/* ── Counter cards (status dashboard) ── */
.counter-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 14px;
}
.counter-card {
    background: #FFFFFF;
    border: 1px solid #EAF3FF;
    border-radius: 10px;
    padding: 12px 14px;
    min-width: 85px;
    text-align: center;
    border-top: 3px solid #E2E8F0;
    flex: 1;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}
.counter-card .c-val {
    font-family: 'Poppins', sans-serif;
    font-size: 1.55rem;
    font-weight: 800;
    color: #06162B !important;
    line-height: 1.1;
}
.counter-card .c-lbl {
    font-size: 0.64rem;
    color: #64748B !important;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-top: 3px;
}
.counter-card.success  { border-top-color: #22C55E; }
.counter-card.failed   { border-top-color: #EF4444; }
.counter-card.running  { border-top-color: #3B82F6; }
.counter-card.pending  { border-top-color: #9CA3AF; }
.counter-card.critic   { border-top-color: #F97316; }
.counter-card.refactor { border-top-color: #A855F7; }
.counter-card.skipped  { border-top-color: #D1D5DB; }

/* ── Pipeline visualization ── */
.pipe-wrap {
    display: flex;
    align-items: flex-start;
    overflow-x: auto;
    padding: 14px 0 8px;
    gap: 0;
}
.pipe-stage {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 88px;
    flex: 0 0 auto;
}
.pipe-circle {
    width: 38px; height: 38px;
    border-radius: 50%;
    border: 2px solid;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.82rem;
    font-weight: 700;
}
.pipe-circle.success { background:#F0FDF4; border-color:#22C55E; color:#16A34A !important; }
.pipe-circle.running { background:#EFF6FF; border-color:#3B82F6; color:#2563EB !important; }
.pipe-circle.failed  { background:#FEF2F2; border-color:#EF4444; color:#DC2626 !important; }
.pipe-circle.pending { background:#F8FAFC; border-color:#C9E0FF; color:#9CA3AF !important; }
.pipe-circle.skipped { background:#F8FAFC; border-color:#E2E8F0; color:#CBD5E1 !important; }
.pipe-lbl {
    font-size: 0.66rem; font-weight: 600; text-align: center;
    margin-top: 5px; max-width: 80px; line-height: 1.2;
    font-family: 'Inter', sans-serif;
}
.pipe-lbl.success { color: #16A34A !important; }
.pipe-lbl.running { color: #2563EB !important; }
.pipe-lbl.failed  { color: #DC2626 !important; }
.pipe-lbl.pending,
.pipe-lbl.skipped { color: #9CA3AF !important; }
.pipe-dur { font-size: 0.59rem; color: #94A3B8 !important; margin-top: 2px; }
.pipe-conn {
    flex: 1; height: 2px; margin-top: 18px;
    min-width: 12px; max-width: 44px;
}
.pipe-conn.done   { background: #22C55E; }
.pipe-conn.active { background: linear-gradient(90deg,#22C55E,#3B82F6); }
.pipe-conn.none   { background: #E2E8F0; }

/* ── Scene timeline ── */
.scene-tl {
    display: flex;
    gap: 4px;
    overflow-x: auto;
    padding: 6px 0 10px;
    flex-wrap: wrap;
}
.scene-tl-dot {
    width: 28px; height: 28px;
    border-radius: 50%;
    border: 2px solid;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.6rem;
    font-weight: 700;
    flex-shrink: 0;
    cursor: default;
}
.scene-tl-dot:hover { outline: 2px solid #2D6DB2; }
.scene-tl-dot.completed { background:#F0FDF4; border-color:#22C55E; color:#16A34A !important; }
.scene-tl-dot.running   { background:#EFF6FF; border-color:#3B82F6; color:#2563EB !important; }
.scene-tl-dot.failed    { background:#FEF2F2; border-color:#EF4444; color:#DC2626 !important; }
.scene-tl-dot.pending   { background:#F8FAFC; border-color:#E2E8F0; color:#9CA3AF !important; }
.scene-tl-dot.ready     { background:#F0FDF4; border-color:#22C55E; color:#16A34A !important; }
.scene-tl-dot.generating{ background:#F5F3FF; border-color:#DDD6FE; color:#7C3AED !important; }
.scene-tl-dot.rendering { background:#FFF7ED; border-color:#FED7AA; color:#C2410C !important; }

/* ── Metric tile ── */
.metric-tile {
    background: #FFFFFF;
    border: 1px solid #EAF3FF;
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}
.metric-tile .m-val {
    font-family: 'Poppins', sans-serif;
    font-size: 1.7rem;
    font-weight: 800;
    color: #06162B !important;
    line-height: 1;
    margin-bottom: 4px;
}
.metric-tile .m-lbl {
    font-size: 0.68rem;
    color: #64748B !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.metric-tile.blue  { border-top: 3px solid #2D6DB2; }
.metric-tile.green { border-top: 3px solid #22C55E; }
.metric-tile.red   { border-top: 3px solid #EF4444; }
.metric-tile.amber { border-top: 3px solid #F59E0B; }

/* ── Badge ── */
.badge {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 9px; border-radius: 20px;
    font-size: 0.68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.4px;
    font-family: 'Inter', sans-serif;
}
.badge.green { background:#F0FDF4; color:#16A34A !important; border:1px solid #BBF7D0; }
.badge.blue  { background:#EAF3FF; color:#1E4F85 !important; border:1px solid #C9E0FF; }
.badge.red   { background:#FEF2F2; color:#DC2626 !important; border:1px solid #FECACA; }
.badge.amber { background:#FFFBEB; color:#D97706 !important; border:1px solid #FDE68A; }
.badge.gray  { background:#F8FAFC; color:#6B7280 !important; border:1px solid #E2E8F0; }

/* ── Prose viewer (renders \\n as actual line-breaks) ── */
.prose-view {
    font-size: 0.82rem;
    line-height: 1.65;
    color: #374151 !important;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px 16px;
    max-height: 300px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: 'Inter', sans-serif;
}

/* ── Key-value info block ── */
.kv-block {
    display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px;
}
.kv-item {
    background: #F5F9FF; border: 1px solid #C9E0FF;
    border-radius: 6px; padding: 6px 12px;
    font-size: 0.78rem;
}
.kv-item .kv-k { color: #64748B !important; font-size: 0.67rem; text-transform: uppercase; letter-spacing: 0.4px; }
.kv-item .kv-v { color: #06162B !important; font-weight: 700; margin-top: 1px; }

/* ── Log table ── */
.log-wrap {
    background: #FFFFFF;
    border: 1px solid #EAF3FF;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}
.log-hdr {
    display: grid;
    grid-template-columns: 82px 68px 130px 130px 1fr 72px;
    gap: 6px;
    padding: 9px 14px;
    background: #06162B;
    color: #94A3B8 !important;
    font-size: 0.64rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    position: sticky;
    top: 0;
    z-index: 2;
    font-family: 'Inter', sans-serif;
}
.log-body { max-height: 520px; overflow-y: auto; }
.log-row {
    display: grid;
    grid-template-columns: 82px 68px 130px 130px 1fr 72px;
    gap: 6px;
    padding: 7px 14px;
    border-bottom: 1px solid #F1F5F9;
    align-items: start;
    border-left: 3px solid transparent;
    font-size: 0.77rem;
    font-family: 'Inter', sans-serif;
}
.log-row:hover { background: #F5F9FF; }
.log-row.debug    { border-left-color: #9CA3AF; }
.log-row.info     { border-left-color: #22C55E; }
.log-row.warning  { border-left-color: #F59E0B; }
.log-row.error    { border-left-color: #EF4444; }
.log-row.critical { border-left-color: #8B5CF6; }
.lvl {
    padding: 1px 5px; border-radius: 4px;
    font-size: 0.62rem; font-weight: 700;
    text-transform: uppercase; white-space: nowrap;
    font-family: 'Inter', sans-serif;
}
.lvl.debug    { background:#F1F5F9; color:#6B7280 !important; }
.lvl.info     { background:#F0FDF4; color:#16A34A !important; }
.lvl.warning  { background:#FFFBEB; color:#D97706 !important; }
.lvl.error    { background:#FEF2F2; color:#DC2626 !important; }
.lvl.critical { background:#F5F3FF; color:#7C3AED !important; }

/* ── Right panel ── */
.rp {
    background: #FFFFFF;
    border: 1px solid #EAF3FF;
    border-radius: 12px;
    padding: 14px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}
.rp-hdr {
    font-family: 'Poppins', sans-serif;
    font-size: 0.66rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.6px;
    color: #06162B !important;
    margin-bottom: 10px; padding-bottom: 8px;
    border-bottom: 2px solid #EAF3FF;
}
.rp-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 0; border-bottom: 1px solid #F1F5F9; font-size: 0.78rem;
}
.rp-lbl { color: #64748B !important; }
.rp-val { font-weight: 700; color: #06162B !important; font-family: 'Poppins', sans-serif; }

/* ── Forms ── */
.stTextArea textarea {
    border: 1px solid #C9E0FF !important;
    border-radius: 10px !important;
    background: #FFFFFF !important;
    color: #06162B !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.87rem !important;
}
.stTextArea textarea:focus {
    border-color: #2D6DB2 !important;
    box-shadow: 0 0 0 3px rgba(45,109,178,0.1) !important;
}
.stSelectbox > div > div,
.stTextInput > div > div > input {
    border: 1px solid #C9E0FF !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Primary button ── */
.stButton > button[kind="primary"]:not([data-testid*="sidebar"]) {
    background: #06162B !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    height: 46px !important;
}
.stButton > button[kind="primary"]:not([data-testid*="sidebar"]):hover {
    background: #143D6B !important;
    box-shadow: 0 4px 14px rgba(6,22,43,0.28) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid #EAF3FF; gap: 0; background: transparent; }
.stTabs [data-baseweb="tab"] {
    padding: 8px 16px; font-size: 0.8rem; font-weight: 600;
    color: #64748B !important; font-family: 'Inter', sans-serif !important;
}
.stTabs [aria-selected="true"] { color: #06162B !important; border-bottom: 2px solid #2D6DB2 !important; }

/* ── Typography ── */
h1, h2, h3, h4 { color: #06162B !important; font-family: 'Poppins', sans-serif !important; }
p, li           { color: #374151 !important; }
label           { color: #374151 !important; font-size: 0.84rem !important; font-family: 'Inter', sans-serif 
!important; }
.stTextArea label, .stSelectbox label, .stTextInput label {
    font-size: 0.81rem !important; font-weight: 600 !important; color: #374151 !important;
}
details summary { font-size: 0.86rem !important; font-weight: 600 !important; }

/* ── Layout helpers ── */
.content-pad { padding: 20px 28px 0 28px; }
.spacer-sm { height: 8px; }
.spacer-md { height: 16px; }
</style>
""", unsafe_allow_html=True
    )

# ── Session State ─────────────────────────────────────────────────────────────

_D: dict[str, Any] = {
    "page": "Generate",
    "session_id": None,
    "pipeline_status": "idle",
    "stages": [],
    "scene_progress": None,
    "render_status": None,
    "final_video_path": None,
    "outline": None,
    "outline_type": None,
    "scenes": None,
    "total_scenes": 0,
    "generate_error": None,
    "auto_poll": False,
    "log_level": "ALL",
    "log_stage": "",
    "log_search": "",
    }
for _k, _v in _D.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── API Helpers ───────────────────────────────────────────────────────────────

def _get(path: str, **kw) -> Any:
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=15, **kw)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _post(path: str, **kw) -> Any:
    try:
        r = requests.post(f"{API_BASE}{path}", timeout=15, **kw)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        raise exc


def fetch_stages(sid: str) -> dict | None:
    return _get(f"/stages/{sid}")


def fetch_sessions() -> list[dict]:
    d = _get("/sessions")
    return d.get("sessions", []) if d else []


def fetch_artifacts(sid: str) -> list[dict]:
    d = _get(f"/artifacts/{sid}")
    return d.get("artifacts", []) if d else []


def fetch_artifact(sid: str, atype: str) -> Any:
    d = _get(f"/artifact/{sid}/{atype}")
    return d.get("data") if d else None


def fetch_scene_progress(sid: str) -> dict | None:
    return _get(f"/scenes/{sid}/progress")


def fetch_render_status(sid: str) -> dict | None:
    return _get(f"/render/status/{sid}")


def fetch_outline(sid: str) -> dict | None:
    return _get(f"/outputs/{sid}/outline")


def fetch_scenes(sid: str) -> dict | None:
    return _get(f"/outputs/{sid}/scenes")


def fetch_logs(sid: str, level: str = "", stage: str = "", search: str = "", limit: int = 500) -> dict | None:
    p: dict[str, Any] = {"limit": limit}
    if level and level != "ALL":
        p["level"] = level
    if stage:
        p["stage"] = stage
    if search:
        p["search"] = search
    return _get(f"/logs/{sid}", params=p)


def refresh_all(sid: str) -> None:
    data = fetch_stages(sid)
    if not data:
        return
    st.session_state.stages = data.get("stages", [])
    st.session_state.pipeline_status = data.get("pipeline_status", "running")
    by_name = {s["stage"]: s for s in st.session_state.stages}

    vp = by_name.get("visual_planning", {})
    vpc = by_name.get("visual_plan_critique", {})
    if vp.get("status") in ("running", "completed") or vpc.get("status") in ("running", "completed"):
        sp = fetch_scene_progress(sid)
        if sp:
            st.session_state.scene_progress = sp

    ol = by_name.get("generate_outline", {})
    if ol.get("status") == "completed" and st.session_state.outline is None:
        od = fetch_outline(sid)
        if od and od.get("outline"):
            st.session_state.outline = od["outline"]
            st.session_state.outline_type = od.get("outline_type")

    if vpc.get("status") == "completed" and st.session_state.scenes is None:
        sd = fetch_scenes(sid)
        if sd and sd.get("scene_visual_plans"):
            st.session_state.scenes = sd["scene_visual_plans"]
            st.session_state.total_scenes = sd.get("total_scenes", len(sd["scene_visual_plans"]))

    rnd = by_name.get("scene_rendering", {})
    if rnd.get("status") in ("running", "completed"):
        rs = fetch_render_status(sid)
        if rs:
            st.session_state.render_status = rs

    asm = by_name.get("video_assembly", {})
    if asm.get("status") == "completed":
        summ = asm.get("output_summary", {})
        if summ.get("final_video_path"):
            st.session_state.final_video_path = summ["final_video_path"]


def _reset() -> None:
    for k in ["generate_error", "outline", "outline_type", "scenes", "total_scenes",
        "stages", "scene_progress", "render_status", "final_video_path"
        ]:
        st.session_state[k] = _D.get(k)
    st.session_state.pipeline_status = "queued"


# ── UI Helpers ────────────────────────────────────────────────────────────────

def status_ind(status: str) -> str:
    cls = STATUS_DOT_CLS.get(status.lower(), "pending")
    lbl = STATUS_LABEL.get(status.lower(), status.upper())
    return f'<span class="status-ind {cls}"><span class="dot {cls}"></span>{lbl}</span>'


def badge(status: str) -> str:
    cls = {
        "completed": "green", "running": "blue", "failed": "red",
        "queued": "amber", "pending": "gray", "skipped": "gray", "idle": "gray",
        }.get(status.lower(), "gray")
    return f'<span class="badge {cls}">{status.upper()}</span>'


def fmt_dur(ms: float | None) -> str:
    if ms is None:
        return "—"
    s = ms / 1000
    return f"{int(s // 60)}m {s % 60:.0f}s" if s >= 60 else f"{s:.1f}s"


def fmt_num(n: int | float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def metric_tile(value: str, label: str, color: str = "") -> str:
    return (
        f'<div class="metric-tile {color}">'
        f'<div class="m-val">{value}</div>'
        f'<div class="m-lbl">{label}</div>'
        f'</div>'
    )


def kv_pair(k: str, v: str) -> str:
    return (
        f'<div class="kv-item">'
        f'<div class="kv-k">{_html_mod.escape(k)}</div>'
        f'<div class="kv-v">{_html_mod.escape(str(v))}</div>'
        f'</div>'
    )


def prose_viewer(text: str) -> None:
    if not text:
        return
    safe = _html_mod.escape(str(text))
    st.markdown(f'<div class="prose-view">{safe}</div>', unsafe_allow_html=True)


def dl_json(data: Any, filename: str, key: str) -> None:
    raw = json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
    st.download_button(
        "Download JSON",
        data=raw,
        file_name=filename,
        mime="application/json",
        key=key,
        use_container_width=True,
        )


def counter_card(value: int | str, label: str, variant: str = "") -> str:
    return (
        f'<div class="counter-card {variant}">'
        f'<div class="c-val">{value}</div>'
        f'<div class="c-lbl">{label}</div>'
        f'</div>'
    )


# ── Pipeline Visualization ─────────────────────────────────────────────────────

def render_pipeline(stages: list[dict]) -> None:
    by = {s["stage"]: s for s in stages}
    items = []
    for i, (key, label) in enumerate(PIPELINE_STAGES):
        info = by.get(key, {})
        status = info.get("status", "pending")
        dur = (
            fmt_dur(info.get("duration_ms")) if status == "completed" else
            "running" if status == "running" else ""
        )
        icon = {"completed": "✓", "running": "↺", "failed": "✕", "pending": "○", "skipped": "–"}.get(status, "○")
        cls = STATUS_DOT_CLS.get(status, "pending")
        items.append(
            f'<div class="pipe-stage">'
            f'<div class="pipe-circle {cls}">{icon}</div>'
            f'<div class="pipe-lbl {cls}">{label}</div>'
            f'<div class="pipe-dur">{dur}</div>'
            f'</div>'
            )
        if i < len(PIPELINE_STAGES) - 1:
            cc = "done" if status == "completed" else ("active" if status == "running" else "none")
            items.append(f'<div class="pipe-conn {cc}"></div>')
    st.markdown('<div class="pipe-wrap">' + "".join(items) + "</div>", unsafe_allow_html=True)


def render_scene_timeline(scenes: list[dict]) -> None:
    dots = []
    for s in scenes:
        idx = s.get("scene_index", "?")
        status = s.get("status", "pending").lower()
        title = _html_mod.escape(s.get("title", f"Scene {idx}"))
        dots.append(
            f'<div class="scene-tl-dot {status}" title="Scene {idx}: {title}">{idx}</div>',
            )
    if dots:
        st.markdown('<div class="scene-tl">' + "".join(dots) + "</div>", unsafe_allow_html=True)


# ── Stage Inline Previews ─────────────────────────────────────────────────────

def _preview_validate_input(sid: str) -> None:
    data = fetch_artifact(sid, "refined_input")
    if not data:
        return
    approach = data.get("approach", "")
    refined = data.get("refined_requirement") or data.get("requirement", "")
    kv_items = []
    if approach:
        kv_items.append(kv_pair("Approach", approach))
    wf = data.get("workflow_id", "")
    if wf:
        kv_items.append(kv_pair("Workflow", wf[-14:]))
    if kv_items:
        st.markdown('<div class="kv-block">' + "".join(kv_items) + "</div>", unsafe_allow_html=True)
    if refined:
        st.markdown("**Refined Requirement**")
        prose_viewer(refined[:600])
    sp = data.get("system_prompt", "")
    if sp:
        with st.expander("System Prompt", expanded=False):
            st.code(sp[:2000], language="text")
    c1, _ = st.columns([1, 3])
    with c1:
        dl_json(data, "refined_input.json", f"dl_ri_{sid}")


def _preview_generate_outline(sid: str) -> None:
    data = fetch_artifact(sid, "outline")
    if not data:
        return
    outline_type = data.get("outline_type", "")
    outline_body = data.get("outline", data)
    if not isinstance(outline_body, dict):
        return
    meta = outline_body.get("meta", {})
    segments = outline_body.get("outline", [])
    kv_items = []
    if outline_type:
        kv_items.append(kv_pair("Approach", outline_type))
    if meta.get("topic"):
        kv_items.append(kv_pair("Topic", meta["topic"]))
    if meta.get("total_duration_seconds"):
        kv_items.append(kv_pair("Duration", f"{meta['total_duration_seconds']}s"))
    if meta.get("pace"):
        kv_items.append(kv_pair("Pace", meta["pace"]))
    if segments:
        kv_items.append(kv_pair("Segments", str(len(segments))))
    if kv_items:
        st.markdown('<div class="kv-block">' + "".join(kv_items) + "</div>", unsafe_allow_html=True)

    for seg in segments:
        if not isinstance(seg, dict):
            continue
        scene_id = seg.get("scene_id", "?")
        title = seg.get("title", f"Scene {scene_id}")
        seg_type = seg.get("segment_type", "")
        dur = seg.get("duration_seconds", 0)
        with st.expander(f"Scene {scene_id}: {title}  [{seg_type} · {dur}s]", expanded=False):
            talking = seg.get("talking_points", [])
            if talking:
                st.markdown("**Talking Points**")
                for pt in talking:
                    st.markdown(f"- {pt}")
            vp = seg.get("visual_plan", "")
            if vp:
                st.markdown("**Visual Plan**")
                prose_viewer(vp)
            narr = seg.get("narration_hint", "")
            if narr:
                st.markdown(f"**Narration Hint:** {narr}")
            ttn = seg.get("transition_to_next", "")
            if ttn:
                st.markdown(f"**Transition:** {ttn}")

    c1, _ = st.columns([1, 3])
    with c1:
        dl_json(data, "outline.json", f"dl_ol_{sid}")


def _preview_outline_critique(sid: str) -> None:
    meta = fetch_artifact(sid, "outline_critique")
    if meta:
        score = meta.get("score")
        approved = meta.get("approved")
        critique = meta.get("critique", "")
        improvements = meta.get("improvements", [])
        iters = meta.get("iterations", meta.get("total_iterations"))
        kv_items = []
        if score is not None:
            kv_items.append(kv_pair("Score", f"{score}/10"))
        if approved is not None:
            kv_items.append(kv_pair("Approved", "Yes" if approved else "No"))
        if iters is not None:
            kv_items.append(kv_pair("Iterations", str(iters)))
        if kv_items:
            st.markdown('<div class="kv-block">' + "".join(kv_items) + "</div>", unsafe_allow_html=True)
        if critique:
            st.markdown("**Critique**")
            prose_viewer(critique)
        if improvements:
            st.markdown("**Improvements Applied**")
            for imp in improvements:
                st.markdown(f"- {imp}")
    c1, _ = st.columns([1, 3])
    with c1:
        if meta:
            dl_json(meta, "outline_critique.json", f"dl_oc_{sid}")


def _preview_visual_planning(sid: str) -> None:
    data = fetch_artifact(sid, "visual_plans")
    if not data:
        return
    plans = data.get("scene_visual_plans", [])
    total = len(plans)
    failed = sum(1 for p in plans if p.get("error"))
    kv_items = [
        kv_pair("Total Scenes", str(total)),
        kv_pair("Succeeded", str(total - failed)),
        ]
    if failed:
        kv_items.append(kv_pair("Failed", str(failed)))
    st.markdown('<div class="kv-block">' + "".join(kv_items) + "</div>", unsafe_allow_html=True)

    for p in plans:
        idx = p.get("scene_index", "?")
        title = p.get("title", f"Scene {idx}")
        has_err = bool(p.get("error"))
        prefix = "Failed" if has_err else "Scene"
        model = (p.get("model_used") or "")[-25:]
        attempts = p.get("total_attempts", "?")
        with st.expander(f"{prefix} {idx}: {title}", expanded=False):
            if has_err:
                st.error(p["error"])
            else:
                kv2 = [kv_pair("Model", model), kv_pair("Attempts", str(attempts))]
                st.markdown('<div class="kv-block">' + "".join(kv2) + "</div>", unsafe_allow_html=True)
            plan = p.get("plan")
            if plan and isinstance(plan, dict):
                vp_text = plan.get("visual_plan", "")
                if vp_text:
                    st.markdown("**Visual Plan**")
                    prose_viewer(vp_text)
                for field in ["scene_type", "color_palette", "key_elements", "technical_notes"]:
                    val = plan.get(field)
                    if val:
                        if isinstance(val, list):
                            st.markdown(f"**{field.replace('_', ' ').title()}:** {', '.join(str(v) for v in val)}")
                        else:
                            st.markdown(f"**{field.replace('_', ' ').title()}:** {val}")
                with st.expander("Raw JSON", expanded=False):
                    raw = json.dumps(plan, indent=2)
                    st.code(raw[:3000] if len(raw) > 3000 else raw, language="json")
                c1, _ = st.columns([1, 3])
                with c1:
                    dl_json(plan, f"scene_{idx:03d}_visual_plan.json", f"dl_vp_{sid}_{idx}")
            elif plan:
                prose_viewer(str(plan)[:400])

    c1, _ = st.columns([1, 3])
    with c1:
        dl_json(data, "visual_plans.json", f"dl_vpa_{sid}")


def _preview_visual_plan_critique(sid: str) -> None:
    sp = fetch_scene_progress(sid)
    if not sp:
        st.caption("Critique data available after visual plan review completes.")
        return
    scenes = sp.get("scenes", [])
    if scenes:
        render_scene_timeline(scenes)
        done = sum(1 for s in scenes if s.get("status") == "completed")
        total = len(scenes)
        st.caption(f"{done}/{total} scenes reviewed")


def _preview_manim_code(sid: str) -> None:
    data = fetch_artifact(sid, "manim_codes")
    if not data:
        return
    codes = data.get("scene_manim_codes", [])
    ready = sum(1 for c in codes if c.get("status") == "READY")
    kv_items = [
        kv_pair("Total", str(len(codes))),
        kv_pair("Ready", str(ready)),
        kv_pair("Failed", str(len(codes) - ready)),
        ]
    st.markdown('<div class="kv-block">' + "".join(kv_items) + "</div>", unsafe_allow_html=True)

    for c in codes:
        idx = c.get("scene_index", "?")
        status = c.get("status", "?")
        title = c.get("title", f"Scene {idx}")
        prefix = "Ready" if status == "READY" else "Failed"
        with st.expander(f"{prefix} — Scene {idx}: {title}", expanded=False):
            if c.get("error"):
                st.error(c["error"])
            py = c.get("python_code", "")
            if py:
                st.code(py[:3500], language="python")
                if len(py) > 3500:
                    st.caption(f"Showing first 3500 chars of {len(py):,} total chars")
                c1, _ = st.columns([1, 3])
                with c1:
                    st.download_button(
                        f"scene_{idx:03d}.py",
                        data=py,
                        file_name=f"scene_{idx:03d}.py",
                        mime="text/x-python",
                        key=f"dl_py_{sid}_{idx}",
                        use_container_width=True,
                        )

    c1, _ = st.columns([1, 3])
    with c1:
        dl_json(data, "manim_codes.json", f"dl_mc_{sid}")


def _preview_scene_rendering(sid: str) -> None:
    rs = fetch_render_status(sid)
    if not rs:
        st.caption("Render status not yet available.")
        return
    rr = rs.get("scene_render_results", [])
    if not rr:
        return
    ready = sum(1 for r in rr if r.get("status") == "READY")
    failed = sum(1 for r in rr if r.get("status") == "FAILED")
    kv_items = [
        kv_pair("Total", str(len(rr))),
        kv_pair("Ready", str(ready)),
        kv_pair("Failed", str(failed)),
        ]
    st.markdown('<div class="kv-block">' + "".join(kv_items) + "</div>", unsafe_allow_html=True)
    scene_data = [
        {
            "scene_index": r.get("scene_index"),
            "title": r.get("title", ""),
            "status": r.get("status", "PENDING").lower(),
            }
        for r in rr
        ]
    render_scene_timeline(scene_data)
    failed_scenes = [r for r in rr if r.get("status") == "FAILED"]
    if failed_scenes:
        st.markdown("**Failed Scenes**")
        for r in failed_scenes:
            err = r.get("error", "Unknown error")
            st.error(f"Scene {r.get('scene_index')}: {err}")


def _preview_video_assembly(sid: str) -> None:
    video_url = f"{API_BASE}/video/{sid}"
    try:
        st.video(video_url)
        video_bytes = requests.get(video_url, timeout=60).content
        c1, _ = st.columns([1, 3])
        with c1:
            st.download_button(
                "Download MP4",
                data=video_bytes,
                file_name=f"{sid}_final.mp4",
                mime="video/mp4",
                key=f"dl_vid_{sid}",
                use_container_width=True,
                )
    except Exception:
        st.caption("Video file not yet available.")


_STAGE_PREVIEW = {
    "validate_input": _preview_validate_input,
    "generate_outline": _preview_generate_outline,
    "outline_critique": _preview_outline_critique,
    "visual_planning": _preview_visual_planning,
    "visual_plan_critique": _preview_visual_plan_critique,
    "manim_code_generation": _preview_manim_code,
    "scene_rendering": _preview_scene_rendering,
    "video_assembly": _preview_video_assembly,
    }


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _sidebar() -> None:
    with st.sidebar:
        st.markdown("""
        <div style="padding:20px 16px 12px;">
            <div style="font-family:'Poppins',sans-serif;font-size:1.15rem;font-weight:800;
                        color:#FFFFFF;letter-spacing:-0.3px;">Text-2-Shorts</div>
            <div style="font-size:0.68rem;color:#334155;margin-top:2px;font-family:'Inter',sans-serif;">
                AI Video Workflow Platform
            </div>
        </div>
        <hr style="border:none;border-top:1px solid #0F2745;margin:0 0 6px 0;">
        """, unsafe_allow_html=True
            )

        sessions = fetch_sessions()
        total_s = len(sessions)
        done_s = sum(1 for s in sessions if s.get("pipeline_status") == "completed")
        st.markdown(
            f'<div style="padding:0 16px 10px;font-size:0.7rem;font-family:Inter,sans-serif;">'
            f'<span style="background:#0F2745;color:#94A3B8;padding:2px 8px;border-radius:4px;margin-right:6px;">'
            f'{total_s} sessions</span>'
            f'<span style="background:#0F2745;color:#22C55E;padding:2px 8px;border-radius:4px;">'
            f'{done_s} done</span></div>',
            unsafe_allow_html=True,
            )

        for label in NAV_PAGES:
            active = st.session_state.page == label
            if st.button(label, key=f"nav_{label}", use_container_width=True,
                    type="primary" if active else "secondary",
                    ):
                st.session_state.page = label
                st.rerun()

        st.markdown('<hr style="border:none;border-top:1px solid #0F2745;margin:8px 0;">', unsafe_allow_html=True)

        sid = st.session_state.session_id
        if sid:
            ps = st.session_state.pipeline_status
            st.markdown(
                f'<div style="padding:8px 16px;">'
                f'<div style="font-size:0.6rem;color:#334155;margin-bottom:4px;text-transform:uppercase;'
                f'letter-spacing:0.5px;font-family:Inter,sans-serif;">ACTIVE SESSION</div>'
                f'<div style="font-family:monospace;font-size:0.7rem;color:#64748B;word-break:break-all;">'
                f'{sid}</div>'
                f'<div style="margin-top:5px;">{badge(ps)}</div>'
                f'</div>',
                unsafe_allow_html=True,
                )


# ── Right Panel ───────────────────────────────────────────────────────────────

def _right_panel() -> None:
    sid = st.session_state.session_id
    stages = st.session_state.stages or []
    ps = st.session_state.pipeline_status
    sp = st.session_state.scene_progress

    st.markdown('<div class="rp">', unsafe_allow_html=True)
    st.markdown('<div class="rp-hdr">Live Status</div>', unsafe_allow_html=True)

    if not sid:
        st.markdown(
            '<div style="font-size:0.78rem;color:#94A3B8;text-align:center;padding:14px 0;">No active session</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
        return

    rows = []

    def _row(lbl: str, val: str) -> str:
        return f'<div class="rp-row"><span class="rp-lbl">{lbl}</span><span class="rp-val">{val}</span></div>'

    rows.append(_row("Status", badge(ps)))

    if stages:
        done = sum(1 for s in stages if s.get("status") == "completed")
        total = len(stages)
        pct = int(done / total * 100) if total else 0
        rows.append(_row("Progress", f"{done}/{total} ({pct}%)"))

        cur = next((s["label"] for s in stages if s.get("status") == "running"), None)
        if cur:
            rows.append(_row("Stage", f'<span style="font-size:0.72rem;">{cur}</span>'))

        total_ms = sum(s.get("duration_ms") or 0 for s in stages)
        if total_ms:
            rows.append(_row("Runtime", fmt_dur(total_ms)))

    if sp and sp.get("total", 0) > 0:
        rows.append(_row("Scenes", f'{sp.get("completed", 0)}/{sp["total"]}'))

    st.markdown("".join(rows), unsafe_allow_html=True)
    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    if st.button("Refresh", key="rp_refresh", use_container_width=True):
        refresh_all(sid)
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: GENERATE
# ─────────────────────────────────────────────────────────────────────────────

def page_generate() -> None:
    st.markdown('<div class="section-hd">New Generation</div>', unsafe_allow_html=True)

    form_col, cfg_col = st.columns([7, 3])

    with form_col:
        requirement = st.text_area(
            "Video Requirement",
            placeholder=(
                "Describe the educational topic and learning goals.\n\n"
                "Example: Create a 90-second visual explainer on how gradient descent works "
                "for undergraduates who know basic calculus. Show the loss landscape and "
                "animate parameter updates step-by-step."
            ),
            height=240,
            key="req_input",
            )
        chars = len(requirement)
        words = len(requirement.split()) if requirement.strip() else 0
        st.markdown(
            f'<div style="text-align:right;font-size:0.7rem;color:#94A3B8;margin-top:2px;">'
            f'{chars} chars · {words} words</div>',
            unsafe_allow_html=True,
            )

    with cfg_col:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        approach = st.selectbox("Narrative Approach", APPROACHES, key="cfg_approach")
        st.markdown('</div>', unsafe_allow_html=True)

        gen_btn = st.button(
            "Generate Video",
            type="primary",
            key="btn_gen",
            disabled=not requirement.strip(),
            use_container_width=True,
            )

    if gen_btn:
        _reset()
        try:
            data = _post("/generate", json={"requirement": requirement.strip(), "approach": approach})
            st.session_state.session_id = data.get("session_id")
            st.session_state.pipeline_status = "queued"
            st.session_state.auto_poll = True
            st.session_state.page = "Pipeline"
            st.rerun()
        except Exception as exc:
            st.session_state.generate_error = str(exc)

    if st.session_state.generate_error:
        st.error(st.session_state.generate_error)

    if st.session_state.session_id:
        sid = st.session_state.session_id
        ps = st.session_state.pipeline_status
        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
        st.markdown(
            f'Active session: <span class="session-chip">{sid}</span> &nbsp; {badge(ps)}',
            unsafe_allow_html=True,
            )
        if ps in ("running", "queued"):
            st.info("Pipeline running — switch to Pipeline to monitor progress.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: SESSIONS
# ─────────────────────────────────────────────────────────────────────────────

def page_sessions() -> None:
    sessions = fetch_sessions()
    total = len(sessions)
    completed = sum(1 for s in sessions if s.get("pipeline_status") == "completed")
    failed = sum(1 for s in sessions if s.get("pipeline_status") == "failed")
    running = sum(1 for s in sessions if s.get("pipeline_status") == "running")

    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl, color in [
        (c1, total, "Total", "blue"),
        (c2, completed, "Completed", "green"),
        (c3, failed, "Failed", "red"),
        (c4, running, "Running", "amber"),
        ]:
        with col:
            st.markdown(metric_tile(str(val), lbl, color), unsafe_allow_html=True)

    st.markdown('<div class="section-hd">All Sessions</div>', unsafe_allow_html=True)

    if not sessions:
        st.info("No sessions yet. Generate your first video to get started.")
        return

    for s in reversed(sessions):
        sid = s.get("session_id", "?")
        approach_s = s.get("approach", "—")
        req_prev = s.get("requirement_preview", "")
        status = s.get("pipeline_status", "unknown")
        total_scn = s.get("total_scenes", 0)
        created_at = s.get("created_at", 0)
        completed_stages = s.get("completed_stages", [])

        ts = "—"
        if created_at:
            try:
                ts = _dt.datetime.fromtimestamp(created_at).strftime("%b %d %Y %H:%M")
            except Exception:
                pass

        with st.expander(f"{sid[-16:]}  ·  {approach_s}  ·  {ts}", expanded=False):
            ci, ca = st.columns([3, 1])
            with ci:
                st.markdown(
                    f'<div style="font-family:monospace;font-size:0.77rem;color:#2563EB;margin-bottom:6px;">{sid}</div>'
                    f'<div style="font-size:0.83rem;color:#374151;margin-bottom:6px;">'
                    f'{req_prev[:180]}{"…" if len(req_prev) > 180 else ""}</div>'
                    f'<div style="font-size:0.74rem;color:#64748B;">'
                    f'{status_ind(status)} &nbsp;·&nbsp; {len(completed_stages)}/8 stages &nbsp;·&nbsp; {total_scn} scenes</div>',
                    unsafe_allow_html=True,
                )
            with ca:
                if st.button("View", key=f"sv_{sid}", use_container_width=True):
                    st.session_state.session_id = sid
                    st.session_state.pipeline_status = status
                    for k in ["stages", "outline", "scenes", "scene_progress",
                        "render_status", "final_video_path",
                        ]:
                        st.session_state[k] = _D.get(k)
                    refresh_all(sid)
                    st.session_state.page = "Pipeline"
                    st.rerun()

                if status in ("failed", "running") and len(completed_stages) > 0:
                    if st.button("Resume", key=f"sr_{sid}", use_container_width=True):
                        try:
                            res = _post(f"/resume/{sid}")
                            if res:
                                st.session_state.session_id = sid
                                st.session_state.pipeline_status = "running"
                                st.session_state.auto_poll = True
                                for k in ["stages", "outline", "scenes", "scene_progress"]:
                                    st.session_state[k] = _D.get(k)
                                st.session_state.page = "Pipeline"
                                st.rerun()
                        except Exception as e:
                            st.error(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def page_pipeline() -> None:
    sid = st.session_state.session_id
    if not sid:
        st.info("No active session. Generate a video or select one from Sessions.")
        return

    ps = st.session_state.pipeline_status
    stages = st.session_state.stages or []
    by_name = {s["stage"]: s for s in stages}

    # ── Session card + controls ───────────────────────────────────────────────
    sc, ca = st.columns([3, 1])
    with sc:
        sp = st.session_state.scene_progress
        total_scn = st.session_state.total_scenes or (sp.get("total", 0) if sp else 0)
        done_stg = sum(1 for s in stages if s.get("status") == "completed")
        total_ms = sum(s.get("duration_ms") or 0 for s in stages)
        kv_html = (
                f'<div class="kv-block">'
                + kv_pair("Session", sid[-14:])
                + kv_pair("Stages", f"{done_stg}/{len(PIPELINE_STAGES)}")
                + (kv_pair("Scenes", str(total_scn)) if total_scn else "")
                + (kv_pair("Runtime", fmt_dur(total_ms)) if total_ms else "")
                + f'</div>'
        )
        st.markdown('<div class="card">' + kv_html + badge(ps) + '</div>', unsafe_allow_html=True)

    with ca:
        if st.button("Refresh", key="pp_refresh", use_container_width=True):
            refresh_all(sid)
            st.rerun()
        if ps in ("failed", "running"):
            if st.button("Resume", key="pp_resume", use_container_width=True):
                try:
                    _post(f"/resume/{sid}")
                    st.session_state.auto_poll = True
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    # ── Status counters dashboard ─────────────────────────────────────────────
    if stages:
        n_success = sum(1 for s in stages if s.get("status") == "completed")
        n_failed = sum(1 for s in stages if s.get("status") == "failed")
        n_running = sum(1 for s in stages if s.get("status") == "running")
        n_pending = sum(1 for s in stages if s.get("status") == "pending")
        n_skipped = sum(1 for s in stages if s.get("status") == "skipped")

        sp2 = st.session_state.scene_progress
        scene_done = sp2.get("completed", 0) if sp2 else 0
        scene_total = sp2.get("total", 0) if sp2 else 0
        scene_fail = sp2.get("failed", 0) if sp2 else 0

        cards = (
                counter_card(n_success, "Success", "success") +
                counter_card(n_failed, "Failed", "failed") +
                counter_card(n_running, "Running", "running") +
                counter_card(n_pending, "Pending", "pending") +
                (counter_card(n_skipped, "Skipped", "skipped") if n_skipped else "") +
                (counter_card(f"{scene_done}/{scene_total}", "Scenes", "success") if scene_total else "")
        )
        st.markdown('<div class="counter-row">' + cards + '</div>', unsafe_allow_html=True)

    # ── Pipeline visualization ────────────────────────────────────────────────
    st.markdown('<div class="section-hd">Pipeline Stages</div>', unsafe_allow_html=True)
    display_stages = stages or [
        {"stage": k, "label": l, "status": "pending", "duration_ms": None}
        for k, l in PIPELINE_STAGES
        ]
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_pipeline(display_stages)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Stage details with inline artifact previews ───────────────────────────
    active_stages = [s for s in stages if s.get("status") in ("completed", "failed", "running")]
    if active_stages:
        st.markdown('<div class="section-hd">Stage Details</div>', unsafe_allow_html=True)
        for s in active_stages:
            stage_key = s["stage"]
            label = s["label"]
            status = s.get("status", "pending")
            dur_str = fmt_dur(s.get("duration_ms"))
            err = s.get("error")

            icon = "Completed" if status == "completed" else ("Running" if status == "running" else "Failed")
            header = f"{icon} — {label}  [{dur_str}]"

            with st.expander(header, expanded=False):
                # Status indicator row
                summ = s.get("output_summary", {})
                kv_row = [status_ind(status)]
                if summ:
                    for k, v in summ.items():
                        kv_row.append(kv_pair(k.replace("_", " ").title(), str(v)[:40]))
                if kv_row[1:]:
                    st.markdown(
                        '<div class="kv-block">' + "".join(kv_row[1:]) + '</div>',
                        unsafe_allow_html=True,
                        )
                st.markdown(kv_row[0], unsafe_allow_html=True)

                if err:
                    st.error(f"Error: {err}")

                # Stage-specific preview
                preview_fn = _STAGE_PREVIEW.get(stage_key)
                if preview_fn and status in ("completed", "running"):
                    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
                    try:
                        preview_fn(sid)
                    except Exception:
                        pass

    # ── Scene progress (visual planning / critique) ───────────────────────────
    vp_status = by_name.get("visual_planning", {}).get("status")
    vpc_status = by_name.get("visual_plan_critique", {}).get("status")
    sp_data = st.session_state.scene_progress
    if (vp_status in ("running", "completed") or vpc_status in ("running", "completed")) and sp_data and sp_data.get(
            "total",
            0,
            ) > 0:
        active_stage_label = "Plan Review" if vpc_status in ("running", "completed") else "Visual Planning"
        st.markdown(f'<div class="section-hd">Scene Progress — {active_stage_label}</div>', unsafe_allow_html=True)
        tot = sp_data["total"]
        done = sp_data.get("completed", 0)
        fail = sp_data.get("failed", 0)
        st.markdown(
            f'<div class="card">'
            f'<div style="margin-bottom:8px;font-size:0.82rem;">'
            f'<strong>{done}/{tot}</strong> scenes'
            + (f' &nbsp;·&nbsp; <span style="color:#EF4444;">{fail} failed</span>' if fail else " &nbsp;·&nbsp; all ok")
            + f'</div>',
            unsafe_allow_html=True,
            )
        st.progress(done / tot if tot else 0)
        render_scene_timeline(sp_data.get("scenes", []))
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Render progress ───────────────────────────────────────────────────────
    rs = st.session_state.render_status
    rnd_status = by_name.get("scene_rendering", {}).get("status")
    if rnd_status in ("running", "completed") and rs:
        rr = rs.get("scene_render_results", [])
        if rr:
            st.markdown('<div class="section-hd">Scene Progress — Rendering</div>', unsafe_allow_html=True)
            ready = sum(1 for r in rr if r.get("status") == "READY")
            fail_r = sum(1 for r in rr if r.get("status") == "FAILED")
            scene_data = [
                {"scene_index": r.get("scene_index"), "title": r.get("title", ""),
                    "status": r.get("status", "PENDING").lower()
                    }
                for r in rr
                ]
            st.markdown(
                f'<div class="card">'
                f'<div style="margin-bottom:8px;font-size:0.82rem;">'
                f'<strong>{ready}</strong> ready &nbsp;·&nbsp; <strong>{fail_r}</strong> failed &nbsp;·&nbsp; <strong>{len(rr)}</strong> total'
                f'</div>',
                unsafe_allow_html=True,
                )
            render_scene_timeline(scene_data)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Final video ───────────────────────────────────────────────────────────
    asm_done = by_name.get("video_assembly", {}).get("status") == "completed"
    if asm_done:
        st.markdown('<div class="section-hd">Final Video</div>', unsafe_allow_html=True)
        _preview_video_assembly(sid)

    # ── Status banner ─────────────────────────────────────────────────────────
    if ps == "completed":
        st.success("Pipeline completed successfully.")
    elif ps == "failed":
        err_msg = next((s.get("error") for s in stages if s.get("status") == "failed"), "An error occurred.")
        st.error(f"Pipeline failed: {err_msg}")
    elif ps in ("running", "queued"):
        st.info(f"Pipeline {ps}…")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: LOGS
# ─────────────────────────────────────────────────────────────────────────────

def page_logs() -> None:
    sid = st.session_state.session_id
    if not sid:
        st.info("No active session. Select one from Sessions to view logs.")
        return

    c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1])
    with c1:
        search = st.text_input("Search", placeholder="Event, stage, node, message…", key="ls_search")
    with c2:
        level_f = st.selectbox("Level", ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], key="ls_level")
    with c3:
        stage_f = st.text_input("Stage", placeholder="e.g. visual_planning", key="ls_stage")
    with c4:
        limit_f = st.selectbox("Limit", [100, 250, 500, 1000], index=1, key="ls_limit")

    logs_data = fetch_logs(sid, level=level_f, stage=stage_f or "", search=search or "", limit=limit_f)
    if logs_data is None:
        st.warning("Could not fetch logs. Is the API running?")
        return

    entries = logs_data.get("entries", [])
    total = logs_data.get("total", 0)

    counts: dict[str, int] = {}
    for e in entries:
        lv = e.get("level", "INFO").upper()
        counts[lv] = counts.get(lv, 0) + 1

    m1, m2, m3, m4, m5 = st.columns(5)
    for col, val, lbl, color in [
        (m1, len(entries), "Shown", "blue"),
        (m2, counts.get("INFO", 0), "Info", "green"),
        (m3, counts.get("WARNING", 0), "Warnings", "amber"),
        (m4, counts.get("ERROR", 0) + counts.get("CRITICAL", 0), "Errors", "red"),
        (m5, total, "Total", ""),
        ]:
        with col:
            st.markdown(metric_tile(str(val), lbl, color), unsafe_allow_html=True)

    if logs_data.get("has_more"):
        st.info(f"Showing {len(entries)} of {total}. Increase limit for more.")

    if not entries:
        st.info("No log entries match the current filters.")
        return

    rows_html = []
    for entry in entries:
        ts = entry.get("timestamp", "")
        if ts:
            try:
                dt_obj = _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts = dt_obj.strftime("%H:%M:%S.%f")[:-3]
            except Exception:
                ts = ts[11:22] if len(ts) > 11 else ts

        level = entry.get("level", "INFO").upper()
        stage = _html_mod.escape((entry.get("stage") or "")[:22])
        node = _html_mod.escape((entry.get("node") or "")[:22])
        event = entry.get("event") or ""
        details = entry.get("details") or {}
        dur_ms = entry.get("duration_ms")
        dur_str = f"{dur_ms:.0f}ms" if dur_ms else "—"

        msg_parts = [f"[{_html_mod.escape(event)}]"] if event else []
        if isinstance(details, dict):
            for k in ["message", "step", "stage_name", "error"]:
                if k in details:
                    msg_parts.append(_html_mod.escape(str(details[k])[:120]))
                    break
        msg = " ".join(msg_parts)[:220] if msg_parts else _html_mod.escape(str(details)[:120])

        ll = level.lower()
        rows_html.append(
            f'<div class="log-row {ll}">'
            f'<div style="font-family:monospace;color:#64748B;white-space:nowrap;font-size:0.74rem;">{ts}</div>'
            f'<div><span class="lvl {ll}">{level}</span></div>'
            f'<div style="color:#64748B;font-size:0.72rem;word-break:break-word;">{stage}</div>'
            f'<div style="color:#94A3B8;font-size:0.72rem;word-break:break-word;">{node}</div>'
            f'<div style="color:#0F172A;word-break:break-word;">{msg}</div>'
            f'<div style="font-family:monospace;color:#94A3B8;white-space:nowrap;font-size:0.72rem;">{dur_str}</div>'
            f'</div>'
            )

    hdr = (
        '<div class="log-hdr">'
        '<div>Time</div><div>Level</div><div>Stage</div>'
        '<div>Node</div><div>Message</div><div>Duration</div>'
        '</div>'
    )
    st.markdown(
        '<div class="log-wrap"><div class="log-body">' + hdr + "".join(rows_html) + '</div></div>',
        unsafe_allow_html=True,
        )

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
    c1, _ = st.columns([1, 4])
    with c1:
        log_text = "\n".join(json.dumps(e) for e in entries)
        st.download_button(
            "Download Logs (JSONL)",
            data=log_text,
            file_name=f"{sid}_logs.jsonl",
            mime="application/x-ndjson",
            key="dl_logs_btn",
            use_container_width=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

_sidebar()

sid = st.session_state.session_id
ps = st.session_state.pipeline_status

# Header bar
dot_color = (
    "#3B82F6" if ps in ("running", "queued") else
    "#22C55E" if ps == "completed" else
    "#EF4444" if ps == "failed" else "#9CA3AF"
)
st.markdown(
    f'<div class="app-header">'
    f'<div style="display:flex;align-items:center;">'
    f'<span class="app-logo">Text-2-Shorts</span>'
    f'<span class="app-badge">v{VERSION}</span>'
    f'</div>'
    + (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="width:8px;height:8px;border-radius:50%;background:{dot_color};display:inline-block;"></span>'
        f'<span class="session-chip">{sid}</span>'
        f'</div>'
        if sid else
        '<div style="font-size:0.82rem;color:#94A3B8;font-family:Inter,sans-serif;">No active session</div>'
    )
    + '</div>',
    unsafe_allow_html=True,
    )

_, main_col, right_col = st.columns([0.02, 4, 1])

with right_col:
    st.markdown('<div style="padding-top:14px;">', unsafe_allow_html=True)
    _right_panel()
    st.markdown('</div>', unsafe_allow_html=True)

with main_col:
    st.markdown('<div class="content-pad">', unsafe_allow_html=True)
    page = st.session_state.page
    if page == "Generate":
        page_generate()
    elif page == "Sessions":
        page_sessions()
    elif page == "Pipeline":
        page_pipeline()
    elif page == "Logs":
        page_logs()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Auto-polling ──────────────────────────────────────────────────────────────

_TERMINAL = {"completed", "failed"}

if (
        st.session_state.auto_poll
        and st.session_state.session_id
        and st.session_state.pipeline_status not in _TERMINAL
):
    time.sleep(POLL_INTERVAL_S)
    refresh_all(st.session_state.session_id)
    if st.session_state.pipeline_status in _TERMINAL:
        st.session_state.auto_poll = False
    st.rerun()
