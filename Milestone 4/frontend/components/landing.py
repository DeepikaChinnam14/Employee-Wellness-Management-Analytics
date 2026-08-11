
# Landing page code will go here
# components/landing.py

"""
components/landing.py

Premium landing page for the Employee Wellness Management System.
Renders a pastel mountain hero background, centered logo, AI Powered
badges, hero title/subtitle, glassmorphism feature cards, and a
Get Started call-to-action that opens the auth panel.

Expects:
  - assets/backgrounds/background.png  (hero background image)
  - assets/logo/logo.png               (centered logo)
  - assets/css/landing.css             (stylesheet, loaded separately)
"""

import base64
import os
from pathlib import Path

import streamlit as st

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
#
# Different launch environments (local venv, Colab, Docker, `streamlit run`
# from a different cwd, etc.) can make __file__-relative paths and the
# current working directory disagree about where the project root is.
# _resolve_path() checks several likely roots and returns the first path
# that actually exists, so assets load regardless of how the app is run.

_THIS_FILE = Path(__file__).resolve()
_CANDIDATE_ROOTS = [
    _THIS_FILE.parent.parent,      # e.g. project_root/components/landing.py -> project_root
    Path.cwd(),                    # wherever `streamlit run` was launched from
    Path.cwd().parent,             # one level up from cwd, just in case
]


def _resolve_path(*relative_parts: str) -> Path:
    """Return the first existing path among candidate project roots.

    If none exist, returns the path under the primary (file-based) root so
    the caller still gets a sensible path to report in error messages.
    """
    for root in _CANDIDATE_ROOTS:
        candidate = root.joinpath(*relative_parts)
        if candidate.exists():
            return candidate
    return _CANDIDATE_ROOTS[0].joinpath(*relative_parts)


def _resolve_first(*candidate_relative_paths: tuple) -> Path:
    """Like _resolve_path, but tries several different relative-path shapes.

    Useful when a file could plausibly live under more than one folder
    convention (e.g. `styles/landing.css` vs `assets/css/landing.css`).
    Each argument is a tuple of path parts. Returns the first that exists
    across all candidate roots, else the first shape under the primary root.
    """
    for root in _CANDIDATE_ROOTS:
        for parts in candidate_relative_paths:
            candidate = root.joinpath(*parts)
            if candidate.exists():
                return candidate
    return _CANDIDATE_ROOTS[0].joinpath(*candidate_relative_paths[0])


def _get_paths() -> dict:
    """Resolve asset paths fresh on every call (cheap, avoids stale imports)."""
    return {
        "background": _resolve_path("assets", "backgrounds", "background.png"),
        "logo": _resolve_path("assets", "logo", "logo.png"),
        # CSS may live in a top-level `styles/` folder (this project's layout)
        # or the `assets/css/` convention -- try both.
        "css": _resolve_first(
            ("styles", "landing.css"),
            ("assets", "css", "landing.css"),
        ),
    }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner=False)
def _get_base64_of_file(file_path: str) -> str:
    """Read a local file and return its base64-encoded string."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")
    except FileNotFoundError:
        return ""


def _load_css(css_path: Path) -> bool:
    """Inject an external CSS file into the Streamlit app. Returns True if found."""
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        return True
    return False


def _inject_background(image_path: Path) -> bool:
    """Set the page background image via base64 CSS. Returns True if found.

    Newer Streamlit versions render an inner `stAppViewContainer` div with
    its own opaque background-color that sits on top of `.stApp`, which
    silently hides a background-image set only on `.stApp`. We target every
    layer that could be painting over it and force those layers transparent.
    """
    encoded = _get_base64_of_file(str(image_path))
    if not encoded:
        return False
    st.markdown(
        f"""
        <style>
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {{
            background-color: transparent !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background-image:
                linear-gradient(
                    180deg,
                    rgba(255, 255, 255, 0.12) 0%,
                    rgba(255, 255, 255, 0.05) 40%,
                    rgba(255, 255, 255, 0.18) 100%
                ),
                url("data:image/png;base64,{encoded}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}

        [data-testid="stHeader"] {{
            background-color: transparent !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    return True


def _get_logo_html(logo_path: Path, max_width_px: int = 260) -> str:
    """Return an <img> tag for the logo, or a text fallback."""
    encoded = _get_base64_of_file(str(logo_path))
    if encoded:
        return (
            f'<img src="data:image/png;base64,{encoded}" '
            f'class="landing-logo-img" style="max-width:{max_width_px}px;" '
            f'alt="Company Logo" />'
        )
    return f'<div class="landing-logo-fallback">{BRAND_NAME_PRIMARY}{BRAND_NAME_ACCENT}</div>'


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #

FEATURE_CARDS = [
    {
        "icon": "🙂",
        "title": "Understand",
        "tone": "indigo",
        "description": "Understand your emotions and gain clarity about your inner self.",
    },
    {
        "icon": "🌱",
        "title": "Improve",
        "tone": "green",
        "description": "Build healthy habits and improve your mental and emotional well-being.",
    },
    {
        "icon": "📈",
        "title": "Grow",
        "tone": "pink",
        "description": "Track your progress and grow into the best version of yourself.",
    },
]

AI_BADGES = [
    {"icon": "✨", "label": "AI Powered", "tone": "indigo"},
    {"icon": "🔒", "label": "Private &amp; Secure", "tone": "green"},
    {"icon": "💜", "label": "Always Here", "tone": "pink"},
]

BRAND_NAME_PRIMARY = "Mood"
BRAND_NAME_ACCENT = "Mentor"
BRAND_TAGLINE = "AI-Powered Emotional Wellness Assistant"
BRAND_DESCRIPTION = (
    "Understand your emotions, improve your well-being, and grow into "
    "the best version of yourself with the power of AI and self-care."
)


# --------------------------------------------------------------------------- #
# Section renderers
# --------------------------------------------------------------------------- #

def _render_badge_row() -> str:
    return "".join(
        f'<span class="ai-badge ai-badge--{b["tone"]}">'
        f'<span class="ai-badge-icon">{b["icon"]}</span>{b["label"]}</span>'
        for b in AI_BADGES
    )


def _render_hero(logo_html: str) -> None:
    st.markdown(
        f"""
        <div class="hero-container">
            <div class="landing-logo-wrapper">
                {logo_html}
            </div>
            <div class="ai-badge-row">
                {_render_badge_row()}
            </div>
            <p class="hero-eyebrow">Welcome to</p>
            <div class="hero-divider">
                <span class="hero-divider-line"></span>
                <span class="hero-divider-leaf">🌿</span>
                <span class="hero-divider-line"></span>
            </div>
            <h1 class="hero-title">
                {BRAND_NAME_PRIMARY}<span class="hero-title-accent">{BRAND_NAME_ACCENT}</span>
            </h1>
            <p class="hero-tagline">{BRAND_TAGLINE}</p>
            <p class="hero-subtitle">{BRAND_DESCRIPTION}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_feature_cards() -> None:
    st.markdown('<div class="feature-grid">', unsafe_allow_html=True)

    cols = st.columns(len(FEATURE_CARDS), gap="medium")
    for col, feature in zip(cols, FEATURE_CARDS):
        with col:
            st.markdown(
                f"""
                <div class="glass-card">
                    <div class="glass-card-icon glass-card-icon--{feature['tone']}">
                        {feature['icon']}
                    </div>
                    <div class="glass-card-title glass-card-title--{feature['tone']}">
                        {feature['title']}
                    </div>
                    <div class="glass-card-desc">{feature['description']}</div>
                    <div class="glass-card-underline glass-card-underline--{feature['tone']}"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_cta() -> None:
    st.markdown('<div class="cta-wrapper">', unsafe_allow_html=True)

    left, center, right = st.columns([1.3, 1, 1.3])
    with center:
        clicked = st.button(
            "Get Started  →",
            key="landing_get_started_btn",
        )
        if clicked:
            st.session_state.show_auth_panel = True
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _render_footer() -> None:
    st.markdown(
        """
        <div class="landing-footer">
            <span class="privacy-pill">
                🛡️ Your privacy is our priority. Your journey is safe with us.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

def render_landing_page(debug: bool = True) -> None:
    """Render the full premium landing page.

    Args:
        debug: When True (default), shows a small warning banner listing
            exact resolved paths for any missing asset (css/background/logo)
            so misplacement is easy to spot. Set to False once assets are
            confirmed in place.
    """

    if "show_auth_panel" not in st.session_state:
        st.session_state.show_auth_panel = False

    paths = _get_paths()

    css_ok = _load_css(paths["css"])
    bg_ok = _inject_background(paths["background"])

    if debug:
        missing = []
        if not css_ok:
            missing.append(f"CSS not found at: `{paths['css']}`")
        if not bg_ok:
            missing.append(f"Background image not found at: `{paths['background']}`")
        if not paths["logo"].exists():
            missing.append(f"Logo not found at: `{paths['logo']}`")
        if missing:
            st.warning(
                "Landing page assets missing (page will look unstyled until "
                "these exist at the exact paths below):\n\n"
                + "\n\n".join(f"- {m}" for m in missing)
                + f"\n\nSearched project roots (in order): "
                + ", ".join(f"`{r}`" for r in _CANDIDATE_ROOTS)
            )

    st.markdown('<div class="landing-page-container">', unsafe_allow_html=True)

    logo_html = _get_logo_html(paths["logo"])
    _render_hero(logo_html)
    _render_cta()
    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    _render_feature_cards()
    _render_footer()

    st.markdown("</div>", unsafe_allow_html=True)


# Alias for compatibility with callers that import `show_landing`
# (e.g. `from components.landing import show_landing`).
show_landing = render_landing_page


# Allow `components/landing.py` to be run directly for isolated preview.
if __name__ == "__main__":
    st.set_page_config(
        page_title="Employee Wellness Management System",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    render_landing_page()
