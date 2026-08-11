"""
components/wellness_chat.py

Premium "Wellness Chat" section for MoodMentor, matching the reference
design: an intro card with trust badges, an empty/active chat area, and a
styled chat input bar.

IMPORTANT: UI ONLY. Every backend call (POST /chat), every session_state
key (chat_history), and every condition is copied verbatim from the
original inline "Wellness Chat" branch in app.py. Only the layout/markup
changed.

Deliberately NOT added: a functional paperclip/attachment button. The
reference screenshot shows one, but there's no file-attachment backend
for chat, so a clickable paperclip would imply functionality that doesn't
exist. Left out rather than faked.

Usage in app.py (replaces the original `elif section == "Wellness Chat": ...` body):

    from components.wellness_chat import render_wellness_chat_section
    ...
    elif section == "Wellness Chat":
        render_wellness_chat_section(st.session_state.token)
"""

import base64
import os
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

_THIS_FILE = Path(__file__).resolve()
_CANDIDATE_ROOTS = [_THIS_FILE.parent.parent, Path.cwd(), Path.cwd().parent]


def _resolve_first(*candidate_relative_paths: tuple) -> Path:
    for root in _CANDIDATE_ROOTS:
        for parts in candidate_relative_paths:
            candidate = root.joinpath(*parts)
            if candidate.exists():
                return candidate
    return _CANDIDATE_ROOTS[0].joinpath(*candidate_relative_paths[0])


@st.cache_data(show_spinner=False)
def _get_base64_of_file(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        return ""


def _img_or_emoji_html(rel_path: tuple, emoji_fallback: str, css_class: str, width_px: int) -> str:
    path = _resolve_first(rel_path)
    b64 = _get_base64_of_file(str(path))
    if b64:
        return (
            f'<img src="data:image/png;base64,{b64}" class="{css_class}" '
            f'width="{width_px}" style="width:{width_px}px;height:auto;" alt="" />'
        )
    return f'<div class="{css_class} {css_class}--emoji">{emoji_fallback}</div>'


TRUST_BADGES = [
    {"icon": "🛡️", "title": "Private & Safe", "desc": "Your conversations are confidential"},
    {"icon": "💗", "title": "Non-Judgmental", "desc": "Talk freely without fear of judgment"},
    {"icon": "🌱", "title": "Here to Help", "desc": "I'm here whenever you need to talk"},
]


def _render_page_header() -> None:
    now = datetime.now()
    st.markdown(
        f"""
        <div class="mm-page-header">
            <div>
                <h1 class="mm-page-title">Wellness Chat 💜</h1>
                <p class="mm-page-subtitle">
                    A supportive space to talk about how you're feeling.<br>
                    Not a substitute for professional care.
                </p>
            </div>
            <div class="mm-home-datetime">
                📅 {now.strftime('%A, %-d %B %Y')} &nbsp;|&nbsp; 🕐 {now.strftime('%I:%M %p')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_intro_card() -> None:
    mascot_html = _img_or_emoji_html(
        ("assets", "illustrations", "mentor-brain-mascot.png"), "🧠", "mm-chat-mascot", 140
    )
    badges_html = "".join(
        f"""
        <div class="mm-trust-badge">
            <div class="mm-trust-badge-icon">{b['icon']}</div>
            <div>
                <div class="mm-trust-badge-title">{b['title']}</div>
                <div class="mm-trust-badge-desc">{b['desc']}</div>
            </div>
        </div>
        """
        for b in TRUST_BADGES
    )
    with st.container(border=True):
        st.markdown('<div class="mm-intro-card-marker"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="mm-chat-intro-row">
                {mascot_html}
                <div>
                    <div class="mm-chat-intro-title">Hi there! I'm MoodMentor 👋</div>
                    <div class="mm-chat-intro-desc">
                        I'm here to listen and support you.<br>
                        Share what's on your mind &mdash; big or small.
                    </div>
                </div>
            </div>
            <div class="mm-trust-badge-row">{badges_html}</div>
            """,
            unsafe_allow_html=True,
        )


def _render_empty_state() -> None:
    bubbles_html = _img_or_emoji_html(
        ("assets", "illustrations", "chat-bubbles.png"), "💬", "mm-chat-empty-illustration", 160
    )
    st.markdown(
        f"""
        <div class="mm-chat-empty-state">
            {bubbles_html}
            <div class="mm-chat-empty-title">Let's start a conversation</div>
            <div class="mm-chat-empty-desc">
                Share how you're feeling today.<br>I'm here to listen.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_wellness_chat_section(token: str, debug: bool = True) -> None:
    """Render the Wellness Chat section. Identical backend calls/session
    state to the original inline `elif section == "Wellness Chat":` block
    -- only the layout/markup is new.

    `debug=True` (default) shows a warning if dashboard.css can't be found.
    """
    if debug:
        css_path = _resolve_first(
            ("styles", "dashboard.css"),
            ("assets", "styles", "dashboard.css"),
            ("assets", "css", "dashboard.css"),
        )
        if not css_path.exists():
            st.warning(
                "dashboard.css not found -- Wellness Chat page will look "
                f"unstyled. Checked: `{css_path}` (and sibling candidate roots)."
            )

    headers = {"Authorization": f"Bearer {token}"}

    _render_page_header()
    _render_intro_card()

    with st.container(border=True):
        st.markdown('<div class="mm-chat-area-marker"></div>', unsafe_allow_html=True)

        if not st.session_state.chat_history:
            _render_empty_state()
        else:
            top_l, top_r = st.columns([5, 1])
            with top_r:
                if st.button("Clear chat", key="wellness_clear_chat_btn"):
                    st.session_state.chat_history = []
                    st.rerun()

            chat_box = st.container(height=380)
            with chat_box:
                for turn in st.session_state.chat_history:
                    with st.chat_message(turn["role"]):
                        st.write(turn["content"])

    user_msg = st.chat_input("How are you feeling today?")
    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        recent_history = st.session_state.chat_history[-10:-1]
        try:
            resp = requests.post(
                f"{BACKEND_URL}/chat",
                json={"message": user_msg, "history": recent_history},
                headers=headers, timeout=60,
            )
            reply = resp.json()["reply"] if resp.status_code == 200 else \
                "Sorry, I couldn't reach the wellness assistant right now."
        except requests.exceptions.RequestException:
            reply = "Sorry, I couldn't reach the wellness assistant right now."
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()
