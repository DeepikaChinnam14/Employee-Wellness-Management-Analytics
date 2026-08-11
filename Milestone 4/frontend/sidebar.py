"""
components/sidebar.py

Premium sidebar for MoodMentor's authenticated app screens (Home, Journal,
Wellness Chat, Face Detection, Relax, Dashboard, Reports).

IMPORTANT: UI ONLY. Reuses the exact session_state keys and logout logic
from the original inline sidebar block in app.py:
    - st.session_state.nav
    - st.session_state.token / page / show_auth_panel (cleared on logout)
No new backend calls. Nav options are only ever what the caller passes in
(app.py already computes these correctly per role) -- this module does not
invent extra nav items.

Usage in app.py (replaces the `with st.sidebar: ...` block):

    from components.sidebar import render_sidebar
    ...
    if role == "employee":
        nav_options = ["Home", "Journal", "Wellness Chat", "Face Detection", "Relax", "Dashboard"]
    else:
        nav_options = ["Reports"]
    render_sidebar(user, role, nav_options)
"""

import base64
from pathlib import Path

import streamlit as st

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


def _load_dashboard_css() -> bool:
    css_path = _resolve_first(
        ("styles", "dashboard.css"),
        ("assets", "styles", "dashboard.css"),
        ("assets", "css", "dashboard.css"),
    )
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
        return True
    return False


# Only icons for routes that actually exist in nav_options get used --
# this dict is a lookup table, not a feature list.
_NAV_ICONS = {
    "Home": "🏠",
    "Journal": "📖",
    "Wellness Chat": "💬",
    "Face Detection": "📷",
    "Relax": "🧘",
    "Dashboard": "📊",
    "Reports": "📈",
}


def render_sidebar(user: dict, role: str, nav_options: list, debug: bool = True) -> None:
    """Render the styled sidebar and update st.session_state.nav.

    `nav_options` must be exactly what app.py already computes for the
    current role -- this function does not add or remove routes.

    `debug=True` (default) shows a small warning in the sidebar itself if
    dashboard.css can't be found, listing the exact paths checked. Set to
    False once you've confirmed the file is in place.
    """
    css_ok = _load_dashboard_css()

    bg_path = _resolve_first(("assets", "backgrounds", "background.png"))
    bg_b64 = _get_base64_of_file(str(bg_path))

    with st.sidebar:
        if debug and not css_ok:
            checked = [
                str(Path(root, "styles", "dashboard.css")) for root in _CANDIDATE_ROOTS
            ] + [
                str(Path(root, "assets", "styles", "dashboard.css")) for root in _CANDIDATE_ROOTS
            ]
            st.warning(
                "dashboard.css not found. Sidebar/Home will look unstyled "
                "until it exists at one of:\n\n"
                + "\n\n".join(f"- `{p}`" for p in checked[:3])
            )

        logo_path = _resolve_first(("assets", "logo", "logo.png"))
        logo_b64 = _get_base64_of_file(str(logo_path))
        if logo_b64:
            logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="mm-sidebar-logo-img" alt="Logo" />'
        else:
            logo_html = '<div class="mm-sidebar-brand-icon">🌿</div>'

        st.markdown(
            f"""
            <div class="mm-sidebar-brand">
                {logo_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        labeled_options = [f"{_NAV_ICONS.get(o, '•')}  {o}" for o in nav_options]
        current = st.session_state.nav if st.session_state.nav in nav_options else nav_options[0]
        current_label = f"{_NAV_ICONS.get(current, '•')}  {current}"
        default_index = labeled_options.index(current_label) if current_label in labeled_options else 0

        choice_label = st.radio(
            "Navigate", labeled_options, index=default_index,
            label_visibility="collapsed", key="sidebar_nav_radio",
        )
        st.session_state.nav = nav_options[labeled_options.index(choice_label)]

        initials = "".join(w[0] for w in user["username"].split()[:2]).upper() or "U"
        st.markdown(
            f"""
            <div class="mm-sidebar-profile">
                <div class="mm-sidebar-avatar">{initials}</div>
                <div>
                    <div class="mm-sidebar-username">{user['username']}</div>
                    <div class="mm-sidebar-role">{role.capitalize()}</div>
                </div>
            </div>
            <div class="mm-sidebar-email">{user['email']}</div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("↩  Log out", use_container_width=True, key="sidebar_logout_btn"):
            st.session_state.token = None
            st.session_state.page = "welcome"
            st.session_state.show_auth_panel = False
            st.rerun()

        if bg_b64:
            st.markdown(
                f"""
                <style>
                section[data-testid="stSidebar"] {{
                    background-image:
                        linear-gradient(180deg, rgba(247,245,255,0.98) 0%, rgba(247,245,255,0.55) 30%, rgba(247,245,255,0.02) 55%, rgba(247,245,255,0) 100%),
                        url("data:image/png;base64,{bg_b64}") !important;
                    background-size: cover !important;
                    background-position: bottom center !important;
                    background-repeat: no-repeat !important;
                    background-attachment: fixed !important;
                }}
                section[data-testid="stSidebar"] > div:first-child {{
                    background: transparent !important;
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )
