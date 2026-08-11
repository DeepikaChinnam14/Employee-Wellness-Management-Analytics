"""
components/journal.py

Premium "Journal" section for MoodMentor, matching the reference design:
a "write your entry" card with AI mood analysis, a file-upload card, and a
styled past-entries list.

IMPORTANT: UI ONLY. Every backend call (POST /analyze-text, POST /analyze),
every db call (save_mood_log, get_user_mood_history), and every condition
is copied verbatim from the original inline "Journal" branch in app.py.
Only the layout/markup changed.

One small, disclosed UX choice: the reference screenshot shows no visible
"confirm" button for the file-upload flow (just a dropzone). The original
code required an explicit "Run NLP Analysis on file" click after choosing
a file. I kept that explicit confirm step rather than silently changing
behavior to auto-analyze on upload -- flagging this in case you'd prefer
the auto-trigger version instead.

Usage in app.py (replaces the original `elif section == "Journal": ...` body):

    from components.journal import render_journal_section
    ...
    elif section == "Journal":
        render_journal_section(user, st.session_state.token)
"""

import base64
import os
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

from db import MOOD_EMOJI, get_user_mood_history, save_mood_log

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

MOOD_STYLE = {
    "Happy":   {"emoji": MOOD_EMOJI["Happy"],   "color": "#2ecc71"},
    "Neutral": {"emoji": MOOD_EMOJI["Neutral"], "color": "#3498db"},
    "Sad":     {"emoji": MOOD_EMOJI["Sad"],     "color": "#e67e22"},
    "Stress":  {"emoji": MOOD_EMOJI["Stress"],  "color": "#f1c40f"},
    "Angry":   {"emoji": MOOD_EMOJI["Angry"],   "color": "#e74c3c"},
    "Fear":    {"emoji": MOOD_EMOJI["Fear"],    "color": "#9b59b6"},
}


def _style_for(label):
    return MOOD_STYLE.get(label, {"emoji": "", "color": "#bdbdbd"})


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


def _img_or_emoji_html(rel_path: tuple, emoji_fallback: str, css_class: str, width_px: int = 90) -> str:
    """Use a generated illustration if present, else fall back to an emoji.

    width_px is applied as both an inline attribute AND via CSS class, so
    the image is capped at a sane size even if the stylesheet fails to
    load for any reason -- it won't render at native (huge) resolution.
    """
    path = _resolve_first(rel_path)
    b64 = _get_base64_of_file(str(path))
    if b64:
        return (
            f'<img src="data:image/png;base64,{b64}" class="{css_class}" '
            f'width="{width_px}" style="width:{width_px}px;height:auto;" alt="" />'
        )
    return f'<div class="{css_class} {css_class}--emoji">{emoji_fallback}</div>'


def _render_page_header() -> None:
    now = datetime.now()
    st.markdown(
        f"""
        <div class="mm-page-header">
            <div>
                <h1 class="mm-page-title">Journal</h1>
                <p class="mm-page-subtitle">A safe space to reflect and express yourself 💜</p>
            </div>
            <div class="mm-home-datetime">
                📅 {now.strftime('%A, %-d %B %Y')} &nbsp;|&nbsp; 🕐 {now.strftime('%I:%M %p')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_analysis_result(r: dict) -> None:
    confidence = r.get("emotion_confidence")
    conf_str = f", Confidence: **{confidence:.0%}**" if confidence is not None else ""
    st.success(f"Saved! Sentiment: **{r['final_sentiment']}**, "
               f"Emotion: **{r['final_emotion']}**{conf_str}")
    st.bar_chart(r["emotion_scores"])
    if r.get("recommendation"):
        st.info(f"**Recommendation:** {r['recommendation']}")


def render_journal_section(user: dict, token: str, debug: bool = True) -> None:
    """Render the Journal section. Identical backend calls/db calls to the
    original inline `elif section == "Journal":` block -- only the
    layout/markup is new.

    `debug=True` (default) shows a warning if dashboard.css can't be found,
    since this page's card/illustration styling depends entirely on it
    (loaded once via render_sidebar(), which runs before this on every
    authenticated page).
    """

    if debug:
        css_path = _resolve_first(
            ("styles", "dashboard.css"),
            ("assets", "styles", "dashboard.css"),
            ("assets", "css", "dashboard.css"),
        )
        if not css_path.exists():
            st.warning(
                "dashboard.css not found -- Journal page will look "
                f"unstyled. Checked: `{css_path}` (and sibling candidate roots)."
            )

    headers = {"Authorization": f"Bearer {token}"}

    _render_page_header()

    # -------------------------------------------------------------- #
    # Write & analyze card
    # -------------------------------------------------------------- #
    book_html = _img_or_emoji_html(
        ("assets", "illustrations", "journal-book.png"), "📔", "mm-journal-illustration"
    )
    with st.container(border=True):
        st.markdown('<div class="mm-write-card-marker"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="mm-card-header-row">
                <div class="mm-card-icon">📝</div>
                <div>
                    <div class="mm-card-title">Write about how you're feeling today</div>
                    <div class="mm-card-subtitle">Let your thoughts flow freely. This is your space.</div>
                </div>
                {book_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        journal_text = st.text_area(
            "Write about how you're feeling today", height=150,
            placeholder="Your note here...", label_visibility="collapsed",
            max_chars=2000, key="journal_text_input",
        )
        st.markdown(
            f'<div class="mm-char-counter">{len(journal_text)} / 2000</div>',
            unsafe_allow_html=True,
        )

        analyze_clicked = st.button("✨  Analyze my mood", key="journal_analyze_btn")
        st.markdown(
            '<p class="mm-card-hint">Get AI insights about your current mood</p>',
            unsafe_allow_html=True,
        )

        if analyze_clicked:
            if not journal_text.strip():
                st.warning("Write something first.")
            else:
                with st.spinner("Running NLP analysis…"):
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/analyze-text",
                            json={"text": journal_text},
                            headers=headers, timeout=120,
                        )
                    except requests.exceptions.RequestException as e:
                        st.error(f"Could not reach backend: {e}")
                        resp = None
                if resp is not None:
                    if resp.status_code != 200:
                        st.error("Analysis failed.")
                    else:
                        r = resp.json()
                        save_mood_log(
                            user["id"], r["final_sentiment"], r["final_emotion"],
                            r["sentiment_scores"]["compound"], journal_text,
                            confidence=r.get("emotion_confidence"),
                        )
                        _render_analysis_result(r)

    st.markdown('<div class="mm-card-spacer"></div>', unsafe_allow_html=True)

    # -------------------------------------------------------------- #
    # File upload card
    # -------------------------------------------------------------- #
    upload_html = _img_or_emoji_html(
        ("assets", "illustrations", "upload-cloud.png"), "☁️", "mm-upload-illustration"
    )
    with st.container(border=True):
        st.markdown('<div class="mm-upload-card-marker"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="mm-card-header-row">
                <div class="mm-card-icon mm-card-icon--teal">📤</div>
                <div>
                    <div class="mm-card-title">Or upload a file</div>
                    <div class="mm-card-subtitle">Upload a CSV or TXT file to analyze your mood data.</div>
                </div>
                {upload_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "Choose a CSV or TXT file", type=["csv", "txt"], label_visibility="collapsed",
        )
        st.markdown(
            '<p class="mm-card-hint">CSV, TXT files only &bull; Max size 200MB</p>',
            unsafe_allow_html=True,
        )

        if uploaded is not None:
            run_clicked = st.button("Run NLP Analysis on file", key="journal_file_analyze_btn")
            if run_clicked:
                files = {"file": (uploaded.name, uploaded.getvalue())}
                with st.spinner("Running multilingual NLP pipeline…"):
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/analyze", files=files, headers=headers, timeout=120,
                        )
                    except requests.exceptions.RequestException as e:
                        st.error(f"Could not reach backend: {e}")
                        resp = None
                if resp is not None:
                    if resp.status_code != 200:
                        st.error("Analysis failed.")
                    else:
                        r = resp.json()
                        save_mood_log(
                            user["id"], r["final_sentiment"], r["final_emotion"],
                            r["sentiment_scores"]["compound"], r.get("cleaned_text", ""),
                            confidence=r.get("emotion_confidence"),
                        )
                        _render_analysis_result(r)

    st.markdown('<div class="mm-card-spacer"></div>', unsafe_allow_html=True)

    # -------------------------------------------------------------- #
    # Past entries
    # -------------------------------------------------------------- #
    st.markdown(
        """
        <div class="mm-section-heading-row">
            <span class="mm-section-heading-icon">🕐</span>
            <span class="mm-section-heading-text">Past entries</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    history = [h for h in get_user_mood_history(user["id"], limit=20) if h["journal_text"]]
    if not history:
        st.caption("No journal entries yet.")
    for h in history:
        s = _style_for(h["sentiment"])
        conf_str = f" · Confidence: {h['confidence']:.0%}" if h.get("confidence") is not None else ""
        with st.expander(
            f"{s['emoji']}  {h['sentiment']} — {h['created_at'].strftime('%Y-%m-%d %H:%M')}{conf_str}"
        ):
            st.write(h["journal_text"])

    st.markdown(
        """
        <div class="mm-page-footer-quote">
            🍃 Small steps every day lead to a better you. Keep going! 💜 🍃
        </div>
        """,
        unsafe_allow_html=True,
    )
