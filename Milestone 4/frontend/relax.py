"""
components/relax.py

Premium "Relax & Recharge" section for MoodMentor.

IMPORTANT: UI ONLY for the core logic. The breathing circle markup and the
mood-based Spotify playlist selection are functionally identical to the
original inline "Relax" branch in app.py -- same three playlist IDs, same
mood-to-playlist mapping, same components.iframe() call.

ONE REAL ADDITION (not fabricated, agreed with you): the playlists that
were previously only auto-selected by mood are now also directly
selectable via "Play Music" (calming) / "Explore Sounds" (lo-fi, reused
for "Nature Sounds") buttons. If the user hasn't clicked either, behavior
is 100% identical to the original -- auto-picks by last mood, same
messaging. Nothing about the original behavior was removed or changed,
only added to.

NOT included, by final decision: "Mood Boost Activities" and
"Recommended for You" sections were built, previewed, then intentionally
removed -- they had no backend behind them and would have looked
clickable without doing anything, which erodes trust. Better to ship
only what's real.

Usage in app.py (replaces the original `elif section == "Relax": ...` body):

    from components.relax import render_relax_section
    ...
    elif section == "Relax":
        render_relax_section(user)
"""

import base64
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from db import get_user_mood_history

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


# The exact three playlist IDs from your original code -- unchanged.
_PLAYLISTS = {
    "calm":   "https://open.spotify.com/embed/playlist/37i9dQZF1DWZqd5JICZI0u?utm_source=generator",
    "upbeat": "https://open.spotify.com/embed/playlist/37i9dQZF1DXcBWIGoYBM5M?utm_source=generator",
    "lofi":   "https://open.spotify.com/embed/playlist/37i9dQZF1DWWQRwui0ExPn?utm_source=generator",
}


def _render_page_header() -> None:
    now = datetime.now()
    st.markdown(
        f"""
        <div class="mm-page-header">
            <div>
                <h1 class="mm-page-title">🌿 Relax &amp; Recharge</h1>
                <p class="mm-page-subtitle">Take a deep breath, relax your mind, and reset your mood.</p>
            </div>
            <div class="mm-home-datetime">
                📅 {now.strftime('%A, %-d %B %Y')} &nbsp;|&nbsp; 🕐 {now.strftime('%I:%M %p')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_top_cards() -> None:
    """Guided Breathing anchors to the real breathing section below.
    Calming/Upbeat/Nature Sounds Music buttons set a session_state override
    read by _render_music_section() -- Nature Sounds reuses the existing
    lo-fi playlist (closest honest match; no new playlist link invented)."""
    st.markdown(
        """
        <div class="mm-relax-top-row">
            <div class="mm-relax-card mm-relax-card--purple">
                <div class="mm-relax-card-title">Guided Breathing</div>
                <div class="mm-relax-card-desc">Calm your mind with soothing breathing exercises.</div>
                <a href="#mm-breathing-section" class="mm-relax-card-btn">🌬️ Start Breathing</a>
            </div>
            <div class="mm-relax-card mm-relax-card--blue">
                <div class="mm-relax-card-title">Calming Music</div>
                <div class="mm-relax-card-desc">Listen to relaxing sounds and healing melodies.</div>
            </div>
            <div class="mm-relax-card mm-relax-card--green">
                <div class="mm-relax-card-title">Nature Sounds</div>
                <div class="mm-relax-card-desc">Immerse yourself in the sounds of nature.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, c2, c3 = st.columns([1, 1, 1])
    with c2:
        with st.container():
            st.markdown('<div class="mm-relax-btn-marker mm-relax-btn-marker--blue"></div>', unsafe_allow_html=True)
            if st.button("🎵  Play Music", key="relax_play_calm_btn", use_container_width=True):
                st.session_state.relax_playlist_override = "calm"
                st.rerun()
    with c3:
        with st.container():
            st.markdown('<div class="mm-relax-btn-marker mm-relax-btn-marker--green"></div>', unsafe_allow_html=True)
            if st.button("🌿  Explore Sounds", key="relax_play_nature_btn", use_container_width=True):
                st.session_state.relax_playlist_override = "lofi"
                st.rerun()


def _render_music_section(user: dict) -> None:
    st.markdown('<div class="mm-section-heading-row" id="mm-music-section">'
                '<span class="mm-section-heading-icon">🎵</span>'
                '<span class="mm-section-heading-text">Therapy Recommendations</span></div>',
                unsafe_allow_html=True)

    override = st.session_state.get("relax_playlist_override")

    if override:
        # User explicitly picked a playlist -- honor that choice.
        playlist_key = override
        label = "Calming acoustic playlist" if override == "calm" else "Upbeat playlist"
        st.info(f"**Playing:** {label} (your choice). "
                f"[Reset to auto-recommendation](#mm-music-section)")
        if st.button("↺  Back to mood-based recommendation", key="relax_reset_override_btn"):
            st.session_state.relax_playlist_override = None
            st.rerun()
    else:
        # EXACT original logic: auto-pick by last mood entry.
        history = get_user_mood_history(user["id"], limit=1)
        last_mood = history[0]["sentiment"] if history else "Normal"

        if last_mood in ["Sad", "Angry", "Stress", "Fear"]:
            st.warning(f"**Mentor's Advice:** Since your last entry showed you were feeling "
                       f"**{last_mood}**, I recommend 5 minutes of mindful breathing before your "
                       f"next meeting. Listen to this calming acoustic playlist to help you center yourself.")
            playlist_key = "calm"
        elif last_mood in ["Happy", "Amazing"]:
            st.success(f"**Mentor's Advice:** Since your last entry showed you were feeling "
                       f"**{last_mood}**, keep that incredible momentum going! This upbeat playlist "
                       f"is perfect while you work.")
            playlist_key = "upbeat"
        else:
            st.info(f"**Mentor's Advice:** You've been feeling **{last_mood}**. To help you find "
                    f"your flow and stay centered today, try this Lo-Fi Beats playlist.")
            playlist_key = "lofi"

    with st.container(border=True):
        st.markdown('<div class="mm-music-card-marker"></div>', unsafe_allow_html=True)
        components.iframe(_PLAYLISTS[playlist_key], width=300, height=352, scrolling=False)


def _render_breathing_section() -> None:
    st.markdown('<div id="mm-breathing-section"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('<div class="mm-breathing-card-marker"></div>', unsafe_allow_html=True)
        breath_img_html = _img_or_emoji_html(
            ("assets", "illustrations", "breathing-woman.png"), "🧘‍♀️", "mm-breathing-illustration", 130
        )
        st.markdown(
            f"""
            <div class="mm-breathing-row">
                <div>
                    <div class="mm-card-title">🌬️ Guided Breathing</div>
                    <div class="mm-card-subtitle">
                        Follow the circle. Breathe in as it expands, hold, and breathe out as it shrinks.
                    </div>
                    <div class="breathing-container">
                        <div class="circle">Breathe</div>
                    </div>
                </div>
                {breath_img_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info("💡 **Mentor's Tip:** This 4-7-8 breathing technique activates your parasympathetic "
                "nervous system, reducing anxiety in just 60 seconds.")


def _render_footer_quote() -> None:
    cup_html = _img_or_emoji_html(
        ("assets", "illustrations", "relax-quote-cup.png"), "☕", "mm-relax-quote-illustration", 90
    )
    st.markdown(
        f"""
        <div class="mm-relax-quote-card">
            <div class="mm-relax-quote-text">
                "You deserve this moment. You matter. Take care of your mind,
                just like you take care of everything else."
            </div>
            {cup_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_relax_section(user: dict, debug: bool = True) -> None:
    """Render the Relax section. Breathing markup and Spotify playlist
    selection logic are functionally identical to the original inline
    `elif section == "Relax":` block -- only layout/markup changed, plus
    one disclosed additive feature (manual playlist choice)."""

    if "relax_playlist_override" not in st.session_state:
        st.session_state.relax_playlist_override = None

    if debug:
        css_path = _resolve_first(
            ("styles", "dashboard.css"),
            ("assets", "styles", "dashboard.css"),
            ("assets", "css", "dashboard.css"),
        )
        if css_path.exists():
            st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
        else:
            st.warning(
                "dashboard.css not found -- Relax page will look unstyled. "
                f"Checked: `{css_path}` (and sibling candidate roots)."
            )

    _render_page_header()
    _render_top_cards()

    left, right = st.columns([1, 1], gap="large")
    with left:
        _render_breathing_section()
    with right:
        _render_music_section(user)

    _render_footer_quote()
