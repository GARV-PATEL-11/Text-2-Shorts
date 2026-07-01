"""Text-2-Shorts — AI Workflow Dashboard v2.0"""
from __future__ import annotations

import datetime as _dt
import json
import time
from typing import Any

import requests

import streamlit as st


# ── Constants ─────────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000"
POLL_INTERVAL_S = 3.0
VERSION = "2.0"

PIPELINE_STAGES: list[tuple[str, str]] = [
    ("validate_input", "Validate Input"),
    ("generate_outline", "Gen Outline"),
    ("map_outline", "Map Scenes"),
    ("visual_planning", "Visual Plans"),
    ("manim_code_generation", "Gen Code"),
    ("scene_rendering", "Render"),
    ("video_assembly", "Assemble"),
    ]

APPROACHES = [
    "Classic Linear Narrative",
    "Conceptual Zoom",
    "Problem-Solution Arc",
    ]

NAV_PAGES = [
    ("Generate", "🎬"),
    ("Sessions", "📋"),
    ("Pipeline", "⚡"),
    ("Artifacts", "📦"),
    ("Logs", "📜"),
    ("Analytics", "📊"),
    ("Downloads", "⬇"),
    ]

STATUS_ICONS = {
    "completed": "✓", "running": "↺", "failed": "✕",
    "pending": "○", "queued": "○", "skipped": "–",
    }

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Text-2-Shorts | AI Workflow Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
    )

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Reset ── */
#MainMenu, footer { visibility: hidden; }
.stApp > header { display: none !important; }
.stApp { background: #F8FAFC !important; }
.main .block-container {
    padding: 0 0 2rem 0 !important;
    max-width: 100% !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0F172A !important;
    border-right: 1px solid #1E293B !important;
}
[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; }
[data-testid="stSidebar"] button {
    background: transparent !important;
    border: none !important;
    color: #94A3B8 !important;
    text-align: left !important;
    padding: 8px 12px !important;
    font-size: 0.85rem !important;
    border-radius: 6px !important;
    margin: 1px 6px !important;
    justify-content: flex-start !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(255,255,255,0.08) !important;
    color: #E2E8F0 !important;
}
[data-testid="stSidebar"] button[kind="primary"] {
    background: rgba(37,99,235,0.25) !important;
    color: #FFFFFF !important;
    border-left: 3px solid #2563EB !important;
    border-radius: 0 6px 6px 0 !important;
}

/* ── App header bar ── */
.app-header {
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    padding: 0 28px;
    height: 62px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0;
}
.app-logo {
    font-size: 1.25rem;
    font-weight: 800;
    color: #0F172A !important;
    letter-spacing: -0.5px;
}
.app-version {
    font-size: 0.7rem;
    color: #94A3B8 !important;
    background: #F1F5F9;
    border: 1px solid #E2E8F0;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 10px;
}
.session-chip {
    font-family: 'Courier New', monospace;
    font-size: 0.78rem;
    color: #2563EB !important;
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    padding: 4px 12px;
    border-radius: 6px;
}
.pulse { animation: pulse 2s infinite; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.35; } }

/* ── Cards ── */
.card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.card-hover:hover {
    border-color: #BFDBFE;
    box-shadow: 0 4px 14px rgba(0,0,0,0.07);
    transition: all 0.15s;
}
.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #0F172A !important;
    margin: 20px 0 10px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #E2E8F0;
}

/* ── Status badges ── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
.badge-green  { background: #F0FDF4; color: #16A34A !important; border: 1px solid #BBF7D0; }
.badge-blue   { background: #EFF6FF; color: #1D4ED8 !important; border: 1px solid #BFDBFE; }
.badge-red    { background: #FEF2F2; color: #DC2626 !important; border: 1px solid #FECACA; }
.badge-amber  { background: #FFFBEB; color: #D97706 !important; border: 1px solid #FDE68A; }
.badge-gray   { background: #F8FAFC; color: #64748B !important; border: 1px solid #E2E8F0; }

/* ── Metric tiles ── */
.metric-tile {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 16px 18px;
    text-align: center;
}
.metric-val {
    font-size: 1.65rem;
    font-weight: 800;
    color: #0F172A !important;
    line-height: 1;
    margin-bottom: 5px;
}
.metric-lbl {
    font-size: 0.7rem;
    color: #64748B !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.metric-tile.blue  { border-top: 3px solid #2563EB; }
.metric-tile.green { border-top: 3px solid #22C55E; }
.metric-tile.red   { border-top: 3px solid #EF4444; }
.metric-tile.amber { border-top: 3px solid #F59E0B; }

/* ── Pipeline stages ── */
.pipe-row {
    display: flex;
    align-items: flex-start;
    padding: 14px 0 6px;
    overflow-x: auto;
    gap: 0;
}
.pipe-stage {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 100px;
    flex: 0 0 auto;
}
.pipe-icon {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    font-weight: 700;
    border: 2px solid;
}
.pipe-icon.completed { background:#F0FDF4; border-color:#22C55E; color:#16A34A !important; }
.pipe-icon.running   { background:#EFF6FF; border-color:#2563EB; color:#2563EB !important; }
.pipe-icon.failed    { background:#FEF2F2; border-color:#EF4444; color:#DC2626 !important; }
.pipe-icon.pending   { background:#F8FAFC; border-color:#CBD5E1; color:#94A3B8 !important; }
.pipe-icon.skipped   { background:#F8FAFC; border-color:#CBD5E1; color:#94A3B8 !important; }
.pipe-icon.running .icon-char { animation: spin 1.2s linear infinite; display:inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
.pipe-lbl {
    font-size: 0.68rem;
    font-weight: 600;
    text-align: center;
    margin-top: 5px;
    line-height: 1.3;
    max-width: 90px;
}
.pipe-lbl.completed { color: #16A34A !important; }
.pipe-lbl.running   { color: #1D4ED8 !important; }
.pipe-lbl.failed    { color: #DC2626 !important; }
.pipe-lbl.pending,
.pipe-lbl.skipped   { color: #94A3B8 !important; }
.pipe-dur {
    font-size: 0.6rem;
    color: #94A3B8 !important;
    margin-top: 3px;
}
.pipe-conn {
    flex: 1;
    height: 2px;
    margin-top: 18px;
    min-width: 16px;
}
.pipe-conn.done     { background: #22C55E; }
.pipe-conn.active   { background: linear-gradient(90deg,#22C55E 0%,#2563EB 100%); }
.pipe-conn.inactive { background: #E2E8F0; }

/* ── Scene grid ── */
.scene-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    padding: 8px 0;
}
.scene-cell {
    width: 30px;
    height: 30px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.68rem;
    font-weight: 700;
    border: 1px solid;
    cursor: default;
    transition: transform 0.1s;
}
.scene-cell:hover { transform: scale(1.15); }
.scene-cell.completed  { background:#F0FDF4; border-color:#BBF7D0; color:#16A34A !important; }
.scene-cell.running    { background:#EFF6FF; border-color:#BFDBFE; color:#2563EB !important; }
.scene-cell.failed     { background:#FEF2F2; border-color:#FECACA; color:#DC2626 !important; }
.scene-cell.pending    { background:#F8FAFC; border-color:#E2E8F0; color:#94A3B8 !important; }
.scene-cell.ready      { background:#F0FDF4; border-color:#BBF7D0; color:#16A34A !important; }
.scene-cell.generating { background:#F5F3FF; border-color:#DDD6FE; color:#7C3AED !important; }
.scene-cell.rendering  { background:#FFF7ED; border-color:#FED7AA; color:#C2410C !important; }
.scene-cell.debugging  { background:#FFFBEB; border-color:#FDE68A; color:#D97706 !important; }

/* ── Log table ── */
.log-container {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    max-height: 560px;
    overflow-y: auto;
    font-size: 0.78rem;
}
.log-head {
    display: grid;
    grid-template-columns: 90px 70px 120px 120px 1fr 70px;
    gap: 6px;
    padding: 8px 12px;
    background: #F8FAFC;
    border-bottom: 2px solid #E2E8F0;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #64748B !important;
    position: sticky;
    top: 0;
}
.log-row {
    display: grid;
    grid-template-columns: 90px 70px 120px 120px 1fr 70px;
    gap: 6px;
    padding: 7px 12px;
    border-bottom: 1px solid #F1F5F9;
    align-items: start;
    border-left: 3px solid transparent;
}
.log-row:hover { background: #F8FAFC; }
.log-row.debug    { border-left-color: #94A3B8; }
.log-row.info     { border-left-color: #22C55E; }
.log-row.warning  { border-left-color: #F59E0B; }
.log-row.error    { border-left-color: #EF4444; }
.log-row.critical { border-left-color: #8B5CF6; }
.lvl {
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    white-space: nowrap;
}
.lvl.debug    { background:#F1F5F9; color:#64748B !important; }
.lvl.info     { background:#F0FDF4; color:#16A34A !important; }
.lvl.warning  { background:#FFFBEB; color:#D97706 !important; }
.lvl.error    { background:#FEF2F2; color:#DC2626 !important; }
.lvl.critical { background:#F5F3FF; color:#7C3AED !important; }

/* ── Right panel ── */
.rp {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 14px;
}
.rp-title {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #64748B !important;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid #E2E8F0;
}
.rp-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid #F1F5F9;
    font-size: 0.8rem;
}
.rp-lbl { color: #64748B !important; }
.rp-val { font-weight: 700; color: #0F172A !important; }

/* ── Forms ── */
.stTextArea textarea {
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
    color: #0F172A !important;
    min-height: 250px !important;
}
.stTextArea textarea:focus {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}
.stSelectbox > div > div,
.stTextInput > div > div > input {
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
}

/* ── Generate button ── */
.stButton > button[kind="primary"]:not([data-testid*="sidebar"]) {
    background: #1E3A8A !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    height: 48px !important;
    letter-spacing: 0.2px;
    transition: all 0.15s !important;
}
.stButton > button[kind="primary"]:not([data-testid*="sidebar"]):hover {
    background: #2563EB !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(37,99,235,0.3) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 1px solid #E2E8F0;
    gap: 0;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    padding: 9px 16px;
    font-size: 0.82rem;
    font-weight: 600;
    color: #64748B !important;
    border-radius: 0;
}
.stTabs [aria-selected="true"] {
    color: #1E3A8A !important;
    border-bottom: 2px solid #2563EB !important;
    background: transparent;
}

/* ── Typography ── */
h1,h2,h3,h4 { color: #0F172A !important; }
p, li        { color: #374151 !important; }
label        { color: #374151 !important; font-size: 0.85rem !important; }
.stTextArea label, .stSelectbox label, .stSlider label, .stTextInput label {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: #374151 !important;
    margin-bottom: 3px !important;
}
details summary { font-size: 0.88rem !important; font-weight: 600 !important; }

/* ── Content padding ── */
.content-pad { padding: 20px 28px 0 28px; }

/* ── Download row ── */
.dl-row {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-bottom: 7px;
    gap: 12px;
}
.dl-name { font-weight: 600; font-size: 0.85rem; color: #0F172A !important; flex: 1; }
.dl-meta { font-size: 0.72rem; color: #94A3B8 !important; min-width: 80px; }
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
    "dev_mode": False,
    "analytics": {},
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


def fetch_analytics(sid: str) -> dict | None:
    return _get(f"/logs/{sid}/analytics")


def refresh_all(sid: str) -> None:
    data = fetch_stages(sid)
    if not data:
        return
    st.session_state.stages = data.get("stages", [])
    st.session_state.pipeline_status = data.get("pipeline_status", "running")
    by_name = {s["stage"]: s for s in st.session_state.stages}

    vp = by_name.get("visual_planning", {})
    if vp.get("status") in ("running", "completed"):
        sp = fetch_scene_progress(sid)
        if sp:
            st.session_state.scene_progress = sp

    ol = by_name.get("generate_outline", {})
    if ol.get("status") == "completed" and st.session_state.outline is None:
        od = fetch_outline(sid)
        if od and od.get("outline"):
            st.session_state.outline = od["outline"]
            st.session_state.outline_type = od.get("outline_type")

    if vp.get("status") == "completed" and st.session_state.scenes is None:
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
        "stages", "scene_progress", "render_status", "final_video_path", "analytics",
        ]:
        st.session_state[k] = _D.get(k)
    st.session_state.pipeline_status = "queued"


# ── UI Helpers ────────────────────────────────────────────────────────────────

def badge(status: str) -> str:
    cls = {
        "completed": "badge-green", "running": "badge-blue", "failed": "badge-red",
        "queued": "badge-amber", "pending": "badge-gray", "skipped": "badge-gray",
        "idle": "badge-gray",
        }.get(status.lower(), "badge-gray")
    icon = STATUS_ICONS.get(status.lower(), "○")
    return f'<span class="badge {cls}">{icon} {status.upper()}</span>'


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
        f'<div class="metric-val">{value}</div>'
        f'<div class="metric-lbl">{label}</div>'
        f'</div>'
    )


def json_card(data: Any, key_suffix: str = "", max_chars: int = 12000) -> None:
    raw = json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
    trunc = len(raw) > max_chars
    st.code(raw[:max_chars] if trunc else raw, language="json")
    if trunc:
        st.caption(f"Showing {max_chars // 1024} KB of {len(raw) // 1024} KB")
    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        safe = json.dumps(raw)
        st.html(
            f"""<button onclick="navigator.clipboard.writeText({safe}).then(()=>{{
                this.textContent='✓ Copied';
                setTimeout(()=>this.textContent='Copy',2000);
            }})"
            style="cursor:pointer;padding:5px 14px;border:1px solid #BFDBFE;border-radius:6px;
                   background:#EFF6FF;color:#1D4ED8;font-size:11px;font-family:system-ui;
                   font-weight:600;white-space:nowrap;">Copy</button>""",
            )
    with c2:
        st.download_button(
            "⬇ Save",
            data=raw,
            file_name=f"artifact{key_suffix}.json",
            mime="application/json",
            key=f"jdl{key_suffix}_{abs(hash(raw[:80]))}",
            use_container_width=True,
            )


def render_pipeline(stages: list[dict]) -> None:
    by = {s["stage"]: s for s in stages}
    items = []
    for i, (key, label) in enumerate(PIPELINE_STAGES):
        info = by.get(key, {})
        status = info.get("status", "pending")
        dur = fmt_dur(info.get("duration_ms")) if info.get("status") == "completed" else (
            "running…" if info.get("status") == "running" else ""
        )
        icon = STATUS_ICONS.get(status, "○")
        spin = " pulse" if status == "running" else ""
        items.append(
            f'<div class="pipe-stage">'
            f'<div class="pipe-icon {status}"><span class="{spin}">{icon}</span></div>'
            f'<div class="pipe-lbl {status}">{label}</div>'
            f'<div class="pipe-dur">{dur}</div>'
            f'</div>',
            )
        if i < len(PIPELINE_STAGES) - 1:
            cc = "done" if status == "completed" else ("active" if status == "running" else "inactive")
            items.append(f'<div class="pipe-conn {cc}"></div>')
    pipe_html = '<div class="pipe-row">' + "".join(items) + "</div>"
    st.markdown(pipe_html, unsafe_allow_html=True)


def render_scenes(scenes: list[dict]) -> None:
    cells = []
    for s in scenes:
        idx = s.get("scene_index", "?")
        status = s.get("status", "pending").lower()
        title = s.get("title", f"Scene {idx}")
        cells.append(
            f'<div class="scene-cell {status}" title="{idx}: {title}">{idx}</div>',
            )
    st.markdown('<div class="scene-grid">' + "".join(cells) + "</div>", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _sidebar() -> None:
    with st.sidebar:
        st.markdown("""
        <div style="padding:18px 14px 14px;">
            <div style="font-size:1.2rem;font-weight:800;color:#FFFFFF;letter-spacing:-0.5px;">
                🎬 Text-2-Shorts
            </div>
            <div style="font-size:0.7rem;color:#475569;margin-top:3px;">AI Workflow Dashboard</div>
        </div>
        <hr style="border:none;border-top:1px solid #1E293B;margin:0 0 6px 0;">
        """, unsafe_allow_html=True,
            )

        sessions = fetch_sessions()
        total_s = len(sessions)
        done_s = sum(1 for s in sessions if s.get("pipeline_status") == "completed")
        st.markdown(
            f'<div style="padding:2px 14px 10px;font-size:0.72rem;color:#475569;">'
            f'<span style="background:#1E293B;color:#94A3B8;padding:2px 8px;border-radius:4px;margin-right:6px;">'
            f'{total_s} sessions</span>'
            f'<span style="background:#1E293B;color:#22C55E;padding:2px 8px;border-radius:4px;">'
            f'{done_s} completed</span></div>',
            unsafe_allow_html=True,
            )

        for label, icon in NAV_PAGES:
            active = st.session_state.page == label
            if st.button(
                    f"{icon}  {label}",
                    key=f"nav_{label}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                    ):
                st.session_state.page = label
                st.rerun()

        st.markdown('<hr style="border:none;border-top:1px solid #1E293B;margin:10px 0 6px 0;">',
            unsafe_allow_html=True,
            )

        # Recent sessions
        recent = [s for s in reversed(sessions[-6:])]
        if recent:
            st.markdown(
                '<div style="padding:4px 14px 6px;font-size:0.66rem;font-weight:700;'
                'text-transform:uppercase;letter-spacing:0.5px;color:#334155;">RECENT</div>',
                unsafe_allow_html=True,
                )
            for s in recent:
                sid = s.get("session_id", "")
                ps = s.get("pipeline_status", "?")
                dot = "🟢" if ps == "completed" else "🔵" if ps == "running" else "🔴" if ps == "failed" else "⚪"
                short = sid[-10:] if len(sid) > 10 else sid
                if st.button(
                        f"{dot} {short}",
                        key=f"rec_{sid}",
                        use_container_width=True,
                        help=f"{sid} — {ps}",
                        ):
                    st.session_state.session_id = sid
                    st.session_state.pipeline_status = ps
                    for k in ["stages", "outline", "scenes", "scene_progress", "analytics"]:
                        st.session_state[k] = _D.get(k)
                    refresh_all(sid)
                    st.session_state.page = "Pipeline"
                    st.rerun()

        st.markdown('<hr style="border:none;border-top:1px solid #1E293B;margin:8px 0 6px 0;">', unsafe_allow_html=True)

        dev = st.toggle("Developer Mode", value=st.session_state.dev_mode, key="dev_toggle")
        if dev != st.session_state.dev_mode:
            st.session_state.dev_mode = dev

        if st.session_state.session_id:
            ps = st.session_state.pipeline_status
            st.markdown(
                f'<div style="padding:10px 14px 6px;">'
                f'<div style="font-size:0.62rem;color:#475569;margin-bottom:4px;">ACTIVE SESSION</div>'
                f'<div style="font-family:monospace;font-size:0.72rem;color:#94A3B8;word-break:break-all;">'
                f'{st.session_state.session_id}</div>'
                f'<div style="margin-top:5px;">{badge(ps)}</div>'
                f'</div>',
                unsafe_allow_html=True,
                )


# ── Right Analytics Panel ─────────────────────────────────────────────────────

def _right_panel() -> None:
    sid = st.session_state.session_id
    stages = st.session_state.stages or []
    ps = st.session_state.pipeline_status
    sp = st.session_state.scene_progress
    ana = st.session_state.analytics

    st.markdown('<div class="rp">', unsafe_allow_html=True)
    st.markdown('<div class="rp-title">Live Metrics</div>', unsafe_allow_html=True)

    if not sid:
        st.markdown(
            '<div style="font-size:0.78rem;color:#94A3B8;text-align:center;padding:16px 0;">No active session</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
        return

    rows = []

    def _row(label: str, value: str) -> str:
        return f'<div class="rp-row"><span class="rp-lbl">{label}</span><span class="rp-val">{value}</span></div>'

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

    if ana:
        tok = ana.get("total_tokens", 0)
        if tok:
            rows.append(_row("Tokens", fmt_num(tok)))
        calls = ana.get("total_llm_calls", 0)
        if calls:
            rows.append(_row("LLM Calls", str(calls)))
        errs = ana.get("total_errors", 0)
        if errs:
            rows.append(_row("Errors", f'<span style="color:#DC2626;">{errs}</span>'))

    st.markdown("".join(rows), unsafe_allow_html=True)

    st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
    if st.button("↻ Refresh", key="rp_refresh", use_container_width=True):
        refresh_all(sid)
        ad = fetch_analytics(sid)
        if ad:
            st.session_state.analytics = ad.get("analytics", {})
        st.rerun()

    if st.session_state.dev_mode:
        st.markdown(
            '<div style="margin-top:10px;font-size:0.65rem;color:#475569;border-top:1px solid #E2E8F0;padding-top:8px;">'
            'DEV MODE ON</div>',
            unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: GENERATE
# ─────────────────────────────────────────────────────────────────────────────

def page_generate() -> None:
    st.markdown('<div class="section-title">New Generation</div>', unsafe_allow_html=True)

    form_col, cfg_col = st.columns([7, 3])

    with form_col:
        requirement = st.text_area(
            "Video Requirement",
            placeholder=(
                "Describe the educational topic, target audience, and learning goals.\n\n"
                "Example: Create a 90-second visual explainer on how gradient descent works, "
                "for undergraduates who know basic calculus. Show the loss landscape and "
                "animate parameter updates step-by-step."
            ),
            height=260,
            key="req_input",
            help="Be specific about topic, audience level, depth, and any constraints.",
            )
        chars = len(requirement)
        words = len(requirement.split()) if requirement.strip() else 0
        est_s = max(30, words // 2)
        st.markdown(
            f'<div style="text-align:right;font-size:0.7rem;color:#94A3B8;margin-top:2px;">'
            f'{chars} chars · {words} words · ~{est_s}s narration est.</div>',
            unsafe_allow_html=True,
            )

    with cfg_col:
        st.markdown('<div class="card">', unsafe_allow_html=True)

        approach = st.selectbox("Narrative Approach", APPROACHES, key="cfg_approach")
        audience = st.selectbox(
            "Target Audience",
            ["General Public", "Children (8–12)", "High School", "Undergraduate",
                "Graduate", "Professional", "Expert",
                ],
            key="cfg_audience",
            )
        complexity = st.selectbox(
            "Complexity Level",
            ["Introductory", "Intermediate", "Advanced", "Expert"],
            key="cfg_complexity",
            )
        duration = st.slider(
            "Target Duration (s)",
            30, 300, 90, 15,
            key="cfg_duration",
            format="%d s",
            )
        anim_density = st.selectbox(
            "Animation Density",
            ["Minimal", "Moderate", "Dense", "Very Dense"],
            index=1,
            key="cfg_anim",
            )
        edu_style = st.selectbox(
            "Educational Style",
            ["Lecture", "Socratic", "Demonstration", "Narrative", "Problem-Solving"],
            key="cfg_edu",
            )
        aspect = st.selectbox(
            "Aspect Ratio",
            ["9:16 (Short)", "16:9 (Widescreen)", "1:1 (Square)"],
            key="cfg_aspect",
            )
        language = st.selectbox(
            "Language",
            ["English", "Spanish", "French", "German", "Hindi", "Mandarin"],
            key="cfg_lang",
            )

        st.markdown('</div>', unsafe_allow_html=True)

        gen_btn = st.button(
            "🎬  Generate Video",
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
        st.error(f"⚠ {st.session_state.generate_error}")

    if st.session_state.session_id:
        st.markdown("---")
        sid = st.session_state.session_id
        ps = st.session_state.pipeline_status
        st.markdown(
            f'**Active session:** <span class="session-chip">{sid}</span> &nbsp; {badge(ps)}',
            unsafe_allow_html=True,
            )
        if ps in ("running", "queued"):
            st.info("⏳ Pipeline running — switch to the **Pipeline** page to monitor progress.")


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
        (c1, total, "Total Sessions", "blue"),
        (c2, completed, "Completed", "green"),
        (c3, failed, "Failed", "red"),
        (c4, running, "Running", "amber"),
        ]:
        with col:
            st.markdown(metric_tile(str(val), lbl, color), unsafe_allow_html=True)

    st.markdown('<div class="section-title">All Sessions</div>', unsafe_allow_html=True)

    if not sessions:
        st.info("No sessions found. Generate your first video to get started.")
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

        status_icon = (
            "🟢" if status == "completed" else
            "🔵" if status == "running" else
            "🔴" if status == "failed" else "⚪"
        )

        with st.expander(
                f"{status_icon} {sid[-14:]}  ·  {approach_s}  ·  {ts}",
                expanded=False,
                ):
            ci, ca = st.columns([3, 1])
            with ci:
                st.markdown(
                    f'<div style="font-family:monospace;font-size:0.78rem;color:#2563EB;margin-bottom:6px;">{sid}</div>'
                    f'<div style="font-size:0.84rem;color:#374151;margin-bottom:6px;">'
                    f'{req_prev[:180]}{"…" if len(req_prev) > 180 else ""}</div>'
                    f'<div style="font-size:0.75rem;color:#64748B;">'
                    f'{badge(status)} &nbsp;·&nbsp; {len(completed_stages)}/7 stages &nbsp;·&nbsp; {total_scn} scenes</div>',
                    unsafe_allow_html=True,
                )
            with ca:
                if st.button("View", key=f"sv_{sid}", use_container_width=True):
                    st.session_state.session_id = sid
                    st.session_state.pipeline_status = status
                    for k in ["stages", "outline", "scenes", "scene_progress", "analytics",
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
        st.info("No active session. Generate a video first or select one from Sessions.")
        return

    ps = st.session_state.pipeline_status
    stages = st.session_state.stages or []
    by_name = {s["stage"]: s for s in stages}

    # Session card + controls
    cc, ca = st.columns([3, 1])
    with cc:
        sp = st.session_state.scene_progress
        total_scn = st.session_state.total_scenes or (sp.get("total", 0) if sp else 0)
        completed_stg = sum(1 for s in stages if s.get("status") == "completed")
        total_ms = sum(s.get("duration_ms") or 0 for s in stages)
        st.markdown(
            f'<div class="card">'
            f'<div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center;">'
            f'<div><div style="font-size:0.65rem;color:#64748B;margin-bottom:3px;">SESSION</div>'
            f'<span class="session-chip">{sid}</span></div>'
            f'<div><div style="font-size:0.65rem;color:#64748B;margin-bottom:3px;">STATUS</div>'
            f'{badge(ps)}</div>'
            f'<div><div style="font-size:0.65rem;color:#64748B;margin-bottom:3px;">STAGES</div>'
            f'<span style="font-weight:700;">{completed_stg}/{len(PIPELINE_STAGES)}</span></div>'
            f'<div><div style="font-size:0.65rem;color:#64748B;margin-bottom:3px;">SCENES</div>'
            f'<span style="font-weight:700;">{total_scn or "—"}</span></div>'
            f'<div><div style="font-size:0.65rem;color:#64748B;margin-bottom:3px;">RUNTIME</div>'
            f'<span style="font-weight:700;">{fmt_dur(total_ms) if total_ms else "—"}</span></div>'
            f'</div></div>',
            unsafe_allow_html=True,
            )
    with ca:
        if st.button("↻ Refresh", key="pp_refresh", use_container_width=True):
            refresh_all(sid)
            ad = fetch_analytics(sid)
            if ad:
                st.session_state.analytics = ad.get("analytics", {})
            st.rerun()
        if ps in ("failed", "running"):
            if st.button("Resume", key="pp_resume", use_container_width=True):
                try:
                    _post(f"/resume/{sid}")
                    st.session_state.auto_poll = True
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    # Pipeline visualization
    st.markdown('<div class="section-title">Pipeline Stages</div>', unsafe_allow_html=True)
    if not stages:
        stages_placeholder = [
            {"stage": k, "label": l, "status": "pending", "duration_ms": None, "error": None}
            for k, l in PIPELINE_STAGES
            ]
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            render_pipeline(stages_placeholder)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            render_pipeline(stages)
            st.markdown('</div>', unsafe_allow_html=True)

    # Stage detail table
    done_stages = [s for s in stages if s.get("status") in ("completed", "failed", "running")]
    if done_stages:
        st.markdown('<div class="section-title">Stage Details</div>', unsafe_allow_html=True)
        for s in done_stages:
            icon = "✓" if s["status"] == "completed" else ("↺" if s["status"] == "running" else "✕")
            with st.expander(f"{icon} {s['label']}  ·  {fmt_dur(s.get('duration_ms'))}", expanded=False):
                if s.get("error"):
                    st.error(f"Error: {s['error']}")
                summ = s.get("output_summary", {})
                if summ:
                    cols = st.columns(min(len(summ), 4))
                    for i, (k, v) in enumerate(summ.items()):
                        with cols[i % len(cols)]:
                            st.metric(k.replace("_", " ").title(), str(v)[:40])
                if st.session_state.dev_mode:
                    st.json(s)

    # Scene progress (visual planning)
    vp_status = by_name.get("visual_planning", {}).get("status")
    sp = st.session_state.scene_progress
    if vp_status in ("running", "completed") and sp and sp.get("total", 0) > 0:
        st.markdown('<div class="section-title">Scene Progress — Visual Planning</div>', unsafe_allow_html=True)
        tot = sp["total"]
        done = sp.get("completed", 0)
        fail = sp.get("failed", 0)
        pct = done / tot if tot else 0
        st.markdown(
            f'<div class="card"><div style="margin-bottom:8px;font-size:0.82rem;">'
            f'<strong>{done}/{tot}</strong> scenes &nbsp;·&nbsp; '
            + (f'<span style="color:#EF4444;">{fail} failed</span>' if fail else "all ok")
            + f'</div>',
            unsafe_allow_html=True,
            )
        st.progress(pct)
        render_scenes(sp.get("scenes", []))
        st.markdown('</div>', unsafe_allow_html=True)

    # Render progress
    rs = st.session_state.render_status
    rnd_status = by_name.get("scene_rendering", {}).get("status")
    if rnd_status in ("running", "completed") and rs:
        rr = rs.get("scene_render_results", [])
        if rr:
            st.markdown('<div class="section-title">Scene Progress — Rendering</div>', unsafe_allow_html=True)
            ready = sum(1 for r in rr if r.get("status") == "READY")
            fail_r = sum(1 for r in rr if r.get("status") == "FAILED")
            scene_data = [
                {"scene_index": r.get("scene_index"), "title": r.get("title", ""),
                    "status": r.get("status", "PENDING").lower(), "error": r.get("error"),
                    }
                for r in rr
                ]
            st.markdown(
                f'<div class="card"><div style="margin-bottom:8px;font-size:0.82rem;">'
                f'<strong>{ready}</strong> ready · <strong>{fail_r}</strong> failed · <strong>{len(rr)}</strong> total'
                f'</div>',
                unsafe_allow_html=True,
                )
            render_scenes(scene_data)
            st.markdown('</div>', unsafe_allow_html=True)

    # Final video
    asm_done = by_name.get("video_assembly", {}).get("status") == "completed"
    if asm_done:
        st.markdown('<div class="section-title">Final Video</div>', unsafe_allow_html=True)
        video_url = f"{API_BASE}/video/{sid}"
        try:
            st.video(video_url)
            video_bytes = requests.get(video_url, timeout=60).content
            st.download_button(
                "⬇ Download MP4",
                data=video_bytes,
                file_name=f"{sid}_final.mp4",
                mime="video/mp4",
                key="dl_vid_pipe",
                )
        except Exception:
            st.info("Video available in the Downloads page once assembly completes.")

    # Status banner
    if ps == "completed":
        st.success("✅ Pipeline completed successfully!")
    elif ps == "failed":
        err = next((s.get("error") for s in stages if s.get("status") == "failed"), "An error occurred.")
        st.error(f"❌ Pipeline failed: {err}")
    elif ps in ("running", "queued"):
        st.info(f"⏳ Pipeline {ps}…")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: ARTIFACTS
# ─────────────────────────────────────────────────────────────────────────────

def page_artifacts() -> None:
    sid = st.session_state.session_id
    if not sid:
        st.info("No active session. Select one from Sessions or generate a new video.")
        return

    artifacts = fetch_artifacts(sid)
    if not artifacts:
        st.info("No artifacts stored yet. Run the pipeline to generate artifacts.")
        return

    ART_ORDER = [
        ("refined_input", "Intent Spec"),
        ("outline", "Outline"),
        ("scene_map", "Scene Map"),
        ("visual_plans", "Visual Plans"),
        ("manim_codes", "Manim Code"),
        ("render_results", "Render Results"),
        ]
    art_map = {a["artifact_type"]: a for a in artifacts}
    scene_arts = [a for a in artifacts if a["artifact_type"].startswith("scene_")]

    avail_tabs = [(k, l) for k, l in ART_ORDER if k in art_map]
    if scene_arts:
        avail_tabs.append(("_scenes", f"Scenes ({len(scene_arts)})"))

    if not avail_tabs:
        st.info("No viewable artifacts.")
        return

    tab_labels = [l for _, l in avail_tabs]
    tabs = st.tabs(tab_labels)

    for tab, (atype, _) in zip(tabs, avail_tabs):
        with tab:
            if atype == "_scenes":
                scene_keys = sorted(a["artifact_type"] for a in scene_arts)
                sel = st.selectbox("Select scene", scene_keys, key="scene_art_sel")
                if sel:
                    data = fetch_artifact(sid, sel)
                    if data and isinstance(data, dict):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Scene", data.get("scene_index", "?"))
                        c2.metric("Model", (data.get("model_used") or "—")[-30:])
                        c3.metric("Attempts", data.get("total_attempts", "?"))
                        if data.get("error"):
                            st.error(data["error"])
                        plan = data.get("plan")
                        if plan:
                            json_card(plan, key_suffix=f"_{sel}")
                    elif data:
                        json_card(data, key_suffix=f"_{sel}")
                continue

            art_info = art_map.get(atype, {})
            size_kb = art_info.get("size_bytes", 0) / 1024
            st.caption(f"{size_kb:.1f} KB · JSON")

            data = fetch_artifact(sid, atype)
            if data is None:
                st.warning("Could not load artifact.")
                continue

            # ── Enhanced views ──
            if atype == "refined_input" and isinstance(data, dict):
                c1, c2 = st.columns(2)
                with c1:
                    req = data.get("requirement") or data.get("refined_requirement", "—")
                    st.markdown("**Requirement**")
                    st.write(req[:400] + ("…" if len(req) > 400 else ""))
                    st.markdown(f"**Approach:** `{data.get('approach', '—')}`")
                with c2:
                    sp = data.get("system_prompt", "")
                    if sp:
                        with st.expander("System Prompt", expanded=False):
                            st.code(sp[:2000], language="text")
                with st.expander("Raw JSON", expanded=False):
                    json_card(data, key_suffix="_ri")

            elif atype == "outline" and isinstance(data, dict):
                ot = data.get("outline_type", "")
                if ot:
                    st.info(f"Approach: **{ot}**")
                outline_body = data.get("outline", data)
                if isinstance(outline_body, dict):
                    segs = outline_body.get("outline", [])
                    if segs:
                        st.markdown(f"**{len(segs)} segments:**")
                        for i, seg in enumerate(segs, 1):
                            lbl = seg.get("title", "") if isinstance(seg, dict) else str(seg)[:60]
                            with st.expander(f"Segment {i}: {lbl}", expanded=False):
                                if isinstance(seg, (dict, list)):
                                    st.json(seg)
                                elif isinstance(seg, str):
                                    st.text(seg)
                                else:
                                    st.code(str(seg))
                with st.expander("Raw JSON", expanded=False):
                    json_card(data, key_suffix="_ol")

            elif atype == "visual_plans" and isinstance(data, dict):
                plans = data.get("scene_visual_plans", [])
                t = len(plans)
                f = sum(1 for p in plans if p.get("error"))
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Scenes", t)
                c2.metric("Succeeded", t - f)
                c3.metric("Failed", f)
                for p in plans:
                    idx = p.get("scene_index", "?")
                    title = p.get("title", f"Scene {idx}")
                    has_err = bool(p.get("error"))
                    with st.expander(f"{'⚠' if has_err else '✓'} Scene {idx}: {title}", expanded=False):
                        if has_err:
                            st.error(p["error"])
                        else:
                            c1, c2 = st.columns(2)
                            c1.caption(f"Model: `{p.get('model_used', '?')}`")
                            c2.caption(f"Attempts: `{p.get('total_attempts', '?')}`")
                            if p.get("plan"):
                                json_card(p["plan"], key_suffix=f"_vp{idx}")

            elif atype == "manim_codes" and isinstance(data, dict):
                codes = data.get("scene_manim_codes", [])
                ready = sum(1 for c in codes if c.get("status") == "READY")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total", len(codes))
                c2.metric("Ready", ready)
                c3.metric("Failed", len(codes) - ready)
                for c in codes:
                    idx = c.get("scene_index", "?")
                    status = c.get("status", "?")
                    with st.expander(
                            f"{'✓' if status == 'READY' else '✕'} Scene {idx}: {c.get('title', '')} — {status}",
                            expanded=False,
                            ):
                        if c.get("error"):
                            st.error(c["error"])
                        py = c.get("python_code", "")
                        if py:
                            st.code(py[:4000], language="python")
                            if len(py) > 4000:
                                st.caption(f"Truncated. Download for full code.")
                            st.download_button(
                                f"⬇ scene_{idx:03d}.py",
                                data=py,
                                file_name=f"scene_{idx:03d}.py",
                                mime="text/x-python",
                                key=f"dl_pyc_{idx}",
                                )

            else:
                json_card(data, key_suffix=f"_{atype}")


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
        l = e.get("level", "INFO").upper()
        counts[l] = counts.get(l, 0) + 1

    m1, m2, m3, m4, m5 = st.columns(5)
    for col, val, lbl in [
        (m1, len(entries), "Shown"),
        (m2, counts.get("INFO", 0), "Info"),
        (m3, counts.get("WARNING", 0), "Warnings"),
        (m4, counts.get("ERROR", 0) + counts.get("CRITICAL", 0), "Errors"),
        (m5, total, "Total in File"),
        ]:
        col.metric(lbl, val)

    if logs_data.get("has_more"):
        st.info(f"Showing {len(entries)} of {total}. Increase limit to see more.")

    if not entries:
        st.info("No entries match the current filters.")
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
        stage = (entry.get("stage") or "")[:22]
        node = (entry.get("node") or "")[:22]
        event = entry.get("event") or ""
        details = entry.get("details") or {}
        dur_ms = entry.get("duration_ms")
        dur_str = f"{dur_ms:.0f}ms" if dur_ms else "—"

        msg_parts = [f"[{event}]"] if event else []
        if isinstance(details, dict):
            for k in ["message", "step", "stage_name", "error"]:
                if k in details:
                    msg_parts.append(str(details[k])[:120])
                    break
        msg = " ".join(msg_parts)[:220] if msg_parts else str(details)[:120]

        ll = level.lower()
        rows_html.append(
            f'<div class="log-row {ll}">'
            f'<div style="font-family:monospace;color:#64748B;white-space:nowrap;">{ts}</div>'
            f'<div><span class="lvl {ll}">{level}</span></div>'
            f'<div style="color:#64748B;font-size:0.72rem;word-break:break-word;">{stage}</div>'
            f'<div style="color:#94A3B8;font-size:0.72rem;word-break:break-word;">{node}</div>'
            f'<div style="color:#0F172A;word-break:break-word;">{msg}</div>'
            f'<div style="font-family:monospace;color:#94A3B8;white-space:nowrap;">{dur_str}</div>'
            f'</div>',
            )

    header_html = (
        '<div class="log-head">'
        '<div>Time</div><div>Level</div><div>Stage</div>'
        '<div>Node</div><div>Message</div><div>Duration</div>'
        '</div>'
    )

    st.markdown(
        '<div class="log-container">' + header_html + "".join(rows_html) + "</div>",
        unsafe_allow_html=True,
        )

    log_text = "\n".join(json.dumps(e) for e in entries)
    st.download_button(
        "⬇ Download Logs (JSONL)",
        data=log_text,
        file_name=f"{sid}_logs.jsonl",
        mime="application/x-ndjson",
        key="dl_logs_btn",
        )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

def page_analytics() -> None:
    sid = st.session_state.session_id
    if not sid:
        st.info("No active session.")
        return

    if not st.session_state.analytics:
        with st.spinner("Computing analytics…"):
            ad = fetch_analytics(sid)
            if ad:
                st.session_state.analytics = ad.get("analytics", {})

    if st.button("↻ Refresh Analytics", key="ana_refresh"):
        ad = fetch_analytics(sid)
        if ad:
            st.session_state.analytics = ad.get("analytics", {})
        st.rerun()

    ana = st.session_state.analytics

    # ── Token Usage ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Token Usage</div>', unsafe_allow_html=True)
    t_in = ana.get("total_input_tokens", 0)
    t_out = ana.get("total_output_tokens", 0)
    t_all = ana.get("total_tokens", t_in + t_out)
    calls = ana.get("total_llm_calls", 0)
    retries = ana.get("total_retries", 0)
    fallbacks = ana.get("total_fallbacks", 0)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    for col, val, lbl, color in [
        (c1, fmt_num(t_all), "Total Tokens", "blue"),
        (c2, fmt_num(t_in), "Input Tokens", ""),
        (c3, fmt_num(t_out), "Output Tokens", ""),
        (c4, str(calls), "LLM Calls", "green"),
        (c5, str(retries), "Retries", "amber"),
        (c6, str(fallbacks), "Fallbacks", ""),
        ]:
        with col:
            st.markdown(metric_tile(val, lbl, color), unsafe_allow_html=True)

    # ── Request Analytics ─────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Request Analytics</div>', unsafe_allow_html=True)
    avg_lat = ana.get("avg_llm_latency_ms", 0)
    max_lat = ana.get("max_llm_latency_ms", 0)
    min_lat = ana.get("min_llm_latency_ms", 0)
    errors = ana.get("total_errors", 0)

    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl, color in [
        (c1, f"{avg_lat:.0f} ms", "Avg LLM Latency", ""),
        (c2, f"{max_lat:.0f} ms", "Max LLM Latency", ""),
        (c3, f"{min_lat:.0f} ms", "Min LLM Latency", ""),
        (c4, str(errors), "Log Errors", "red" if errors else ""),
        ]:
        with col:
            st.markdown(metric_tile(val, lbl, color), unsafe_allow_html=True)

    # ── Model Usage Table ─────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Model Usage</div>', unsafe_allow_html=True)
    model_usage = ana.get("model_usage", [])
    if model_usage:
        try:
            import pandas as pd

            df = pd.DataFrame(model_usage)
            cols_show = [c for c in
                ["model", "provider", "requests", "input_tokens", "output_tokens",
                    "total_tokens", "avg_latency_ms", "retries",
                    ]
                if c in df.columns]
            st.dataframe(
                df[cols_show],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "model": st.column_config.TextColumn("Model"),
                    "provider": st.column_config.TextColumn("Provider"),
                    "requests": st.column_config.NumberColumn("Requests"),
                    "input_tokens": st.column_config.NumberColumn("Input"),
                    "output_tokens": st.column_config.NumberColumn("Output"),
                    "total_tokens": st.column_config.NumberColumn("Total"),
                    "avg_latency_ms": st.column_config.NumberColumn("Avg Latency (ms)", format="%.1f"),
                    "retries": st.column_config.NumberColumn("Retries"),
                    },
                )
        except ImportError:
            for m in model_usage:
                st.write(m)
    else:
        st.info("No LLM call data available for this session.")

    # ── Pipeline Performance ──────────────────────────────────────────────────
    stages = st.session_state.stages
    if stages:
        st.markdown('<div class="section-title">Pipeline Performance</div>', unsafe_allow_html=True)
        timed = [(s["label"], s["duration_ms"]) for s in stages if s.get("duration_ms")]
        if timed:
            total_ms = sum(d for _, d in timed)
            fastest = min(timed, key=lambda x: x[1])
            slowest = max(timed, key=lambda x: x[1])
            p1, p2, p3 = st.columns(3)
            p1.metric("Total Runtime", fmt_dur(total_ms))
            p2.metric("Fastest Stage", f"{fastest[0]} · {fmt_dur(fastest[1])}")
            p3.metric("Slowest Stage", f"{slowest[0]} · {fmt_dur(slowest[1])}")
            try:
                import pandas as pd

                df2 = pd.DataFrame(timed, columns=["Stage", "ms"])
                df2["s"] = (df2["ms"] / 1000).round(2)
                st.bar_chart(df2.set_index("Stage")["s"], use_container_width=True)
            except ImportError:
                pass

    # ── Errors ───────────────────────────────────────────────────────────────
    err_list = ana.get("errors", [])
    if err_list:
        st.markdown('<div class="section-title">Log Errors</div>', unsafe_allow_html=True)
        for e in err_list:
            ts_str = (e.get("timestamp") or "")[:19]
            stage = e.get("stage", "?")
            node = e.get("node", "?")
            etype = e.get("error_type", "Error")
            msg = (e.get("message") or "")[:200]
            st.error(f"**{etype}** — `{stage}/{node}` — {ts_str}\n{msg}")

    if st.session_state.dev_mode:
        st.markdown('<div class="section-title">Raw Analytics (Dev)</div>', unsafe_allow_html=True)
        st.json(ana)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: DOWNLOADS
# ─────────────────────────────────────────────────────────────────────────────

def page_downloads() -> None:
    sid = st.session_state.session_id
    if not sid:
        st.info("No active session.")
        return

    stages_map = {s["stage"]: s for s in (st.session_state.stages or [])}

    # ── Artifacts ─────────────────────────────────────────────────────────────
    st.markdown("#### Pipeline Artifacts (JSON)")
    arts = fetch_artifacts(sid)
    if arts:
        for a in arts:
            atype = a["artifact_type"]
            label = a["label"]
            size_kb = a.get("size_bytes", 0) / 1024
            c1, c2, c3 = st.columns([4, 2, 1])
            with c1:
                st.markdown(f'<div class="dl-row"><span class="dl-name">📄 {label}</span>'
                            f'<span class="dl-meta">{size_kb:.1f} KB</span></div>',
                    unsafe_allow_html=True,
                    )
            with c3:
                d = fetch_artifact(sid, atype)
                if d is not None:
                    st.download_button(
                        "⬇",
                        data=json.dumps(d, indent=2),
                        file_name=f"{atype}.json",
                        mime="application/json",
                        key=f"dl_a_{atype}",
                        use_container_width=True,
                        )
    else:
        st.info("No artifacts yet.")

    # ── Logs ─────────────────────────────────────────────────────────────────
    st.markdown("#### Logs")
    c1, _, c3 = st.columns([4, 2, 1])
    with c1:
        st.markdown('<div class="dl-row"><span class="dl-name">📜 Session Logs</span>'
                    '<span class="dl-meta">JSONL</span></div>',
            unsafe_allow_html=True,
            )
    with c3:
        ld = fetch_logs(sid, limit=2000)
        if ld:
            log_raw = "\n".join(json.dumps(e) for e in ld.get("entries", []))
            st.download_button(
                "⬇",
                data=log_raw,
                file_name=f"{sid}_logs.jsonl",
                mime="application/x-ndjson",
                key="dl_logs_dc",
                use_container_width=True,
                )

    # ── Python Code ──────────────────────────────────────────────────────────
    codes_data = fetch_artifact(sid, "manim_codes")
    if codes_data and isinstance(codes_data, dict):
        codes = codes_data.get("scene_manim_codes", [])
        ready_codes = [c for c in codes if c.get("python_code")]
        if ready_codes:
            st.markdown("#### Generated Python / Manim Code")
            for c in ready_codes:
                idx = c.get("scene_index", "?")
                py = c.get("python_code", "")
                c1, _, c3 = st.columns([4, 2, 1])
                with c1:
                    st.markdown(
                        f'<div class="dl-row"><span class="dl-name">🐍 scene_{idx:03d}.py</span>'
                        f'<span class="dl-meta">{len(py):,} chars</span></div>',
                        unsafe_allow_html=True,
                        )
                with c3:
                    st.download_button(
                        "⬇",
                        data=py,
                        file_name=f"scene_{idx:03d}.py",
                        mime="text/x-python",
                        key=f"dl_py_{idx}",
                        use_container_width=True,
                        )

    # ── Final Video ───────────────────────────────────────────────────────────
    asm_done = stages_map.get("video_assembly", {}).get("status") == "completed"
    if asm_done:
        st.markdown("#### Final Video")
        video_url = f"{API_BASE}/video/{sid}"
        c1, _, c3 = st.columns([4, 2, 1])
        with c1:
            st.markdown(f'<div class="dl-row"><span class="dl-name">🎬 {sid}_final.mp4</span>'
                        f'<span class="dl-meta">MP4</span></div>',
                unsafe_allow_html=True,
                )
        with c3:
            try:
                vbytes = requests.get(video_url, timeout=60).content
                st.download_button(
                    "⬇",
                    data=vbytes,
                    file_name=f"{sid}_final.mp4",
                    mime="video/mp4",
                    key="dl_vid_dc",
                    use_container_width=True,
                )
            except Exception:
                st.caption("Not available yet")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

_sidebar()

sid = st.session_state.session_id
ps = st.session_state.pipeline_status

# Header bar
pulse_cls = "pulse" if ps in ("running", "queued") else ""
status_dot_color = (
    "#2563EB" if ps in ("running", "queued") else
    "#22C55E" if ps == "completed" else
    "#EF4444" if ps == "failed" else "#94A3B8"
)
st.markdown(
    f'<div class="app-header">'
    f'<div style="display:flex;align-items:center;">'
    f'<span class="app-logo">🎬 Text-2-Shorts</span>'
    f'<span class="app-version">v{VERSION}</span>'
    f'</div>'
    + (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="width:8px;height:8px;border-radius:50%;background:{status_dot_color};'
        f'display:inline-block;" class="{pulse_cls}"></span>'
        f'<span class="session-chip">{sid}</span>'
        f'</div>'
        if sid else
        '<div style="font-size:0.82rem;color:#94A3B8;">No active session</div>'
    )
    + '</div>',
    unsafe_allow_html=True,
    )

# Three-column layout: empty gutter | main content | right panel
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
    elif page == "Artifacts":
        page_artifacts()
    elif page == "Logs":
        page_logs()
    elif page == "Analytics":
        page_analytics()
    elif page == "Downloads":
        page_downloads()

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
        ad = fetch_analytics(st.session_state.session_id)
        if ad:
            st.session_state.analytics = ad.get("analytics", {})
    st.rerun()
