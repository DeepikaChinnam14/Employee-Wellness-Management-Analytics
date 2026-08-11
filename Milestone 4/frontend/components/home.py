"""
components/home.py

Premium "Home" dashboard section for MoodMentor, matching the reference
design: metric cards, mood picker, calendar, and a right-hand info column.

IMPORTANT: UI ONLY for the core dashboard (metrics/mood-picker/calendar) --
every db call, every session_state key (picked_mood, today_mood_saved,
cal_year, cal_month), and every condition is copied verbatim from the
original inline Home section in app.py.

The right-hand column (Daily Affirmation, Take a Breath, Insights, Tip of
the Day) is NEW and not from the original code, scoped exactly as agreed:
    - Daily Affirmation: decorative only (static rotating quote)
    - Take a Breath: REAL -- switches st.session_state.nav to "Relax"
      (your actual Relax section) and reruns, same mechanism the app
      already uses elsewhere
    - Insights: decorative only (no fabricated data claims)
    - Tip of the Day: decorative only (static rotating tip)

Usage in app.py (replaces the original `if section == "Home": ...` body):

    from components.home import render_home_section
    ...
    if section == "Home":
        render_home_section(user)
"""

import base64
import calendar
from datetime import date, datetime
from pathlib import Path

import streamlit as st

from db import MOOD_LABELS, MOOD_EMOJI, get_mood_logs_for_month, get_user_mood_history, save_manual_mood

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


# --------------------------------------------------------------------------- #
# Duplicated (not imported) from app.py to avoid a circular import --
# app.py imports this module, so this module can't import back from app.py.
# Keep these in sync with app.py's MOOD_STYLE if you change mood colors.
# --------------------------------------------------------------------------- #

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


# --------------------------------------------------------------------------- #
# Decorative-only static content (clearly not derived from real data)
# --------------------------------------------------------------------------- #

_AFFIRMATIONS = [
    "You are stronger than you think and braver than you feel.",
    "Every feeling is valid. Every day is a new beginning.",
    "Small steps still move you forward.",
    "You don't have to be perfect to be proud of yourself.",
    "Rest is productive too.",
    "Your feelings are data, not a verdict.",
    "Progress, not perfection.",
]

_TIPS = [
    "Go for a short walk in nature. It boosts your mood instantly.",
    "Drink a glass of water and stretch for 60 seconds.",
    "Write down one thing you're grateful for today.",
    "Step away from your screen for 5 minutes.",
    "Send a kind message to someone you appreciate.",
    "Take three slow, deep breaths before your next meeting.",
]


def _pick_of_the_day(options: list) -> str:
    """Deterministic per-day rotation -- same value all day, changes daily."""
    idx = date.today().toordinal() % len(options)
    return options[idx]


# --------------------------------------------------------------------------- #
# Metric tile
# --------------------------------------------------------------------------- #

def _metric_tile(label: str, icon: str, value: str, sub: str, accent: str) -> None:
    st.markdown(
        f"""
        <div class="mm-home-metric" style="--accent:{accent}">
            <div class="mm-home-metric-label">{label}</div>
            <div class="mm-home-metric-row">
                <div class="mm-home-metric-icon">{icon}</div>
                <div>
                    <div class="mm-home-metric-value">{value}</div>
                    <div class="mm-home-metric-sub">{sub}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Right column (decorative + one real feature)
# --------------------------------------------------------------------------- #

def _render_right_column() -> None:
    quote = _pick_of_the_day(_AFFIRMATIONS)
    tip = _pick_of_the_day(_TIPS)

    bg_path = _resolve_first(
        ("assets", "backgrounds", "affirmation-bg.png"),
        ("assets", "backgrounds", "background.png"),
    )
    bg_b64 = _get_base64_of_file(str(bg_path))
    bg_style = (
        f'background-image: linear-gradient(180deg, rgba(91,79,196,0.25) 0%, rgba(60,45,140,0.65) 100%), '
        f'url("data:image/png;base64,{bg_b64}"); background-size: cover; background-position: center;'
        if bg_b64 else ""
    )

    st.markdown(
        f"""
        <div class="mm-home-side-card mm-home-affirmation" style='{bg_style}'>
            <div class="mm-home-side-title">💬 Daily Affirmation</div>
            <div class="mm-home-affirmation-text">&ldquo;{quote}&rdquo;</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    breath_img_path = _resolve_first(("assets", "illustrations", "breathing-woman.png"))
    breath_img_b64 = _get_base64_of_file(str(breath_img_path))
    if breath_img_b64:
        breath_illustration_html = (
            f'<img src="data:image/png;base64,{breath_img_b64}" '
            f'class="mm-home-breath-img" alt="Meditation illustration" />'
        )
    else:
        breath_illustration_html = '<div class="mm-home-breath-illustration">🧘‍♀️</div>'

    st.markdown(
        f"""
        <div class="mm-home-side-card mm-home-breath-card">
            <div class="mm-home-side-title">🌬️ Take a Breath</div>
            <div class="mm-home-breath-row">
                <div class="mm-home-side-desc">Take a 2-minute mindful breathing break.</div>
                {breath_illustration_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("▶  Start Breathing", key="home_start_breathing_btn", use_container_width=True):
        st.session_state.nav = "Relax"
        st.rerun()

    st.markdown(
        """
        <div class="mm-home-side-card">
            <div class="mm-home-side-title">📈 Insights</div>
            <div class="mm-home-side-desc">Check your Dashboard tab for mood trends and detailed analytics.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="mm-home-side-card mm-home-tip-card">
            <div class="mm-home-side-title">💡 Tip of the Day</div>
            <div class="mm-home-side-desc">{tip}</div>
            <div class="mm-home-tip-leaf">🌿</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

def render_home_section(user: dict) -> None:
    """Render the Home dashboard. Identical data/logic to the original
    inline `if section == "Home":` block -- only the layout/markup and the
    (clearly-scoped) right column are new."""

    greeting = "Good Morning" if datetime.now().hour < 12 else (
        "Good Afternoon" if datetime.now().hour < 18 else "Good Evening")
    now = datetime.now()

    _bird_svg = (
        '<svg viewBox="0 0 24 12" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M1 9 Q6 1 12 9 Q18 1 23 9" stroke="#7c6fe8" stroke-width="2" '
        'fill="none" stroke-linecap="round"/></svg>'
    )
    st.markdown(
        f"""
        <div class="mm-home-decor mm-home-decor--branch">🍃🌿🍃</div>
        <div class="mm-home-decor mm-home-decor--bird1">{_bird_svg}</div>
        <div class="mm-home-decor mm-home-decor--bird2">{_bird_svg}</div>
        <div class="mm-home-decor mm-home-decor--bird3">{_bird_svg}</div>
        <div class="mm-home-decor mm-home-decor--floral">🌸🌷🌼</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="mm-home-header">
            <div>
                <h2 class="mm-home-greeting">{greeting}, <span>{user['username']}</span>!</h2>
                <p class="mm-home-subgreeting">Every feeling is valid. Every day is a new beginning. 💜</p>
            </div>
            <div class="mm-home-datetime">
                📅 {now.strftime('%A, %-d %B %Y')} &nbsp;|&nbsp; 🕐 {now.strftime('%I:%M %p')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    main_col, side_col = st.columns([2.3, 1], gap="large")

    with main_col:
        history_all = get_user_mood_history(user["id"], limit=500)
        latest = history_all[0] if history_all else None
        today_count = sum(1 for h in history_all if h["mood_date"] == date.today())
        streak = 0
        day_ptr = date.today()
        day_set = {h["mood_date"] for h in history_all}
        while day_ptr in day_set:
            streak += 1
            day_ptr = date.fromordinal(day_ptr.toordinal() - 1)

        positive_count = sum(1 for h in history_all if h["sentiment"] == "Happy")
        overall_score = int(100 * positive_count / len(history_all)) if history_all else 0

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            if latest:
                s = _style_for(latest["sentiment"])
                _metric_tile("CURRENT MOOD", s["emoji"], latest["sentiment"], "Keep shining!", s["color"])
            else:
                _metric_tile("CURRENT MOOD", "—", "No data", "Pick a mood below", "#bdbdbd")
        with m2:
            _metric_tile(
                "OVERALL SCORE", "📊", f"{overall_score}%",
                "You're improving!" if overall_score >= 50 else "Needs care",
                "#2ecc71" if overall_score >= 50 else "#e67e22",
            )
        with m3:
            _metric_tile("ENTRIES TODAY", "📝", str(today_count), "Keep it up!", "#7c6fe8")
        with m4:
            _metric_tile("CURRENT STREAK", "🔥", f"{streak} Days", "Great consistency!", "#f1a33d")

        st.markdown('<div class="mm-home-section-gap"></div>', unsafe_allow_html=True)
        st.markdown('<h3 class="mm-home-section-title">How Do You Feel Today?</h3>', unsafe_allow_html=True)
        st.caption("Select your current mood")

        cols = st.columns(len(MOOD_LABELS))
        picked = st.session_state.get("picked_mood")
        for col, label in zip(cols, MOOD_LABELS):
            s = _style_for(label)
            is_picked = picked == label
            with col:
                st.markdown(
                    f"""
                    <div class="mm-mood-card {'mm-mood-card--active' if is_picked else ''}" style="--mood-color:{s['color']}">
                        <div class="mm-mood-emoji">{s['emoji']}</div>
                        <div class="mm-mood-label">{label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Select", key=f"pick_{label}", use_container_width=True, help=f"Select {label}"):
                    st.session_state.picked_mood = label
                    st.rerun()

        st.write("")
        confirm_col = st.columns([2, 1.2, 2])[1]
        with confirm_col:
            disabled = picked is None
            if st.button("♥  Save Mood", type="primary", disabled=disabled, use_container_width=True):
                save_manual_mood(user["id"], st.session_state.picked_mood)
                st.session_state.today_mood_saved = True
                st.session_state.picked_mood = None
                st.rerun()

        if st.session_state.today_mood_saved:
            st.success("Today's mood saved!")
            st.session_state.today_mood_saved = False

        st.markdown('<div class="mm-home-section-gap"></div>', unsafe_allow_html=True)
        st.markdown('<h3 class="mm-home-section-title">Your Mood Calendar</h3>', unsafe_allow_html=True)
        st.caption("Track your emotional journey")

        nav_l, nav_mid, nav_r = st.columns([1, 3, 1])
        if nav_l.button("← Prev"):
            m, y = st.session_state.cal_month - 1, st.session_state.cal_year
            if m == 0: m, y = 12, y - 1
            st.session_state.cal_month, st.session_state.cal_year = m, y
            st.rerun()
        if nav_r.button("Next →"):
            m, y = st.session_state.cal_month + 1, st.session_state.cal_year
            if m == 13: m, y = 1, y + 1
            st.session_state.cal_month, st.session_state.cal_year = m, y
            st.rerun()
        nav_mid.markdown(
            f"<h4 style='text-align:center'>{calendar.month_name[st.session_state.cal_month]} "
            f"{st.session_state.cal_year}</h4>", unsafe_allow_html=True,
        )

        logs = get_mood_logs_for_month(user["id"], st.session_state.cal_year, st.session_state.cal_month)
        by_day = {row["mood_date"].day: row for row in logs}

        weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(
            st.session_state.cal_year, st.session_state.cal_month
        )
        day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        header_cols = st.columns(7)
        for c, name in zip(header_cols, day_names):
            c.markdown(f"<div class='mm-cal-dayname'>{name}</div>", unsafe_allow_html=True)

        for week in weeks:
            cols = st.columns(7)
            for col, day_num in zip(cols, week):
                if day_num == 0:
                    col.write("")
                    continue
                entry = by_day.get(day_num)
                s = _style_for(entry["sentiment"] if entry else None)
                is_today = date(st.session_state.cal_year, st.session_state.cal_month, day_num) == date.today()
                col.markdown(
                    f"""
                    <div class="mm-cal-cell {'mm-cal-cell--today' if is_today else ''}"
                         style="--cal-color:{s['color']}">
                        <div class="mm-cal-daynum">{day_num}</div>
                        <div class="mm-cal-emoji">{s['emoji'] or '·'}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        legend_html = "".join(
            f'<span class="mm-cal-legend-item"><span class="mm-cal-legend-dot" '
            f'style="background:{_style_for(l)["color"]}"></span>{_style_for(l)["emoji"]} {l} '
            f'{sum(1 for h in history_all if h["sentiment"] == l)}</span>'
            for l in MOOD_LABELS
        )
        st.markdown(f'<div class="mm-cal-legend">{legend_html}</div>', unsafe_allow_html=True)

    with side_col:
        _render_right_column()
