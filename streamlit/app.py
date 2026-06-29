"""
Text-2-Shorts — Streamlit UI
White theme with light-blue accents. Tabs: Generate | Sessions.
Features: per-stage + per-scene progress, artifact preview, saved-session resume.
"""

from __future__ import annotations

import json
import time
import uuid

import requests
import streamlit.components.v1 as components

import streamlit as st


API_BASE = "http://localhost:8000"
POLL_INTERVAL_S = 3.0

APPROACHES = [
    "Classic Linear Narrative",
    "Conceptual Zoom",
    "Problem-Solution Arc",
    ]

PIPELINE_STAGES = [
    ("validate_input", "Validate Input"),
    ("generate_outline", "Gen Outline"),
    ("map_outline", "Map Scenes"),
    ("visual_planning", "Visual Plans"),
    ("manim_code_generation", "Gen Code"),
    ("scene_rendering", "Render"),
    ("video_assembly", "Assemble"),
    ]

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Text-2-Shorts",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed",
    )

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
        /* Core layout */
        .stApp { background-color: #ffffff; color: #111827; }
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 860px;
        }

        /* Global text color */
        html, body, [class*="st-"], .stMarkdown, .stMarkdown *,
        label, .stSelectbox label, .stTextArea label,
        .stCaption, .stCaption p, span, div {
            color: #111827 !important;
        }

        /* Typography */
        h1 { font-size: 1.65rem !important; font-weight: 700 !important;
             color: #111827 !important; margin-bottom: 0.1rem !important; }
        h2 { font-size: 1.05rem !important; font-weight: 600 !important;
             color: #111827 !important; margin: 1rem 0 0.4rem 0 !important; }
        p, .stMarkdown p { color: #111827 !important; }

        /* Divider */
        hr { border: none; border-top: 1px solid #E5E7EB; margin: 1.1rem 0; }

        /* Inputs */
        textarea, .stTextArea textarea {
            border: 1px solid #D1D5DB !important;
            border-radius: 6px !important;
            background: #FFFFFF !important;
        }
        textarea:focus, .stTextArea textarea:focus {
            border-color: #3B82F6 !important;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
        }

        /* Primary button */
        .stButton > button[kind="primary"] {
            background: #3B82F6 !important;
            border: none !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
            padding: 0.45rem 1.4rem !important;
        }
        .stButton > button[kind="primary"]:hover {
            background: #2563EB !important;
        }

        /* Session ID chip */
        .session-chip {
            display: inline-block;
            font-family: 'Courier New', monospace;
            font-size: 0.78rem;
            background: #EFF6FF;
            border: 1px solid #BFDBFE;
            border-radius: 4px;
            padding: 2px 8px;
            color: #1D4ED8;
        }

        /* Stage progress row */
        .stage-progress {
            display: flex;
            align-items: flex-start;
            gap: 0;
            padding: 1rem 0.25rem 0.5rem;
        }
        .stage-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            flex: 0 0 auto;
            width: 120px;
        }
        .stage-dot {
            width: 34px;
            height: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.35rem;
            line-height: 1;
            background: transparent;
            border: none;
        }
        .stage-dot.completed,
        .stage-dot.running,
        .stage-dot.failed,
        .stage-dot.pending,
        .stage-dot.skipped { background: transparent; border: none; }
        .stage-label {
            font-size: 0.7rem;
            text-align: center;
            margin-top: 5px;
            line-height: 1.3;
        }
        .stage-label.completed { color: #065F46 !important; font-weight: 500; }
        .stage-label.running   { color: #1D4ED8 !important; font-weight: 500; }
        .stage-label.failed    { color: #991B1B !important; font-weight: 500; }
        .stage-label.pending   { color: #374151 !important; }
        .stage-label.skipped   { color: #374151 !important; }
        .stage-time {
            font-size: 0.65rem;
            color: #374151 !important;
            margin-top: 2px;
            text-align: center;
        }
        .stage-connector {
            flex: 1;
            height: 2px;
            margin-top: 16px;
            min-width: 8px;
        }
        .stage-connector.completed { background: #10B981; }
        .stage-connector.active    { background: #3B82F6; }
        .stage-connector.inactive  { background: #E5E7EB; }

        /* Scene progress grid */
        .scene-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            padding: 0.5rem 0;
        }
        .scene-dot {
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.05rem;
            line-height: 1;
            background: transparent;
            border: none;
            cursor: default;
        }
        .scene-dot.completed,
        .scene-dot.running,
        .scene-dot.failed,
        .scene-dot.pending { background: transparent; border: none; }

        /* Output card */
        .output-card {
            border: 1px solid #DBEAFE;
            border-radius: 8px;
            padding: 0.8rem 1rem;
            margin: 0.5rem 0;
            background: #F0F9FF;
        }
        .output-card h4 {
            margin: 0 0 0.35rem 0 !important;
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            color: #111827 !important;
        }
        .output-card p { color: #111827 !important; margin: 0; }

        /* Session list card */
        .session-card {
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin: 0.5rem 0;
            background: #FAFAFA;
        }
        .session-card:hover { border-color: #BFDBFE; background: #F0F9FF; }
        .session-card .s-title { font-weight: 600; font-size: 0.88rem; color: #111827; }
        .session-card .s-meta  { font-size: 0.75rem; color: #6B7280; margin-top: 3px; }

        /* Error banner */
        .error-banner {
            border: 1px solid #FCA5A5;
            border-radius: 6px;
            background: #FEF2F2;
            padding: 0.6rem 0.9rem;
            color: #991B1B;
            font-size: 0.85rem;
            margin: 0.5rem 0;
        }

        /* Code blocks */
        .stCodeBlock { border-radius: 6px !important; }

        /* Expanders */
        details summary {
            font-size: 0.9rem !important;
            font-weight: 600 !important;
            color: #1F2937 !important;
        }

        code { font-size: 0.82rem !important; }
        #MainMenu, footer { visibility: hidden; }
        header { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
    )

# ── Session state ─────────────────────────────────────────────────────────────

_defaults = {
    "session_id": None,
    "pipeline_status": "idle",
    "stages": [],
    "scene_progress": None,
    "render_status": None,  # per-scene render results
    "final_video_path": None,
    "outline": None,
    "outline_type": None,
    "scenes": None,
    "total_scenes": 0,
    "generate_error": None,
    "auto_poll": False,
    "artifact_preview": None,  # {session_id, artifact_type, data}
    }
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── API helpers ───────────────────────────────────────────────────────────────

def _post_generate(requirement: str, approach: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/generate",
        json={"requirement": requirement, "approach": approach, "session_id": uuid.uuid4().hex},
        timeout=15,
        )
    resp.raise_for_status()
    return resp.json()


def _post_resume(session_id: str) -> dict:
    resp = requests.post(f"{API_BASE}/resume/{session_id}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def _fetch_stages(session_id: str) -> dict | None:
    try:
        resp = requests.get(f"{API_BASE}/stages/{session_id}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _fetch_scene_progress(session_id: str) -> dict | None:
    try:
        resp = requests.get(f"{API_BASE}/scenes/{session_id}/progress", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _fetch_outline(session_id: str) -> dict | None:
    try:
        resp = requests.get(f"{API_BASE}/outputs/{session_id}/outline", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _fetch_scenes(session_id: str) -> dict | None:
    try:
        resp = requests.get(f"{API_BASE}/outputs/{session_id}/scenes", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _fetch_sessions() -> list[dict]:
    try:
        resp = requests.get(f"{API_BASE}/sessions", timeout=10)
        resp.raise_for_status()
        return resp.json().get("sessions", [])
    except Exception:
        return []


def _fetch_artifacts(session_id: str) -> list[dict]:
    try:
        resp = requests.get(f"{API_BASE}/artifacts/{session_id}", timeout=10)
        resp.raise_for_status()
        return resp.json().get("artifacts", [])
    except Exception:
        return []


def _fetch_render_status(session_id: str) -> dict | None:
    try:
        resp = requests.get(f"{API_BASE}/render/status/{session_id}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _fetch_artifact(session_id: str, artifact_type: str) -> dict | None:
    try:
        resp = requests.get(f"{API_BASE}/artifact/{session_id}/{artifact_type}", timeout=10)
        resp.raise_for_status()
        return resp.json().get("data")
    except Exception:
        return None


def _refresh_all(session_id: str) -> None:
    data = _fetch_stages(session_id)
    if not data:
        return

    st.session_state.stages = data.get("stages", [])
    st.session_state.pipeline_status = data.get("pipeline_status", "running")

    stages_by_name = {s["stage"]: s for s in st.session_state.stages}

    # Fetch scene progress when visual_planning is active or done
    vp_stage = stages_by_name.get("visual_planning", {})
    if vp_stage.get("status") in ("running", "completed"):
        sp = _fetch_scene_progress(session_id)
        if sp:
            st.session_state.scene_progress = sp

    # Fetch outline when that stage completes
    outline_stage = stages_by_name.get("generate_outline", {})
    if outline_stage.get("status") == "completed" and st.session_state.outline is None:
        od = _fetch_outline(session_id)
        if od and od.get("outline"):
            st.session_state.outline = od["outline"]
            st.session_state.outline_type = od.get("outline_type")

    # Fetch scenes when visual_planning completes
    if vp_stage.get("status") == "completed" and st.session_state.scenes is None:
        sd = _fetch_scenes(session_id)
        if sd and sd.get("scene_visual_plans"):
            st.session_state.scenes = sd["scene_visual_plans"]
            st.session_state.total_scenes = sd.get("total_scenes", len(sd["scene_visual_plans"]))

    # Fetch render status when scene_rendering is active or done
    render_stage = stages_by_name.get("scene_rendering", {})
    if render_stage.get("status") in ("running", "completed"):
        rs = _fetch_render_status(session_id)
        if rs:
            st.session_state.render_status = rs

    # Capture final video path when video_assembly completes
    assembly_stage = stages_by_name.get("video_assembly", {})
    if assembly_stage.get("status") == "completed":
        summary = assembly_stage.get("output_summary", {})
        if summary.get("final_video_path"):
            st.session_state.final_video_path = summary["final_video_path"]


# ── Stage progress HTML ───────────────────────────────────────────────────────

def _stage_icon(status: str) -> str:
    return {
        "completed": "🟢",
        "running": "🔵",
        "failed": "🔴",
        "pending": "⚪",
        "skipped": "⚫",
        }.get(status, "⚪")


def _connector_class(left_status: str, right_status: str) -> str:
    if left_status == "completed":
        return "completed"
    if right_status in ("running", "completed"):
        return "active"
    return "inactive"


def _render_stage_row(ordered: list[tuple[str, str]], stages_by_name: dict) -> str:
    items_html = []
    for i, (key, label) in enumerate(ordered):
        info = stages_by_name.get(key, {})
        status = info.get("status", "pending")
        icon = _stage_icon(status)
        dur = info.get("duration_ms")
        time_str = (
            f"{dur / 1000:.1f}s" if dur is not None
            else "running…" if status == "running"
            else ""
        )
        items_html.append(
            f'<div class="stage-item">'
            f'<div class="stage-dot {status}">{icon}</div>'
            f'<div class="stage-label {status}">{label}</div>'
            f'<div class="stage-time">{time_str}</div>'
            f'</div>',
            )
        if i < len(ordered) - 1:
            next_status = stages_by_name.get(ordered[i + 1][0], {}).get("status", "pending")
            cls = _connector_class(status, next_status)
            items_html.append(f'<div class="stage-connector {cls}"></div>')
    return '<div class="stage-progress">' + "".join(items_html) + "</div>"


def _render_stage_progress(stages: list[dict]) -> None:
    stages_by_name = {s["stage"]: s for s in stages}
    # Row 1: outline pipeline (first 4 stages)
    row1 = PIPELINE_STAGES[:4]
    # Row 2: render pipeline (last 3 stages)
    row2 = PIPELINE_STAGES[4:]
    st.markdown(
        _render_stage_row(row1, stages_by_name)
        + _render_stage_row(row2, stages_by_name),
        unsafe_allow_html=True,
        )


# ── Scene progress panel ──────────────────────────────────────────────────────

def _scene_icon(status: str) -> str:
    return {
        "completed": "🟢", "running": "🔵", "failed": "🔴", "pending": "⚪",
        "ready": "🟢", "rendering": "🔵", "debugging": "🟡", "refactoring": "🟠",
        "generating": "🔵",
        }.get(status.lower(), "⚪")


def _render_scene_progress(sp: dict) -> None:
    total = sp.get("total", 0)
    completed = sp.get("completed", 0)
    failed = sp.get("failed", 0)
    running_idx = sp.get("running_index")
    scenes = sp.get("scenes", [])

    if total == 0:
        return

    pct = int(completed / total * 100) if total else 0
    running_label = f"Scene {running_idx} / {total}" if running_idx else f"{completed} / {total} done"

    st.markdown(
        f'<div style="font-size:0.82rem;color:#374151;margin-bottom:4px;">'
        f'<strong>Scene progress:</strong> {running_label} &nbsp;·&nbsp; {pct}%'
        + (f' &nbsp;·&nbsp; <span style="color:#991B1B">{failed} failed</span>' if failed else "")
        + "</div>",
        unsafe_allow_html=True,
        )

    # Dot grid
    dots = []
    for s in scenes:
        idx = s.get("scene_index", "?")
        status = s.get("status", "pending")
        icon = _scene_icon(status)
        title = s.get("title", f"Scene {idx}")
        dots.append(
            f'<div class="scene-dot {status}" title="{idx}: {title}">{icon}</div>',
            )
    st.markdown(
        '<div class="scene-grid">' + "".join(dots) + "</div>",
        unsafe_allow_html=True,
        )


# ── Copy button ───────────────────────────────────────────────────────────────

def _copy_button(text: str, key: str = "copy") -> None:
    safe = json.dumps(text)
    components.html(
        f"""
        <button id="btn_{key}"
            onclick="navigator.clipboard.writeText({safe})
                .then(()=>{{
                    var b=document.getElementById('btn_{key}');
                    b.textContent='✓ Copied';
                    setTimeout(()=>b.textContent='Copy JSON',2000);
                }});"
            style="cursor:pointer;padding:5px 14px;border:1px solid #BFDBFE;
                   border-radius:4px;background:#EFF6FF;color:#1D4ED8;
                   font-size:12px;font-family:-apple-system,sans-serif;">
            Copy JSON
        </button>
        """,
        height=38,
        )


# ── Artifact preview section ──────────────────────────────────────────────────

def _render_artifact_preview(session_id: str) -> None:
    """Show list of available artifacts with expandable JSON preview."""
    artifacts = _fetch_artifacts(session_id)
    if not artifacts:
        st.caption("No artifacts stored yet.")
        return

    sid_slug = session_id[:12]
    for art in artifacts:
        atype = art["artifact_type"]
        label = art["label"]
        size_kb = art["size_bytes"] / 1024
        with st.expander(f"{label} — {size_kb:.1f} KB", expanded=False):
            data = _fetch_artifact(session_id, atype)
            if data is None:
                st.warning("Could not load artifact.")
            else:
                json_str = json.dumps(data, indent=2)
                st.code(json_str[:8000], language="json")
                if len(json_str) > 8000:
                    st.caption(f"Showing first 8 KB of {len(json_str) // 1024} KB")
                col_c, col_d, _ = st.columns([1.2, 1.2, 2])
                with col_c:
                    _copy_button(json_str, key=f"art_{sid_slug}_{atype}")
                with col_d:
                    st.download_button(
                        "Download",
                        data=json_str,
                        file_name=f"{atype}.json",
                        mime="application/json",
                        key=f"artifact_download_{sid_slug}_{atype}",
                        use_container_width=True,
                        )


# ── Main header ───────────────────────────────────────────────────────────────

st.markdown("<h1>🎬 Text-2-Shorts</h1>", unsafe_allow_html=True)
st.markdown(
    '<p style="margin:0;color:#374151;font-size:0.9rem;">'
    "Generate structured educational video outlines from plain text."
    "</p>",
    unsafe_allow_html=True,
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_generate, tab_sessions = st.tabs(["Generate", "Sessions"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — GENERATE
# ═══════════════════════════════════════════════════════════════════════════════

with tab_generate:

    # Input form
    requirement = st.text_area(
        "Video Requirement",
        placeholder="Describe the educational topic, target audience, and any constraints…",
        height=120,
        help="Be specific about the concept, depth, and audience level.",
    )

    approach = st.selectbox(
        "Narrative Approach",
        options=APPROACHES,
        help="Determines the outline structure the LLM follows.",
    )

    col_btn, col_spacer = st.columns([1, 3])
    with col_btn:
        generate_clicked = st.button(
            "Generate",
            type="primary",
            key="btn_generate",
            disabled=not requirement.strip(),
            use_container_width=True,
            )

    if generate_clicked:
        st.session_state.generate_error = None
        st.session_state.outline = None
        st.session_state.outline_type = None
        st.session_state.scenes = None
        st.session_state.total_scenes = 0
        st.session_state.stages = []
        st.session_state.scene_progress = None
        st.session_state.render_status = None
        st.session_state.final_video_path = None
        st.session_state.pipeline_status = "queued"
        st.session_state.auto_poll = True
        try:
            data = _post_generate(requirement.strip(), approach)
            st.session_state.session_id = data.get("session_id")
        except requests.HTTPError as exc:
            st.session_state.generate_error = (
                f"API error {exc.response.status_code}: {exc.response.text}"
            )
            st.session_state.auto_poll = False
            st.session_state.pipeline_status = "failed"
        except Exception as exc:
            st.session_state.generate_error = str(exc)
            st.session_state.auto_poll = False
            st.session_state.pipeline_status = "failed"

    # Error banner
    if st.session_state.generate_error:
        st.markdown(
            f'<div class="error-banner">⚠ {st.session_state.generate_error}</div>',
            unsafe_allow_html=True,
            )

    # Results section
    if st.session_state.session_id:
        st.markdown("<hr>", unsafe_allow_html=True)

        col_id, col_refresh = st.columns([3, 1])
        with col_id:
            st.markdown(
                f"Session &nbsp;"
                f'<span class="session-chip">{st.session_state.session_id}</span>',
                unsafe_allow_html=True,
                )
        with col_refresh:
            refresh_clicked = st.button(
                "↻ Refresh",
                key="btn_refresh",
                use_container_width=True,
                help="Manually poll for latest pipeline status",
            )
        if refresh_clicked:
            _refresh_all(st.session_state.session_id)

        # ── Stage progress ─────────────────────────────────────────────────

        st.markdown("<h2>Pipeline Progress</h2>", unsafe_allow_html=True)

        stages = st.session_state.stages
        if not stages:
            _render_stage_progress([
                {"stage": k, "label": l, "status": "pending", "duration_ms": None, "error": None}
                for k, l in PIPELINE_STAGES
                ],
                )
        else:
            _render_stage_progress(stages)

        # Scene-level progress (visual planning phase)
        stages_by_name = {s["stage"]: s for s in stages}
        vp_status = stages_by_name.get("visual_planning", {}).get("status")
        if vp_status in ("running", "completed") and st.session_state.scene_progress:
            _render_scene_progress(st.session_state.scene_progress)

        # Render-level scene progress (scene_rendering phase)
        render_stage_status = stages_by_name.get("scene_rendering", {}).get("status")
        if render_stage_status in ("running", "completed") and st.session_state.render_status:
            rs = st.session_state.render_status
            render_results = rs.get("scene_render_results", [])
            if render_results:
                ready = sum(1 for r in render_results if r.get("status") == "READY")
                failed = sum(1 for r in render_results if r.get("status") == "FAILED")
                total_r = len(render_results)
                st.markdown(
                    f'<div style="font-size:0.82rem;color:#374151;margin-bottom:4px;">'
                    f'<strong>Render progress:</strong> {ready}/{total_r} ready'
                    + (f' · <span style="color:#991B1B">{failed} failed</span>' if failed else "")
                    + "</div>",
                    unsafe_allow_html=True,
                    )
                dots = []
                for r in render_results:
                    status = r.get("status", "PENDING").lower()
                    idx = r.get("scene_index", "?")
                    attempts = r.get("render_attempts", 0)
                    title = r.get("title", f"Scene {idx}")
                    icon = _scene_icon(status)
                    tooltip = f"{idx}: {title} ({status}, {attempts} attempts)"
                    dots.append(f'<div class="scene-dot" title="{tooltip}">{icon}</div>')
                st.markdown(
                    '<div class="scene-grid">' + "".join(dots) + "</div>",
                    unsafe_allow_html=True,
                    )

        # Pipeline status banner
        ps = st.session_state.pipeline_status
        if ps == "completed":
            st.success("Pipeline completed successfully.", icon="✅")
        elif ps == "failed":
            err = next((s["error"] for s in stages if s.get("error")), "An error occurred.")
            st.error(f"Pipeline failed: {err}", icon="❌")
        elif ps in ("running", "queued"):
            st.info("Pipeline is running…")

        # ── Stage output summaries ─────────────────────────────────────────

        completed_stages = [s for s in stages if s.get("status") == "completed"]
        if completed_stages:
            st.markdown("<h2>Stage Outputs</h2>", unsafe_allow_html=True)
            for stage in completed_stages:
                summary = stage.get("output_summary", {})
                name = stage["label"]
                dur_s = f" · {stage['duration_ms'] / 1000:.1f}s" if stage.get("duration_ms") else ""

                if stage["stage"] == "validate_input":
                    refined_len = summary.get("refined_len", 0)
                    st.markdown(
                        f'<div class="output-card"><h4>✓ {name}{dur_s}</h4>'
                        f"<p style='font-size:0.8rem;'>Refined requirement: <strong>{refined_len}</strong> chars</p></div>",
                        unsafe_allow_html=True,
                        )
                elif stage["stage"] == "generate_outline":
                    seg_count = summary.get("segment_count", "?")
                    outline_type = summary.get("outline_type") or ""
                    st.markdown(
                        f'<div class="output-card"><h4>✓ {name}{dur_s}</h4>'
                        f"<p style='font-size:0.8rem;'><strong>{seg_count}</strong> segments · <em>{outline_type}</em></p></div>",
                        unsafe_allow_html=True,
                        )
                elif stage["stage"] == "map_outline":
                    total = summary.get("total_scenes", "?")
                    st.markdown(
                        f'<div class="output-card"><h4>✓ {name}{dur_s}</h4>'
                        f"<p style='font-size:0.8rem;'>Mapped <strong>{total}</strong> scenes</p></div>",
                        unsafe_allow_html=True,
                        )
                elif stage["stage"] == "visual_planning":
                    total = summary.get("total_scenes", "?")
                    failed = summary.get("failed_scenes", 0)
                    ok = int(total) - failed if isinstance(total, int) else "?"
                    note = (
                        f"<strong>{ok}</strong> succeeded, <strong>{failed}</strong> failed"
                        if failed
                        else f"<strong>{total}</strong> scenes generated"
                    )
                    st.markdown(
                        f'<div class="output-card"><h4>✓ {name}{dur_s}</h4>'
                        f"<p style='font-size:0.8rem;'>{note}</p></div>",
                        unsafe_allow_html=True,
                        )
                elif stage["stage"] == "manim_code_generation":
                    ready = summary.get("ready_scenes", "?")
                    failed = summary.get("failed_scenes", 0)
                    note = (
                            f"<strong>{ready}</strong> code files generated"
                            + (f", <strong>{failed}</strong> failed" if failed else "")
                    )
                    st.markdown(
                        f'<div class="output-card"><h4>✓ {name}{dur_s}</h4>'
                        f"<p style='font-size:0.8rem;'>{note}</p></div>",
                        unsafe_allow_html=True,
                        )
                elif stage["stage"] == "scene_rendering":
                    ready = summary.get("ready_scenes", "?")
                    failed = summary.get("failed_scenes", 0)
                    note = (
                            f"<strong>{ready}</strong> scenes rendered"
                            + (f", <strong>{failed}</strong> failed" if failed else "")
                    )
                    st.markdown(
                        f'<div class="output-card"><h4>✓ {name}{dur_s}</h4>'
                        f"<p style='font-size:0.8rem;'>{note}</p></div>",
                        unsafe_allow_html=True,
                        )
                elif stage["stage"] == "video_assembly":
                    asm_ms = summary.get("assembly_duration_ms")
                    asm_str = f" · assembled in {asm_ms / 1000:.1f}s" if asm_ms else ""
                    st.markdown(
                        f'<div class="output-card"><h4>✓ {name}{dur_s}</h4>'
                        f"<p style='font-size:0.8rem;'>Final video ready{asm_str}</p></div>",
                        unsafe_allow_html=True,
                        )

        # Failed stage banners
        for stage in stages:
            if stage.get("status") == "failed":
                st.markdown(
                    f'<div class="error-banner"><strong>{stage["label"]}</strong>'
                    f' failed: {stage.get("error", "Unknown error")}</div>',
                    unsafe_allow_html=True,
                )

        # ── Outline output ─────────────────────────────────────────────────

        if st.session_state.outline:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("<h2>Generated Outline</h2>", unsafe_allow_html=True)
            if st.session_state.outline_type:
                st.caption(f"Approach: **{st.session_state.outline_type}**")
            json_str = json.dumps(st.session_state.outline, indent=2)
            with st.expander("View outline JSON", expanded=True):
                st.code(json_str, language="json")
                col_c, col_d, _ = st.columns([1.2, 1.2, 2])
                with col_c:
                    _copy_button(json_str, key="outline_copy")
                with col_d:
                    st.download_button(
                        "Download",
                        data=json_str,
                        file_name="outline.json",
                        mime="application/json",
                        key="download_outline",
                        use_container_width=True,
                        )

        # ── Scene visual plans ─────────────────────────────────────────────

        if st.session_state.scenes:
            st.markdown("<hr>", unsafe_allow_html=True)
            total = st.session_state.total_scenes or len(st.session_state.scenes)
            st.markdown(
                f"<h2>Scene Visual Plans "
                f"<span style='font-weight:400;color:#374151;font-size:0.82rem;'>"
                f"({total} scenes)</span></h2>",
                unsafe_allow_html=True,
                )
            for plan in st.session_state.scenes:
                idx = plan.get("scene_index", "?")
                title = plan.get("title", f"Scene {idx}")
                plan_data = plan.get("plan") or {}
                has_error = bool(plan.get("error"))
                label = f"Scene {idx}: {title}" + (" ⚠" if has_error else "")
                with st.expander(label, expanded=False):
                    if has_error:
                        st.error(f"Generation failed: {plan['error']}")
                    else:
                        meta_parts = []
                        if plan.get("model_used"):
                            meta_parts.append(f"Model: `{plan['model_used']}`")
                        if plan.get("total_attempts"):
                            meta_parts.append(f"Attempts: `{plan['total_attempts']}`")
                        if meta_parts:
                            st.caption(" · ".join(meta_parts))
                        plan_json = (
                            json.dumps(plan_data, indent=2) if isinstance(plan_data, dict)
                            else str(plan_data)
                        )
                        st.code(plan_json, language="json" if isinstance(plan_data, dict) else "text")

            all_json = json.dumps(st.session_state.scenes, indent=2)
            st.download_button(
                "Download all scene plans (JSON)",
                data=all_json,
                file_name="scene_visual_plans.json",
                mime="application/json",
                key="download_all_scene_plans",
                )

        # ── Final video ────────────────────────────────────────────────────

        assembly_done = stages_by_name.get("video_assembly", {}).get("status") == "completed"
        if assembly_done and st.session_state.session_id:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("<h2>Final Video</h2>", unsafe_allow_html=True)
            video_url = f"{API_BASE}/video/{st.session_state.session_id}"
            st.video(video_url)
            st.download_button(
                "Download Video (MP4)",
                data=requests.get(video_url, timeout=60).content,
                file_name=f"{st.session_state.session_id}_final.mp4",
                mime="video/mp4",
                key="download_final_video",
                )

        # ── Artifact preview ───────────────────────────────────────────────

        if st.session_state.session_id and completed_stages:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("<h2>Stored Artifacts</h2>", unsafe_allow_html=True)
            _render_artifact_preview(st.session_state.session_id)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SESSIONS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_sessions:
    col_hdr, col_reload = st.columns([3, 1])
    with col_hdr:
        st.markdown("<h2>Saved Sessions</h2>", unsafe_allow_html=True)
    with col_reload:
        reload_sessions = st.button("↻ Reload", key="reload_sessions", use_container_width=True)

    sessions_list = _fetch_sessions()

    if not sessions_list:
        st.info("No sessions found. Generate a video outline to create your first session.")
    else:
        st.caption(f"{len(sessions_list)} session(s) recorded.")
        st.markdown("<hr>", unsafe_allow_html=True)

        for s in sessions_list:
            sid = s.get("session_id", "?")
            approach_s = s.get("approach", "Unknown approach")
            req_preview = s.get("requirement_preview", "")
            pipeline_status = s.get("pipeline_status", "unknown")
            completed_stgs = s.get("completed_stages", [])
            total_scn = s.get("total_scenes", 0)
            created_at = s.get("created_at")

            # Status icon
            status_icon = {
                "completed": "🟢",
                "running": "🔵",
                "failed": "🔴",
                }.get(pipeline_status, "⚪")

            # Format timestamp
            import datetime as _dt


            if created_at:
                try:
                    ts = _dt.datetime.fromtimestamp(created_at).strftime("%b %d, %Y %H:%M")
                except Exception:
                    ts = "Unknown time"
            else:
                ts = "Unknown time"

            stages_done = len(completed_stgs)
            stages_total = 4

            with st.expander(
                    f"{status_icon} {approach_s} — {ts}",
                    expanded=False,
                    ):
                col_info, col_actions = st.columns([3, 1])
                with col_info:
                    st.markdown(
                        f'<div class="session-chip">{sid[:12]}…</div>',
                        unsafe_allow_html=True,
                        )
                    if req_preview:
                        st.caption(f"*{req_preview[:120]}{'…' if len(req_preview) > 120 else ''}*")
                    st.caption(
                        f"Status: **{pipeline_status}** · "
                        f"Stages: {stages_done}/{stages_total} · "
                        f"Scenes: {total_scn}",
                        )
                    if completed_stgs:
                        st.caption("Completed: " + " → ".join(completed_stgs))

                with col_actions:
                    # Load session into Generate tab for viewing
                    if st.button("View", key=f"view_{sid}", use_container_width=True):
                        st.session_state.session_id = sid
                        st.session_state.pipeline_status = pipeline_status
                        st.session_state.stages = []
                        st.session_state.outline = None
                        st.session_state.scenes = None
                        st.session_state.scene_progress = None
                        st.session_state.auto_poll = False
                        _refresh_all(sid)
                        st.rerun()

                    # Resume button (only for failed/incomplete sessions)
                    can_resume = (
                            pipeline_status in ("failed", "running")
                            and stages_done > 0
                    )
                    if can_resume:
                        if st.button("Resume", key=f"resume_{sid}", use_container_width=True):
                            try:
                                result = _post_resume(sid)
                                st.session_state.session_id = sid
                                st.session_state.pipeline_status = "running"
                                st.session_state.stages = []
                                st.session_state.outline = None
                                st.session_state.scenes = None
                                st.session_state.scene_progress = None
                                st.session_state.auto_poll = True
                                st.session_state.generate_error = None
                                st.success(f"Resuming from {result.get('resumed_from', 'last stage')}…")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Resume failed: {exc}")

                # Inline artifact list
                store_artifacts = _fetch_artifacts(sid)
                if store_artifacts:
                    st.caption(f"{len(store_artifacts)} artifact(s) stored")
                    for art in store_artifacts:
                        atype = art["artifact_type"]
                        label = art["label"]
                        size_kb = art["size_bytes"] / 1024
                        with st.expander(f"  {label} ({size_kb:.1f} KB)", expanded=False):
                            data = _fetch_artifact(sid, atype)
                            if data:
                                json_str = json.dumps(data, indent=2)
                                st.code(json_str[:4000], language="json")
                                if len(json_str) > 4000:
                                    st.caption(f"…truncated to 4 KB")
                                st.download_button(
                                    f"Download {label}",
                                    data=json_str,
                                    file_name=f"{atype}.json",
                                    mime="application/json",
                                    key=f"dl_{sid}_{atype}",
                                    )

# ── Auto-polling ──────────────────────────────────────────────────────────────

TERMINAL = {"completed", "failed"}

if (
        st.session_state.auto_poll
        and st.session_state.session_id
        and st.session_state.pipeline_status not in TERMINAL
):
    time.sleep(POLL_INTERVAL_S)
    _refresh_all(st.session_state.session_id)
    if st.session_state.pipeline_status in TERMINAL:
        st.session_state.auto_poll = False
    st.rerun()
