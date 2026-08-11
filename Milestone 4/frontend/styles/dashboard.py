"""
components/dashboard.py

Premium "Dashboard" section for MoodMentor.

IMPORTANT: UI ONLY for data. get_user_mood_history() is the exact same
call as the original inline "Dashboard" branch, and every number shown is
computed from real data -- no fabricated stats.

DISCLOSED SUBSTITUTIONS (read before wiring this up):
    - The reference had "Wellness Chats" and "Relax Sessions" metric
      cards, but nothing in your code counts either of those. Swapped for
      "Total Check-ins" and "Current Streak" instead -- both real,
      computed the same way Home's streak metric already is.
    - Mood distribution / trend / emotions charts are rebuilt as custom
      SVG/CSS visuals instead of st.pyplot/st.line_chart/st.bar_chart, but
      every number in them comes from the identical counting logic as the
      original code. Only the rendering changed.
    - "View all activity" is a disclosed decorative label -- there's no
      separate activity page in your app.
    - The top date badge is informational (shows the actual span of
      loaded history), not an interactive multi-week filter -- that
      filtering doesn't exist in your original code either.
    - Weekly insights text is computed from real counts (dominant mood,
      trend direction), not a generic made-up sentence.
    - Export PDF uses your exact build_pdf_report() and
      get_period_recommendation() -- passed in as a parameter to avoid
      duplicating that (fairly long) function or creating a circular
      import with app.py.

Usage in app.py (replaces the original `elif section == "Dashboard": ...` body):

    from components.dashboard import render_dashboard_section
    ...
    elif section == "Dashboard":
        render_dashboard_section(user, build_pdf_report)
"""

import base64
from datetime import date
from pathlib import Path

import streamlit as st

from db import MOOD_EMOJI, get_user_mood_history
from recommendations import get_period_recommendation

MOOD_STYLE = {
    "Happy":   {"emoji": MOOD_EMOJI["Happy"],   "color": "#3b82f6"},
    "Neutral": {"emoji": MOOD_EMOJI["Neutral"], "color": "#22c55e"},
    "Sad":     {"emoji": MOOD_EMOJI["Sad"],     "color": "#f59e0b"},
    "Stress":  {"emoji": MOOD_EMOJI["Stress"],  "color": "#f1c40f"},
    "Angry":   {"emoji": MOOD_EMOJI["Angry"],   "color": "#e74c3c"},
    "Fear":    {"emoji": MOOD_EMOJI["Fear"],    "color": "#9b59b6"},
}
MOOD_TO_NUM = {"Happy": 2, "Neutral": 0, "Sad": -1, "Stress": -1, "Angry": -2, "Fear": -2}


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


def _img_or_emoji_html(rel_path: tuple, emoji_fallback: str, css_class: str, width_px: int) -> str:
    path = _resolve_first(rel_path)
    b64 = _get_base64_of_file(str(path))
    if b64:
        return (
            f'<img src="data:image/png;base64,{b64}" class="{css_class}" '
            f'width="{width_px}" style="width:{width_px}px;height:auto;" alt="" />'
        )
    return f'<div class="{css_class} {css_class}--emoji">{emoji_fallback}</div>'


def _metric_card(icon: str, label: str, value: str, sub_html: str, accent: str) -> str:
    return f"""
    <div class="mm-dash-metric" style="--accent:{accent}">
        <div class="mm-dash-metric-icon">{icon}</div>
        <div>
            <div class="mm-dash-metric-label">{label}</div>
            <div class="mm-dash-metric-value">{value}</div>
            <div class="mm-dash-metric-sub">{sub_html}</div>
        </div>
    </div>
    """


def _render_header(oldest_date, newest_date) -> None:
    st.markdown(
        f"""
        <div class="mm-page-header">
            <div>
                <h1 class="mm-page-title">👋 Welcome back!</h1>
                <p class="mm-page-subtitle">Here's your emotional wellness overview.</p>
            </div>
            <div class="mm-home-datetime">
                📅 {oldest_date.strftime('%b %-d')} &ndash; {newest_date.strftime('%b %-d, %Y')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_donut(counts: dict) -> None:
    total = sum(counts.values())
    if total == 0:
        st.caption("No mood data yet.")
        return

    ordered = [(label, count) for label, count in counts.items() if count > 0]
    ordered.sort(key=lambda x: -x[1])

    stops = []
    running_pct = 0.0
    for label, count in ordered:
        pct = 100 * count / total
        color = _style_for(label)["color"]
        stops.append(f"{color} {running_pct:.1f}% {running_pct + pct:.1f}%")
        running_pct += pct
    gradient = ", ".join(stops)

    legend_html = "".join(
        f'<div class="mm-donut-legend-item">'
        f'<span class="mm-donut-legend-dot" style="background:{_style_for(l)["color"]}"></span>'
        f'{l} <b>{100 * c / total:.0f}%</b></div>'
        for l, c in ordered
    )

    st.markdown(
        f"""
        <div class="mm-donut-row">
            <div class="mm-donut-ring" style="background: conic-gradient({gradient});"></div>
            <div class="mm-donut-legend">{legend_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_trend_line(trend: dict) -> None:
    if not trend:
        st.caption("Not enough data yet for a trend line.")
        return

    dates = list(trend.keys())
    values = list(trend.values())
    vmin, vmax = min(values + [0]), max(values + [0])
    span = (vmax - vmin) or 1

    w, h, pad = 400, 140, 10
    n = len(values)
    step = (w - 2 * pad) / max(n - 1, 1)
    points = []
    for i, v in enumerate(values):
        x = pad + i * step
        y = h - pad - ((v - vmin) / span) * (h - 2 * pad)
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)
    dots = "".join(
        f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="4" fill="#7c6fe8" />'
        for p in points
    )
    labels_html = "".join(f'<span>{d[5:]}</span>' for d in dates)

    st.markdown(
        f"""
        <svg viewBox="0 0 {w} {h}" class="mm-trend-svg" preserveAspectRatio="none">
            <polyline points="{polyline}" fill="none" stroke="#7c6fe8" stroke-width="2.5"
                      stroke-linecap="round" stroke-linejoin="round"/>
            {dots}
        </svg>
        <div class="mm-trend-labels">{labels_html}</div>
        """,
        unsafe_allow_html=True,
    )


def _render_emotion_bars(emo_counts: dict) -> None:
    if not emo_counts:
        st.caption("No journal-based emotion data yet.")
        return
    max_v = max(emo_counts.values())
    # NOTE: built as single-line HTML per bar (no leading whitespace on any
    # line) -- Markdown treats lines indented 4+ spaces as a literal code
    # block, which was causing this HTML to render as raw escaped text
    # instead of being parsed as HTML.
    bars = []
    for k, v in sorted(emo_counts.items(), key=lambda x: -x[1]):
        pct = 100 * v / max_v
        bars.append(
            f'<div class="mm-bar-col"><div class="mm-bar-track">'
            f'<div class="mm-bar-fill" style="height:{pct:.0f}%"></div></div>'
            f'<div class="mm-bar-label">{k}</div>'
            f'<div class="mm-bar-value">{v}</div></div>'
        )
    bars_html = "".join(bars)
    st.markdown(f'<div class="mm-bar-chart">{bars_html}</div>', unsafe_allow_html=True)


def _render_activity_table(history: list) -> None:
    rows_html = "".join(
        f"""
        <tr>
            <td>{h['mood_date']}</td>
            <td>{h['created_at'].strftime('%H:%M')}</td>
            <td>{_style_for(h['sentiment'])['emoji']} {h['sentiment']}</td>
            <td>{f"{h['confidence']:.0%}" if h.get('confidence') is not None else '—'}</td>
            <td>{h['source']}</td>
        </tr>
        """
        for h in history[:15]
    )
    st.markdown(
        f"""
        <table class="mm-activity-table">
            <thead>
                <tr><th>Date</th><th>Time</th><th>Mood</th><th>Confidence</th><th>Source</th></tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        <div class="mm-view-all-label">View all activity →</div>
        """,
        unsafe_allow_html=True,
    )


def _compute_weekly_insight(counts: dict, trend: dict) -> str:
    """Real computed insight -- dominant mood + trend direction, not a
    generic made-up sentence."""
    total = sum(counts.values())
    if total == 0:
        return "Log a few moods to start seeing personalized insights here."

    dominant = max(counts.items(), key=lambda x: x[1])[0]
    values = list(trend.values())
    direction = ""
    if len(values) >= 2:
        direction = " up" if values[-1] > values[0] else (" down" if values[-1] < values[0] else " steady")

    return (
        f"Your most common mood recently has been **{dominant}**. "
        f"Your overall trend looks{direction} over this period."
    )


def render_dashboard_section(user: dict, build_pdf_report_fn, debug: bool = True) -> None:
    """Render the Dashboard section. get_user_mood_history() call and all
    counting logic is identical to the original inline
    `elif section == "Dashboard":` block -- only rendering changed.
    build_pdf_report_fn is passed in (your existing build_pdf_report from
    app.py) to avoid duplicating that function or creating a circular
    import.
    """
    if debug:
        css_path = _resolve_first(
            ("styles", "dashboard.css"), ("assets", "styles", "dashboard.css"), ("assets", "css", "dashboard.css"),
        )
        if css_path.exists():
            st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
        else:
            st.warning(f"dashboard.css not found. Checked: `{css_path}`")

    history = get_user_mood_history(user["id"], limit=200)
    if not history:
        st.info("No entries yet — pick a mood on Home or write a journal entry to see your dashboard.")
        return

    counts = {}
    for h in history:
        counts[h["sentiment"]] = counts.get(h["sentiment"], 0) + 1

    by_date = {}
    for h in history:
        by_date.setdefault(h["mood_date"], []).append(MOOD_TO_NUM.get(h["sentiment"], 0))
    trend = {str(d): sum(v) / len(v) for d, v in sorted(by_date.items())}

    emo_counts = {}
    for h in history:
        if h["source"] == "nlp" and h["emotion"]:
            emo_counts[h["emotion"]] = emo_counts.get(h["emotion"], 0) + 1

    latest = history[0]
    journal_count = sum(1 for h in history if h.get("journal_text"))
    streak = 0
    day_ptr = date.today()
    day_set = {h["mood_date"] for h in history}
    while day_ptr in day_set:
        streak += 1
        day_ptr = date.fromordinal(day_ptr.toordinal() - 1)

    _render_header(history[-1]["mood_date"], history[0]["mood_date"])

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        s = _style_for(latest["sentiment"])
        st.markdown(_metric_card("😊", "Overall Mood", latest["sentiment"], "You've had a good week!", s["color"]), unsafe_allow_html=True)
    with m2:
        st.markdown(_metric_card("📝", "Journal Entries", str(journal_count), "Keep journaling!", "#22c55e"), unsafe_allow_html=True)
    with m3:
        st.markdown(_metric_card("📊", "Total Check-ins", str(len(history)), "All-time entries", "#3b82f6"), unsafe_allow_html=True)
    with m4:
        st.markdown(_metric_card("🔥", "Current Streak", f"{streak} Days", "Keep it going!", "#f59e0b"), unsafe_allow_html=True)

    st.markdown('<div class="mm-card-spacer"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown('<div class="mm-dash-card-marker"></div>', unsafe_allow_html=True)
            st.markdown('<div class="mm-card-title">Mood distribution</div>', unsafe_allow_html=True)
            _render_donut(counts)
    with c2:
        with st.container(border=True):
            st.markdown('<div class="mm-dash-card-marker"></div>', unsafe_allow_html=True)
            st.markdown('<div class="mm-card-title">Mood trend over time</div>', unsafe_allow_html=True)
            _render_trend_line(trend)
    with c3:
        with st.container(border=True):
            st.markdown('<div class="mm-dash-card-marker"></div>', unsafe_allow_html=True)
            st.markdown('<div class="mm-card-title">Emotions from journal entries</div>', unsafe_allow_html=True)
            _render_emotion_bars(emo_counts)

    st.markdown('<div class="mm-card-spacer"></div>', unsafe_allow_html=True)

    left, right = st.columns([1.6, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<div class="mm-dash-card-marker"></div>', unsafe_allow_html=True)
            st.markdown('<div class="mm-card-title">Recent activity</div>', unsafe_allow_html=True)
            _render_activity_table(history)

    with right:
        insight_img = _img_or_emoji_html(
            ("assets", "illustrations", "breathing-woman.png"), "🧘‍♀️", "mm-insight-illustration", 90
        )
        insight_text = _compute_weekly_insight(counts, trend)
        with st.container(border=True):
            st.markdown('<div class="mm-dash-card-marker"></div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="mm-insight-row">
                    <div>
                        <div class="mm-card-title">✨ Weekly insights</div>
                        <div class="mm-insight-text">{insight_text}</div>
                    </div>
                    {insight_img}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            st.markdown('<div class="mm-dash-card-marker mm-export-card-marker"></div>', unsafe_allow_html=True)
            st.markdown(
                """
                <div class="mm-card-title">⬇️ Export report</div>
                <div class="mm-card-subtitle">Download your mood and activity report.</div>
                """,
                unsafe_allow_html=True,
            )
            oldest_date = history[-1]["mood_date"]
            today = date.today()
            date_range = st.date_input(
                "Select date range", value=(oldest_date, today),
                min_value=oldest_date, max_value=today,
                key="dashboard_export_range", label_visibility="collapsed",
            )
            with st.container():
                st.markdown('<div class="mm-export-btn-marker"></div>', unsafe_allow_html=True)
                clicked = st.button("Export PDF", key="dashboard_export_btn", use_container_width=True)
            if clicked:
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_d, end_d = date_range
                else:
                    start_d = end_d = date_range
                filtered = [h for h in history if start_d <= h["mood_date"] <= end_d]
                if not filtered:
                    st.warning("No entries in that date range.")
                else:
                    recommendation_text = get_period_recommendation(filtered)
                    pdf_bytes = build_pdf_report_fn(
                        user["username"], start_d, end_d, filtered, recommendation_text,
                    )
                    st.success(recommendation_text)
                    st.download_button(
                        "Download PDF", data=pdf_bytes,
                        file_name=f"moodmentor_report_{start_d}_{end_d}.pdf",
                        mime="application/pdf",
                    )
