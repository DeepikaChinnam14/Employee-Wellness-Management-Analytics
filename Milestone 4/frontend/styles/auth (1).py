"""
components/auth.py

Premium authentication UI for MoodMentor, matching the landing page's
pastel-mountain glassmorphism design language.

IMPORTANT: This module is UI ONLY.
Every backend call (auth.*, email_utils.send_otp), every st.session_state
key (auth_mode, email, token, show_auth_panel, page), and every branch of
the login / signup / verify / forgot / reset flow is copied verbatim from
the original inline block in app.py. No authentication, JWT, OTP, or
database logic has been changed -- only the markup/CSS around it.

Deliberately NOT included (no backend support exists for these yet):
  - "Continue with Google" / "Continue with Microsoft" (no OAuth backend)
  - "Remember Me" checkbox (nothing to wire it to)

Expects:
  - assets/backgrounds/background.png  (shared with the landing page)
  - styles/auth.css                    (primary stylesheet location;
    also checked: assets/styles/auth.css, assets/css/auth.css)

Usage in app.py:

    from components.auth import render_auth_screen
    ...
    if st.session_state.page == "welcome":
        if not st.session_state.show_auth_panel:
            show_landing()
            st.stop()
        render_auth_screen()
        st.stop()
"""

import base64
import re
from pathlib import Path

import streamlit as st

from auth import (
    make_token, get_user, username_taken, create_user, verify_user,
    set_password, check_pw, new_otp, save_otp, check_otp,
)
from email_utils import send_otp


# --------------------------------------------------------------------------- #
# Paths (same robust multi-root resolver pattern as components/landing.py)
# --------------------------------------------------------------------------- #

_THIS_FILE = Path(__file__).resolve()
_CANDIDATE_ROOTS = [
    _THIS_FILE.parent.parent,      # project_root/components/auth.py -> project_root
    Path.cwd(),
    Path.cwd().parent,
]


def _resolve_first(*candidate_relative_paths: tuple) -> Path:
    """Return the first existing path across candidate roots and shapes."""
    for root in _CANDIDATE_ROOTS:
        for parts in candidate_relative_paths:
            candidate = root.joinpath(*parts)
            if candidate.exists():
                return candidate
    return _CANDIDATE_ROOTS[0].joinpath(*candidate_relative_paths[0])


def _get_paths() -> dict:
    return {
        "background": _resolve_first(("assets", "backgrounds", "background.png")),
        "logo": _resolve_first(("assets", "logo", "logo.png")),
        # `styles/auth.css` matches this project's actual layout; the other
        # two are fallbacks in case the project is reorganized later.
        "css": _resolve_first(
            ("styles", "auth.css"),
            ("assets", "styles", "auth.css"),
            ("assets", "css", "auth.css"),
        ),
    }


@st.cache_data(show_spinner=False)
def _get_base64_of_file(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        return ""


def _load_css(css_path: Path) -> bool:
    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )
        return True
    return False


def _inject_background(image_path: Path) -> bool:
    """Same technique used on the landing page: target stAppViewContainer
    directly and force the layers above it transparent, since that inner
    container paints an opaque background over a plain `.stApp` rule."""
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


# --------------------------------------------------------------------------- #
# UI-only helpers (copied from app.py so this module has no import-time
# dependency on app.py, which would create a circular import)
# --------------------------------------------------------------------------- #

def _valid_pw(pw: str) -> bool:
    return bool(len(pw) >= 8 and re.search(r"[A-Za-z]", pw) and re.search(r"[0-9]", pw))


def _goto_auth(mode: str) -> None:
    st.session_state.auth_mode = mode
    st.rerun()


# --------------------------------------------------------------------------- #
# Left panel content (marketing / feature panel)
# --------------------------------------------------------------------------- #

FEATURES = [
    {
        "icon": "🧠",
        "title": "AI Mood Analysis",
        "desc": "Detect emotions from journal entries using NLP.",
    },
    {
        "icon": "📊",
        "title": "Wellness Analytics",
        "desc": "Track mood trends and streaks with visual dashboards.",
    },
    {
        "icon": "💬",
        "title": "MoodMentor Assistant",
        "desc": "Your 24/7 AI companion for supportive conversations.",
    },
    {
        "icon": "📸",
        "title": "Face Detection",
        "desc": "DeepFace-powered scans with personalized recommendations.",
    },
    {
        "icon": "🛡️",
        "title": "Secure & Private",
        "desc": "JWT-secured accounts and encrypted sessions.",
    },
]

def _get_logo_html(logo_path: Path, max_width_px: int = 220) -> str:
    encoded = _get_base64_of_file(str(logo_path))
    if encoded:
        return (
            f'<img src="data:image/png;base64,{encoded}" '
            f'class="auth-header-logo-img" style="max-width:{max_width_px}px;" '
            f'alt="Logo" />'
        )
    return '<div class="auth-header-logo-fallback">MoodMentor</div>'


def _render_top_header(logo_html: str) -> None:
    st.markdown(
        f"""
        <div class="auth-header">
            <div class="auth-header-logo">{logo_html}</div>
            <h1 class="auth-header-title">Employee Wellness Management System</h1>
            <p class="auth-header-subtitle">
                <span>➜</span> AI-Powered Workplace Wellbeing Platform <span>⬅</span>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_floating_cards() -> None:
    st.markdown(
        """
        <div class="auth-float-card auth-float-card--left">
            <div class="auth-float-icon">💜</div>
            <div>
                <div class="auth-float-label">Mood Score</div>
                <div class="auth-float-value">84%</div>
                <div class="auth-float-tag">● Excellent</div>
            </div>
        </div>
        <div class="auth-float-card auth-float-card--right">
            <div class="auth-float-icon">🙂</div>
            <div>
                <div class="auth-float-label">Today's Wellness</div>
                <div class="auth-float-value">Excellent</div>
                <div class="auth-float-tag">Keep it up! 🌱</div>
            </div>
        </div>
        <div class="auth-float-card auth-float-card--bottom-right">
            <div class="auth-float-icon">🤖</div>
            <div>
                <div class="auth-float-label">AI Analysis</div>
                <div class="auth-float-value">Ready</div>
                <div class="auth-float-tag">Tap to view →</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_mockup_preview() -> None:
    """Purely decorative dashboard preview (donut + trend chart + chat
    bubble) -- illustrative only, not wired to real data. Mirrors the
    reference screenshot's right-hand mini preview inside the feature panel."""
    st.markdown(
        """
        <div class="auth-mockup">
            <div class="auth-mockup-card">
                <div class="auth-mockup-title">Wellness Overview</div>
                <div class="auth-mockup-donut-row">
                    <div class="auth-mockup-donut">
                        <div class="auth-mockup-donut-inner">
                            <span class="auth-mockup-donut-value">84</span>
                            <span class="auth-mockup-donut-label">Excellent</span>
                        </div>
                    </div>
                    <svg class="auth-mockup-spark" viewBox="0 0 120 40" preserveAspectRatio="none">
                        <polyline points="0,28 15,20 30,24 45,10 60,16 75,6 90,14 105,4 120,10"
                                  fill="none" stroke="#7c6fe8" stroke-width="2.5"
                                  stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </div>
                <div class="auth-mockup-axis">Mon Tue Wed Thu Fri Sat Sun</div>
            </div>
            <div class="auth-mockup-card">
                <div class="auth-mockup-title">Mood Trend (This Week)</div>
                <svg class="auth-mockup-spark auth-mockup-spark--wide" viewBox="0 0 220 60" preserveAspectRatio="none">
                    <polyline points="0,42 30,30 60,38 90,15 120,25 150,8 180,20 220,12"
                              fill="none" stroke="#a78bfa" stroke-width="3"
                              stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <div class="auth-mockup-axis">Mon Tue Wed Thu Fri Sat Sun</div>
            </div>
            <div class="auth-mockup-chat">
                <div class="auth-mockup-bubble">
                    👋 Hi there!<br>I'm MoodMentor.<br>How can I help you today?
                </div>
                <div class="auth-mockup-avatar">🤖</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_left_panel() -> None:
    # Marker div lets auth.css target this specific glass card via :has()
    # without relying on separate st.markdown calls actually nesting
    # (they don't -- see note in auth.css).
    st.markdown('<div class="auth-left-marker"></div>', unsafe_allow_html=True)

    features_html = "".join(
        f'<div class="auth-feature-item">'
        f'<div class="auth-feature-icon">{f["icon"]}</div>'
        f'<div><div class="auth-feature-title">{f["title"]}</div>'
        f'<div class="auth-feature-desc">{f["desc"]}</div></div>'
        f"</div>"
        for f in FEATURES
    )

    text_col, preview_col = st.columns([1.15, 1], gap="medium")

    with text_col:
        st.markdown(
            f"""
            <div class="auth-left-content">
                <span class="auth-left-badge">AI &bull; Insights &bull; Wellbeing</span>
                <h2 class="auth-left-title">Empower Your Team.<br>Elevate Wellbeing.</h2>
                <p class="auth-left-desc">
                    Understand emotions, improve wellbeing, and build a
                    happier, healthier workplace with the power of AI.
                </p>
                <div class="auth-feature-list">{features_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with preview_col:
        _render_mockup_preview()


# --------------------------------------------------------------------------- #
# Right panel: the actual auth forms
# (identical logic to the original inline block -- only markup/labels
# gained icons; every condition, session_state key, and function call is
# unchanged)
# --------------------------------------------------------------------------- #

def _render_right_panel() -> None:
    st.markdown('<div class="auth-right-marker"></div>', unsafe_allow_html=True)

    mode = st.session_state.auth_mode

    if mode == "login":
        st.markdown('<div class="auth-heading">👋 Welcome Back!</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="auth-subtitle">Sign in to continue your wellness journey.</p>',
            unsafe_allow_html=True,
        )
        with st.form("login"):
            email = st.text_input("📧 Email Address", placeholder="Enter your email")
            pw = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            go = st.form_submit_button("Continue  ", type="primary", use_container_width=True)
        if go:
            u = get_user(email.strip().lower())
            if not u or not check_pw(pw, u["password_hash"]):
                st.error("Invalid email or password.")
            elif not u["is_verified"]:
                st.warning("Verify your email first.")
                st.session_state.email = u["email"]
                _goto_auth("verify")
            else:
                st.session_state.token = make_token(u)
                st.rerun()

        # Forgot password link, right-aligned
        st.markdown('<div class="auth-forgot-link">', unsafe_allow_html=True)
        if st.button("Forgot Password?", key="login_forgot_btn"):
            _goto_auth("forgot")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="auth-divider"><span>OR</span></div>', unsafe_allow_html=True)

        st.markdown('<div class="auth-create-account">', unsafe_allow_html=True)
        if st.button("Don't have an account?  Create Account →", key="login_create_account_btn", use_container_width=True):
            _goto_auth("signup")
        st.markdown("</div>", unsafe_allow_html=True)

    elif mode == "signup":
        st.markdown('<div class="auth-heading">✨ Create Account</div>', unsafe_allow_html=True)
        st.markdown('<p class="auth-subtitle">Let\'s get you started.</p>', unsafe_allow_html=True)
        with st.form("signup"):
            username = st.text_input("👤 Full Name", placeholder="Enter your full name")
            email = st.text_input("📧 Email Address", placeholder="Enter your email")
            pw = st.text_input("🔒 Password", type="password", placeholder="Create password")
            role_label = st.radio("I am signing up as a:", ["Employee", "Manager"], horizontal=True)
            go = st.form_submit_button("Send OTP  🚀", type="primary", use_container_width=True)
        if go:
            email = email.strip().lower()
            role = "manager" if role_label == "Manager" else "employee"
            if len(username) < 3:
                st.error("Username too short.")
            elif not _valid_pw(pw):
                st.error("Password needs 8+ chars, letters and numbers.")
            elif username_taken(username) or get_user(email):
                st.error("Username or email already in use.")
            else:
                create_user(username, email, pw, role=role)
                code = new_otp()
                save_otp(email, code, "signup")
                ok, msg = send_otp(email, code, "signup")
                if ok:
                    st.session_state.email = email
                    st.success("Check your email for the code.")
                    _goto_auth("verify")
                else:
                    st.error(f"Email failed: {msg}")

        if st.button("Already have an account? Login", use_container_width=True):
            _goto_auth("login")

    elif mode == "verify":
        email = st.session_state.email
        st.markdown('<div class="auth-heading">📩 Verify OTP</div>', unsafe_allow_html=True)
        st.markdown(
            f'<p class="auth-subtitle">We sent a 6-digit code to <b>{email}</b></p>',
            unsafe_allow_html=True,
        )
        with st.form("verify"):
            code = st.text_input("🔢 Code", max_chars=6, placeholder="Enter 6-digit code")
            go = st.form_submit_button("Verify OTP  🚀", type="primary", use_container_width=True)
        if go:
            if check_otp(email, code.strip(), "signup"):
                verify_user(email)
                st.success("Verified! Please log in.")
                _goto_auth("login")
            else:
                st.error("Invalid or expired code.")

        if st.button("← Back to login", use_container_width=True):
            _goto_auth("login")

    elif mode == "forgot":
        st.markdown('<div class="auth-heading">🔑 Forgot Password</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="auth-subtitle">We\'ll send a reset code to your email.</p>',
            unsafe_allow_html=True,
        )
        with st.form("forgot"):
            email = st.text_input("📧 Your Account Email")
            go = st.form_submit_button("Send Reset Code  🚀", type="primary", use_container_width=True)
        if go:
            email = email.strip().lower()
            if get_user(email):
                code = new_otp()
                save_otp(email, code, "password_reset")
                send_otp(email, code, "password_reset")
            st.session_state.email = email
            st.info("If that email exists, a code was sent.")
            _goto_auth("reset")

        if st.button("← Back to login", use_container_width=True):
            _goto_auth("login")

    elif mode == "reset":
        email = st.session_state.email
        st.markdown('<div class="auth-heading">🔐 Reset Password</div>', unsafe_allow_html=True)
        st.markdown('<p class="auth-subtitle">Choose a new password.</p>', unsafe_allow_html=True)
        with st.form("reset"):
            code = st.text_input("🔢 Reset Code", max_chars=6)
            pw = st.text_input("🔒 New Password", type="password")
            go = st.form_submit_button("Reset Password  🚀", type="primary", use_container_width=True)
        if go:
            if not _valid_pw(pw):
                st.error("Password needs 8+ chars, letters and numbers.")
            elif not check_otp(email, code.strip(), "password_reset"):
                st.error("Invalid or expired code.")
            else:
                set_password(email, pw)
                st.success("Password reset. Please log in.")
                _goto_auth("login")

        if st.button("← Back to login", use_container_width=True):
            _goto_auth("login")


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

def _render_footer_bar() -> None:
    st.markdown(
        """
        <div class="auth-footer-bar">
            <span>🛡️ Your privacy is our priority. Your journey is safe with us.</span>
            <span class="auth-footer-sep">|</span>
            <span>✨ AI-Powered</span>
            <span class="auth-footer-sep">|</span>
            <span>🔒 Secure</span>
            <span class="auth-footer-sep">|</span>
            <span>👁️ Private</span>
            <span class="auth-footer-sep">|</span>
            <span class="auth-footer-highlight">👥 Trusted by 500+ Organizations</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_auth_screen() -> None:
    """Render the full premium auth screen (login/signup/verify/forgot/reset).

    Drop-in replacement for the inline `left, right = st.columns(...)` block
    that used to live in app.py. Reads/writes the exact same
    st.session_state keys (auth_mode, email, token) so nothing about the
    control flow changes -- only the visual layer.
    """
    paths = _get_paths()
    _load_css(paths["css"])
    _inject_background(paths["background"])

    logo_html = _get_logo_html(paths["logo"])
    _render_top_header(logo_html)
    _render_floating_cards()

    left, right = st.columns([1.35, 1], gap="large")

    with left:
        with st.container(border=True):
            _render_left_panel()

    with right:
        with st.container(border=True):
            _render_right_panel()

    _render_footer_bar()
