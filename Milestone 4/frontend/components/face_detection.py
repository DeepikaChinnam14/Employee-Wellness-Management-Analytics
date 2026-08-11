"""
components/face_detection.py

Premium "Face Scan & Recommendations" section for MoodMentor.

IMPORTANT: UI ONLY. The `analyze_and_display()` function -- every cv2/numpy/
DeepFace call, every mood-based advice branch, save_face_scan() call, and
error handling -- is copied verbatim from the original inline
"Face Detection" branch in app.py. Only the layout/markup around it changed.

One disclosed, non-backend UX change: the reference shows a "Start Camera"
button that reveals the camera widget, rather than the camera opening
immediately on page load (which is what st.camera_input does natively).
This is gated with a plain session_state flag -- analyze_and_display()
itself is untouched.

Usage in app.py (replaces the original `elif section == "Face Detection": ...` body):

    from components.face_detection import render_face_detection_section
    ...
    elif section == "Face Detection":
        render_face_detection_section(user)
"""

import base64
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

from db import save_face_scan

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


def _render_page_header() -> None:
    now = datetime.now()
    st.markdown(
        f"""
        <div class="mm-page-header">
            <div>
                <h1 class="mm-page-title">📸 Face Scan &amp; Recommendations</h1>
                <p class="mm-page-subtitle">
                    Using DeepFace AI to read your micro-expressions and provide personalized mentorship.
                </p>
            </div>
            <div class="mm-home-datetime">
                📅 {now.strftime('%A, %-d %B %Y')} &nbsp;|&nbsp; 🕐 {now.strftime('%I:%M %p')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _analyze_and_display(user: dict, image_bytes: bytes) -> None:
    """UNCHANGED from the original inline function -- same cv2/DeepFace
    calls, same save_face_scan() call, same advice branches, same error
    handling. Only moved into its own function scope."""
    import cv2
    import numpy as np
    from deepface import DeepFace

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        st.info("Scanning biometric markers with MTCNN...")

        tmp_path = "temp_scan.jpg"
        cv2.imwrite(tmp_path, img)

        results = DeepFace.analyze(
            img_path=tmp_path, actions=['emotion'], enforce_detection=True, detector_backend='mtcnn'
        )
        if not isinstance(results, list):
            results = [results]

        st.success(f"Biometric Scan Complete! {len(results)} face(s) mapped.")

        for i, face_data in enumerate(results):
            emotion = face_data['dominant_emotion']
            score_val = face_data['emotion'][emotion]
            box = face_data['region']
            x, y, w, h = box['x'], box['y'], box['w'], box['h']

            cv2.rectangle(img_rgb, (x, y), (x + w, y + h), (0, 255, 120), 3)
            cv2.circle(img_rgb, (x, y), 5, (255, 255, 255), -1)
            cv2.circle(img_rgb, (x + w, y), 5, (255, 255, 255), -1)
            cv2.circle(img_rgb, (x, y + h), 5, (255, 255, 255), -1)
            cv2.circle(img_rgb, (x + w, y + h), 5, (255, 255, 255), -1)
            cv2.putText(
                img_rgb, f"{emotion.upper()} {score_val:.1f}%", (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 120), 2,
            )

            save_face_scan(user["id"], emotion, float(score_val) / 100.0)

        st.image(img_rgb, channels="RGB", use_container_width=True)

        st.markdown("---")
        st.markdown("<h3>🧠 Mood Mentor Analysis</h3>", unsafe_allow_html=True)
        emotion = results[0]['dominant_emotion'].lower()
        if emotion in ["happy", "joy", "amazing"]:
            st.info("💡 **Mentor's Advice:** You're radiating positive energy! Channel this into your "
                    "most challenging tasks today, or share your good mood by helping a colleague.")
            st.balloons()
        elif emotion in ["sad", "sadness"]:
            st.warning("💡 **Mentor's Advice:** It's okay to feel down. Please take a moment for yourself. "
                       "Try the 'Relax' tab for some guided breathing, or write your thoughts down in the Journal.")
        elif emotion in ["angry", "anger", "disgust"]:
            st.error("💡 **Mentor's Advice:** You seem frustrated. Step away from your screen for 5 minutes, "
                     "get a glass of water, and try the 4-7-8 breathing technique in the Relax tab.")
        elif emotion in ["fear", "surprise"]:
            st.warning("💡 **Mentor's Advice:** Take a deep breath. Focus on what you can control right now. "
                       "If you're feeling overwhelmed, break your tasks into smaller steps.")
        else:
            st.success("💡 **Mentor's Advice:** You seem balanced and focused. It's a great time to tackle "
                       "deep work and maintain this calm state.")

    except ValueError:
        st.error("No face detected. Please ensure your face is clearly visible and try again.")
    except Exception as e:
        st.error(f"Error during scan: {e}")
    finally:
        if os.path.exists("temp_scan.jpg"):
            os.remove("temp_scan.jpg")


def _render_camera_tab(user: dict) -> None:
    st.markdown('<p class="mm-scan-label">Initiate Biometric Camera Scan</p>', unsafe_allow_html=True)

    if "face_scan_camera_started" not in st.session_state:
        st.session_state.face_scan_camera_started = False

    with st.container(border=True):
        st.markdown('<div class="mm-scan-card-marker"></div>', unsafe_allow_html=True)

        if not st.session_state.face_scan_camera_started:
            frame_icon_html = _img_or_emoji_html(
                ("assets", "illustrations", "face-scan-icon.png"), "🙂", "mm-scan-frame-icon", 120
            )
            st.markdown(
                f"""
                <div class="mm-scan-placeholder">
                    {frame_icon_html}
                    <div class="mm-scan-placeholder-title">Ready to scan your face</div>
                    <div class="mm-scan-placeholder-desc">
                        Position your face in the center of the frame<br>
                        and click the button below to begin.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            _, center, _ = st.columns([1, 1, 1])
            with center:
                with st.container():
                    st.markdown('<div class="mm-start-camera-marker"></div>', unsafe_allow_html=True)
                    if st.button("📷  Start Camera", key="face_start_camera_btn", use_container_width=True):
                        st.session_state.face_scan_camera_started = True
                        st.rerun()
        else:
            camera_photo = st.camera_input("Initiate Biometric Camera Scan", label_visibility="collapsed")
            if camera_photo:
                _analyze_and_display(user, camera_photo.read())

        st.markdown(
            """
            <div class="mm-privacy-note">
                🛡️ <b>Your privacy is our priority.</b><br>
                <span>Images are processed securely and not stored.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_upload_tab(user: dict) -> None:
    st.markdown('<p class="mm-scan-label">Upload a Photo for Scanning</p>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('<div class="mm-scan-card-marker"></div>', unsafe_allow_html=True)
        uploaded_image = st.file_uploader(
            "Upload Image for Scanning", type=["jpg", "jpeg", "png"], label_visibility="collapsed",
        )
        if uploaded_image:
            _analyze_and_display(user, uploaded_image.read())

        st.markdown(
            """
            <div class="mm-privacy-note">
                🛡️ <b>Your privacy is our priority.</b><br>
                <span>Images are processed securely and not stored.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_tips_footer() -> None:
    tips_html = _img_or_emoji_html(
        ("assets", "illustrations", "tips-plant-books.png"), "🌱📚", "mm-tips-illustration", 130
    )
    st.markdown(
        f"""
        <div class="mm-tips-footer">
            <div>
                <div class="mm-tips-title">💡 Tips for best results</div>
                <div class="mm-tips-desc">Ensure good lighting, face the camera directly and remove any obstructions.</div>
            </div>
            {tips_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _load_dashboard_css_if_needed() -> bool:
    """Load dashboard.css directly, independent of render_sidebar().

    Streamlit doesn't mind duplicate <style> tags (they just apply harmlessly),
    so this is a safe redundancy in case this section ever gets rendered
    without render_sidebar() having run first in the same script pass.
    """
    css_path = _resolve_first(
        ("styles", "dashboard.css"),
        ("assets", "styles", "dashboard.css"),
        ("assets", "css", "dashboard.css"),
    )
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
        return True
    return False


def render_face_detection_section(user: dict, debug: bool = True) -> None:
    """Render the Face Detection section. The scan/analysis logic is
    identical to the original inline `elif section == "Face Detection":`
    block -- only the layout/markup and the camera-reveal gating are new.
    """
    css_ok = _load_dashboard_css_if_needed()

    if debug and not css_ok:
        css_path = _resolve_first(
            ("styles", "dashboard.css"),
            ("assets", "styles", "dashboard.css"),
            ("assets", "css", "dashboard.css"),
        )
        st.warning(
            "dashboard.css not found -- Face Detection page will look "
            f"unstyled. Checked: `{css_path}` (and sibling candidate roots)."
        )

    _render_page_header()

    tab1, tab2 = st.tabs(["📸  Camera Scanner", "📂  Upload Photo"])
    with tab1:
        _render_camera_tab(user)
    with tab2:
        _render_upload_tab(user)

    _render_tips_footer()
