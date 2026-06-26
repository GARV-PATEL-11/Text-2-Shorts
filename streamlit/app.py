"""
Text-2-Shorts — Streamlit UI
"""

from __future__ import annotations

import json
import uuid

import requests
import streamlit.components.v1 as components

import streamlit as st


API_BASE = "http://localhost:8000"

APPROACHES = [
    "Classic Linear Narrative",
    "Conceptual Zoom",
    "Problem-Solution Arc",
    ]

STAGE_ICONS: dict[str, str] = {
    "Queued": "🔵",
    "Generating Outline": "🟡",
    "Mapping Outline": "🟡",
    "Generating Visual Plan": "🟡",
    "Completed": "🟢",
    "Failed": "🔴",
    }

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Text-2-Shorts",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed",
    )

# ── Minimal styling ───────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
        /* Remove top padding */
        .block-container { padding-top: 2rem; }

        /* Monospace IDs */
        code { font-size: 0.85rem; }

        /* Status row spacing */
        .status-line { margin: 0.15rem 0; font-size: 0.95rem; }

        /* Disable animation on spinner */
        div[data-testid="stSpinner"] { animation: none; }

        /* Scrollable outline container */
        .outline-scroll-box {
            max-height: 520px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 4px 0;
            background: #0e1117;
        }
        .outline-scroll-box pre {
            margin: 0;
            padding: 12px 16px;
            font-size: 0.82rem;
            line-height: 1.5;
            white-space: pre;
            overflow-x: auto;
        }
    </style>
    """,
    unsafe_allow_html=True,
    )

# ── Session state defaults ────────────────────────────────────────────────────

_defaults: dict = {
    "session_id": None,
    "workflow_id": None,
    "status_data": None,
    "show_outline": False,
    "generate_error": None,
    "status_error": None,
    }
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helpers ───────────────────────────────────────────────────────────────────

def _post_generate(requirement: str, approach: str) -> dict:
    session_id = uuid.uuid4().hex
    resp = requests.post(
        f"{API_BASE}/generate",
        json={
            "requirement": requirement,
            "approach": approach,
            "session_id": session_id,
            },
        timeout=15,
        )
    resp.raise_for_status()
    return resp.json()


def _get_status(session_id: str) -> dict:
    resp = requests.get(f"{API_BASE}/status/{session_id}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def _copy_button(text: str) -> None:
    """Render an HTML/JS clipboard button."""
    safe = json.dumps(text)  # valid JS string literal, handles all escaping
    components.html(
        f"""
        <button id="cpBtn"
            onclick="navigator.clipboard.writeText({safe})
                .then(()=>{{
                    var b=document.getElementById('cpBtn');
                    b.textContent='✓ Copied';
                    setTimeout(()=>b.textContent='Copy JSON',2000);
                }})
                .catch(()=>alert('Clipboard unavailable — use the copy icon above the code block'));"
            style="cursor:pointer;padding:6px 18px;border:1px solid #d0d0d0;
                   border-radius:4px;background:#fff;font-size:13px;
                   font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
            Copy JSON
        </button>
        """,
        height=42,
        )


# ── Dialog: outline viewer ────────────────────────────────────────────────────

@st.dialog("Video Outline", width="large")
def _outline_dialog() -> None:
    data = st.session_state.status_data or {}
    outline = data.get("outline")

    if not outline:
        st.warning("Outline not available yet.")
    else:
        outline_type = data.get("outline_type", "")
        if outline_type:
            st.caption(f"Approach: **{outline_type}**")

        json_str = json.dumps(outline, indent=2)

        # Read-only code viewer with built-in copy icon
        st.code(json_str, language="json")

        # Explicit Copy JSON button + Download
        col_copy, col_dl, col_close = st.columns([1.4, 1.4, 1])
        with col_copy:
            _copy_button(json_str)
        with col_dl:
            st.download_button(
                "Download JSON",
                data=json_str,
                file_name="outline.json",
                mime="application/json",
                use_container_width=True,
                )
        with col_close:
            if st.button("Close", use_container_width=True):
                st.session_state.show_outline = False
                st.rerun()
        return

    if st.button("Close"):
        st.session_state.show_outline = False
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────

st.title("Text-2-Shorts")
st.caption("Generate structured educational video outlines from a plain-text requirement.")

st.divider()

# ── Input form ────────────────────────────────────────────────────────────────

requirement = st.text_area(
    "Video Requirement",
    placeholder="Describe the educational topic you want to cover…",
    height=130,
    help="Be specific about the concept, target audience, and any constraints.",
    )

approach = st.selectbox(
    "Narrative Approach",
    options=APPROACHES,
    help="Determines the outline structure the LLM will follow.",
    )

generate_clicked = st.button(
    "Generate",
    type="primary",
    disabled=not requirement.strip(),
    use_container_width=False,
    )

if generate_clicked:
    st.session_state.generate_error = None
    st.session_state.status_data = None
    st.session_state.show_outline = False
    with st.spinner("Starting pipeline…"):
        try:
            data = _post_generate(requirement.strip(), approach)
            st.session_state.session_id = data.get("session_id")
            st.session_state.workflow_id = data.get("workflow_id")
        except requests.HTTPError as exc:
            st.session_state.generate_error = f"API error {exc.response.status_code}: {exc.response.text}"
        except Exception as exc:
            st.session_state.generate_error = str(exc)

if st.session_state.generate_error:
    st.error(st.session_state.generate_error)

# ── Results section ───────────────────────────────────────────────────────────

if st.session_state.session_id:
    st.divider()

    # IDs
    st.markdown(f"**Session ID** &nbsp; `{st.session_state.session_id}`", unsafe_allow_html=True)
    if st.session_state.workflow_id:
        st.markdown(f"**Workflow ID** &nbsp; `{st.session_state.workflow_id}`", unsafe_allow_html=True)

    st.write("")  # spacing

    # Action buttons
    outline_ready = bool(
        st.session_state.status_data
        and st.session_state.status_data.get("outline"),
        )

    col_check, col_outline, _ = st.columns([1.2, 1.2, 2])
    with col_check:
        check_clicked = st.button("Check Status", use_container_width=True)
    with col_outline:
        outline_clicked = st.button(
            "View Outline",
            disabled=not outline_ready,
            use_container_width=True,
            )

    if check_clicked:
        st.session_state.status_error = None
        with st.spinner("Fetching status…"):
            try:
                st.session_state.status_data = _get_status(st.session_state.session_id)
            except requests.HTTPError as exc:
                st.session_state.status_error = f"API error {exc.response.status_code}: {exc.response.text}"
            except Exception as exc:
                st.session_state.status_error = str(exc)

    if outline_clicked:
        st.session_state.show_outline = True

    # Status error
    if st.session_state.status_error:
        st.error(st.session_state.status_error)

    # Status display
    if st.session_state.status_data:
        data = st.session_state.status_data
        stage = data.get("stage", "Unknown")
        icon = STAGE_ICONS.get(stage, "⚪")

        st.write("")
        st.markdown(f"**Status** &nbsp; {icon} {stage}", unsafe_allow_html=True)

        if data.get("outline_type"):
            st.markdown(
                f"**Approach** &nbsp; {data['outline_type']}",
                unsafe_allow_html=True,
                )
        if data.get("total_scenes"):
            st.markdown(
                f"**Scenes** &nbsp; {data['total_scenes']}",
                unsafe_allow_html=True,
                )
        if data.get("error"):
            st.error(f"Pipeline error: {data['error']}")

        # ── Inline outline display ─────────────────────────────────────────────
        if data.get("outline"):
            st.write("")
            st.subheader("Generated Outline")
            if data.get("outline_type"):
                st.caption(f"Approach: **{data['outline_type']}**")

            json_str = json.dumps(data["outline"], indent=2)

            # Scrollable code block via HTML wrapper
            import html as _html


            escaped = _html.escape(json_str)
            st.markdown(
                f'<div class="outline-scroll-box"><pre><code>{escaped}</code></pre></div>',
                unsafe_allow_html=True,
                )
            st.write("")

            col_copy2, col_dl2, _ = st.columns([1.2, 1.2, 2])
            with col_copy2:
                _copy_button(json_str)
            with col_dl2:
                st.download_button(
                    "Download JSON",
                    data=json_str,
                    file_name="outline.json",
                    mime="application/json",
                    use_container_width=True,
                    key="dl_inline",
                    )

# ── Outline dialog ────────────────────────────────────────────────────────────

if st.session_state.show_outline:
    _outline_dialog()
