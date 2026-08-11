import os, re, io, calendar
from datetime import date, datetime
import requests, streamlit as st
import matplotlib.pyplot as plt
from components.sidebar import render_sidebar
from components.home import render_home_section
from components.landing import show_landing
from components.wellness_chat import render_wellness_chat_section
from components.face_detection import render_face_detection_section
from components.relax import render_relax_section
from components.auth import render_auth_screen
from components.dashboard import render_dashboard_section
from reportlab.lib.pagesizes import letter
from components.journal import render_journal_section
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from db import (init_db, save_mood_log, save_manual_mood, MOOD_LABELS, MOOD_EMOJI,
                 get_mood_logs_for_month, get_user_mood_history,
                 get_all_employee_mood_logs, get_latest_mood_per_employee, save_face_scan)
from recommendations import get_period_recommendation
from auth import (make_token, read_token, get_user, username_taken, create_user,
                   verify_user, set_password, check_pw, new_otp, save_otp, check_otp)
from email_utils import send_otp

st.set_page_config(page_title="MoodMentor", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

BRAND_GREEN = "#1DBF73"
BRAND_GREEN_DARK = "#159c5e"
INK = "#1f2937"
MUTED = "#6b7280"
BG = "#f5f7f6"

MOOD_STYLE = {
    "Happy":   {"emoji": MOOD_EMOJI["Happy"],   "color": "#2ecc71"},
    "Neutral": {"emoji": MOOD_EMOJI["Neutral"], "color": "#3498db"},
    "Sad":     {"emoji": MOOD_EMOJI["Sad"],     "color": "#e67e22"},
    "Stress":  {"emoji": MOOD_EMOJI["Stress"],  "color": "#f1c40f"},
    "Angry":   {"emoji": MOOD_EMOJI["Angry"],   "color": "#e74c3c"},
    "Fear":    {"emoji": MOOD_EMOJI["Fear"],    "color": "#9b59b6"},
}
def style_for(label):
    return MOOD_STYLE.get(label, {"emoji": "", "color": "#bdbdbd"})

MOOD_TO_NUM = {"Happy": 2, "Neutral": 0, "Sad": -1, "Stress": -1, "Angry": -2, "Fear": -2}

def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

        header {visibility: hidden;}

        /* 1. True Professional Background - Soft Premium Gradient (No messy images) */
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%) !important;
            background-attachment: fixed !important;
            font-family: 'Outfit', sans-serif !important;
        }

        /* 2. Main Layout Container */
        .block-container {
            padding: 3rem 4rem !important;
            max-width: 1200px !important;
        }

        /* 3. The Sidebar - Deep Professional Slate */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
            border-right: 1px solid rgba(255,255,255,0.05) !important;
            box-shadow: 4px 0 24px rgba(0,0,0,0.1) !important;
        }

        /* Sidebar Text - Crisp White */
        [data-testid="stSidebar"] span, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div {
            color: #f8fafc !important;
            font-weight: 500 !important;
            font-size: 15px !important;
        }

        /* Sidebar Navigation Safe Styling */
        [data-testid="stSidebar"] div[role="radiogroup"] > label {
            background: transparent !important;
            padding: 12px 20px !important;
            border-radius: 12px !important;
            margin-bottom: 8px !important;
            border: none !important;
            box-shadow: none !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            background: rgba(255,255,255,0.05) !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] {
            background: #6366f1 !important; /* Indigo accent */
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
        }

        /* Remove any weird background from sidebar user info */
        [data-testid="stSidebar"] div[data-testid="stCaptionContainer"] {
            background: transparent !important;
            backdrop-filter: none !important;
            box-shadow: none !important;
        }

        /* 4. Typography Main Area - High Contrast */
        h1 { color: #0f172a !important; font-weight: 700 !important; font-size: 2.5rem !important; letter-spacing: -0.5px !important; }
        h2, h3 { color: #1e293b !important; font-weight: 600 !important; letter-spacing: -0.3px !important; }
        p { color: #475569 !important; font-size: 16px !important; }

        /* 5. Glassmorphism Metric Cards */
        .mm-metric {
            background: rgba(255, 255, 255, 0.7) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            border-radius: 24px !important;
            padding: 30px !important;
            border: 1px solid rgba(255, 255, 255, 0.8) !important;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.03) !important;
            text-align: left !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        }
        .mm-metric:hover {
            transform: translateY(-5px) !important;
            box-shadow: 0 15px 50px rgba(0, 0, 0, 0.05) !important;
            background: rgba(255, 255, 255, 0.9) !important;
        }
        .mm-metric .mm-value { color: #0f172a !important; font-size: 38px !important; font-weight: 700 !important; margin-top: 10px !important; }
        .mm-metric .mm-label { color: #6366f1 !important; font-size: 13px !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 1px; }

        /* 6. Fix Streamlit Radio Buttons (Emojis) */
        /* We will NOT try to turn them into massive blocks. We will style the container cleanly. */
        .stRadio > div[role="radiogroup"] {
            background: rgba(255, 255, 255, 0.5) !important;
            backdrop-filter: blur(10px) !important;
            padding: 20px !important;
            border-radius: 20px !important;
            border: 1px solid rgba(255, 255, 255, 0.8) !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.02) !important;
        }
        /* Style individual radio labels safely */
        .stRadio > div[role="radiogroup"] > label {
            background: transparent !important;
            padding: 10px 15px !important;
            border-radius: 10px !important;
            transition: all 0.2s ease !important;
            margin-right: 10px !important;
        }
        .stRadio > div[role="radiogroup"] > label:hover {
            background: rgba(255, 255, 255, 0.8) !important;
        }
        .stRadio > div[role="radiogroup"] > label[data-checked="true"] {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
        }

        /* 7. Buttons - Premium Solid Indigo */
        .stButton>button, .stFormSubmitButton>button {
            background: #6366f1 !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            padding: 0.6rem 2.5rem !important;
            font-weight: 600 !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
            transition: all 0.2s ease !important;
        }
        .stButton>button:hover, .stFormSubmitButton>button:hover {
            transform: translateY(-2px);
            background: #4f46e5 !important;
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important;
        }

        /* Secondary Buttons / Logout */
        [data-testid="stSidebar"] .stButton>button, button[kind="secondary"] {
            background: transparent !important;
            color: #f8fafc !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] .stButton>button:hover, button[kind="secondary"]:hover {
            background: rgba(255,255,255,0.1) !important;
            transform: translateY(0) !important;
        }

        /* 8. Container Cards */
        .welcome-box, .auth-card {
            background: rgba(255, 255, 255, 0.7) !important;
            backdrop-filter: blur(10px) !important;
            border-radius: 24px !important;
            padding: 40px !important;
            border: 1px solid rgba(255, 255, 255, 0.8) !important;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.03) !important;
        }
    </style>
    """, unsafe_allow_html=True)

def donut_chart(counts: dict, size=2.6):
    labels, values, colors = [], [], []
    for k, v in counts.items():
        if v > 0:
            labels.append(k); values.append(v)
            colors.append(style_for(k)["color"])
    if not values:
        return None
    fig, ax = plt.subplots(figsize=(size, size))
    ax.pie(values, colors=colors, startangle=90, wedgeprops=dict(width=0.38, edgecolor="white"))
    ax.set(aspect="equal")
    fig.patch.set_alpha(0.0)
    return fig

def metric_tile(label, value, sub=None):
    sub_html = f"<div class='mm-sub'>{sub}</div>" if sub else ""
    st.markdown(
        f"<div class='mm-metric'><div class='mm-label'>{label}</div>"
        f"<div class='mm-value'>{value}</div>{sub_html}</div>",
        unsafe_allow_html=True,
    )

def build_pdf_report(username, start_d, end_d, entries, recommendation_text):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=48, bottomMargin=48)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("MoodMentor Wellness Report", styles["Title"]))
    story.append(Paragraph(f"{username} &nbsp;|&nbsp; {start_d} to {end_d}", styles["Normal"]))
    story.append(Spacer(1, 16))

    counts = {}
    for h in entries:
        counts[h["sentiment"]] = counts.get(h["sentiment"], 0) + 1
    summary_line = ", ".join(f"{k}: {v}" for k, v in counts.items())
    story.append(Paragraph("Mood summary", styles["Heading2"]))
    story.append(Paragraph(f"{len(entries)} entries logged. {summary_line}.", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recommendation", styles["Heading2"]))
    story.append(Paragraph(recommendation_text, styles["Normal"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Entries", styles["Heading2"]))
    table_data = [["Date", "Time", "Mood", "Emotion", "Confidence", "Source"]]
    for h in sorted(entries, key=lambda r: r["created_at"], reverse=True):
        table_data.append([
            str(h["mood_date"]),
            h["created_at"].strftime("%H:%M"),
            h["sentiment"] or "\u2014",
            h.get("emotion") or "\u2014",
            f"{h['confidence']:.0%}" if h.get("confidence") is not None else "\u2014",
            h["source"],
        ])
    tbl = Table(table_data, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1DBF73")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7f6")]),
    ]))
    story.append(tbl)

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


inject_css()

@st.cache_resource
def setup(): init_db()
setup()

if "page" not in st.session_state: st.session_state.page = "welcome"
if "show_auth_panel" not in st.session_state: st.session_state.show_auth_panel = False
if "auth_mode" not in st.session_state: st.session_state.auth_mode = "login"
if "token" not in st.session_state: st.session_state.token = None
if "email" not in st.session_state: st.session_state.email = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "cal_year" not in st.session_state: st.session_state.cal_year = date.today().year
if "cal_month" not in st.session_state: st.session_state.cal_month = date.today().month
if "today_mood_saved" not in st.session_state: st.session_state.today_mood_saved = False
if "nav" not in st.session_state: st.session_state.nav = "Home"

def goto_auth(mode): st.session_state.auth_mode = mode; st.rerun()

def valid_pw(pw):
    return len(pw) >= 8 and re.search(r"[A-Za-z]", pw) and re.search(r"[0-9]", pw)


if st.session_state.token:
    user = read_token(st.session_state.token)
    if user:
        role = user.get("role", "employee")
        headers = {"Authorization": f"Bearer {st.session_state.token}"}

        if role == "employee":
            nav_options = ["Home", "Journal", "Wellness Chat", "Face Detection", "Relax", "Dashboard"]
        else:
            nav_options = ["Reports"]
        render_sidebar(user, role, nav_options)



        if role == "employee":
            section = st.session_state.nav

            if section == "Home":
                render_home_section(user)


            elif section == "Journal":
                render_journal_section(user, st.session_state.token)

            elif section == "Wellness Chat":
                render_wellness_chat_section(st.session_state.token)

            elif section == "Face Detection":
                render_face_detection_section(user)

            elif section == "Relax":
                render_relax_section(user)

            elif section == "Dashboard":
                render_dashboard_section(user, build_pdf_report)

        else:
            st.subheader("Employee Wellness Report")

            latest = get_latest_mood_per_employee()
            if not latest:
                st.info("No employee entries yet.")
            else:
                st.write("**Latest mood per employee**")
                table_rows = [{
                    "Employee": row["username"],
                    "Email": row["email"],
                    "Date": row["mood_date"],
                    "Time": row["created_at"].strftime("%H:%M"),
                    "Mood": f"{style_for(row['sentiment'])['emoji']} {row['sentiment']}",
                    "Emotion": row["emotion"],
                } for row in latest]
                st.dataframe(table_rows, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            st.write("**Team mood trend (last 30 days)**")
            history = get_all_employee_mood_logs(limit_days=30)
            if not history:
                st.info("Not enough data yet to draw a trend chart.")
            else:
                by_date = {}
                for row in history:
                    d = row["mood_date"]
                    by_date.setdefault(d, []).append(MOOD_TO_NUM.get(row["sentiment"], 0))
                trend = {str(d): sum(v) / len(v) for d, v in sorted(by_date.items())}
                st.line_chart(trend)
                st.caption("Average mood score per day across all employees "
                           "(2 = Happy, 0 = Neutral, -1 = Sad/Stress, -2 = Angry/Fear)")
            st.markdown("</div>", unsafe_allow_html=True)

        st.stop()
    st.session_state.token = None


if st.session_state.page == "welcome":

    if not st.session_state.show_auth_panel:
        show_landing()
        st.stop()

    render_auth_screen()

    st.stop()

