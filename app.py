"""Streamlit prototype: keystroke-based continuous authentication.
Run:  streamlit run app.py
"""
import re
import time
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import db
from features import events_to_features
from model import fit_profile, score, tier

MAX_SUSPICIOUS_IN_ROW = 3         # 3 suspicious attempts in a row -> lock
MAX_EMAIL_LEN = 100
EMAIL_RE = re.compile(r"[a-z0-9_%+-]+(\.[a-z0-9_%+-]+)*@([a-z0-9]+(-+[a-z0-9]+)*\.)+[a-z]{2,}")

keystroke = components.declare_component("keystroke", path="components/keystroke")

st.set_page_config(page_title="Keystroke Continuous Auth", page_icon="⌨️")
st.title(" Continuous Authentication (Keystroke Dynamics)")
st.caption("Public research demo. Only key press/release TIMINGS are sent to the server, "
           "never the characters. Still, please use a made-up password, not a real one.")


@st.cache_resource(show_spinner=False)
def connect_db():
    db.init_schema()


@st.cache_resource(show_spinner="Loading profile...")
def load_profile(email):
    """Rebuild the model from the stored timings (fit_profile is deterministic)."""
    rows, password_len = db.load_enrollment(email)
    return {**fit_profile(np.array(rows)), "password_len": password_len}


try:
    connect_db()
except Exception as e:
    st.error(f"Could not reach the database: {e}")
    st.stop()

ss = st.session_state
ss.setdefault("enroll_rows", [])
ss.setdefault("last_t", None)
ss.setdefault("history", [])       # list of (score, tier)
ss.setdefault("locked", False)
ss.setdefault("susp_run", 0)
ss.setdefault("enroll_len", None)   # number of keys in the password


def read_attempt(key, expected_len):
    """Return a feature list for a NEW valid attempt, else None (with a message)."""
    val = keystroke(key=key)
    if not val or val.get("t") == ss.last_t:
        return None
    ss.last_t = val["t"]
    if val["bad"]:
        st.warning("Backspace/paste used - attempt ignored. Retype from the start.")
        return None
    if expected_len and len(val["events"]) != expected_len:
        st.warning(f"Expected {expected_len} keys, got {len(val['events'])} - attempt ignored.")
        return None
    if len(val["events"]) < 4:
        st.warning("Password too short (use at least 6 characters).")
        return None
    return events_to_features(val["events"])


page = st.sidebar.radio("Page", ["1. Enroll", "2. Live session"])

# ------------------------------------------------------------------ ENROLL
if page == "1. Enroll":
    st.subheader("Enroll: retype your password 5-15 times (15 is more accurate)")
    raw_email = st.text_input("Email", placeholder="name@example.com").strip().lower()
    valid = len(raw_email) <= MAX_EMAIL_LEN and EMAIL_RE.fullmatch(raw_email)
    user_id = raw_email if valid else ""
    if raw_email and not valid:
        st.error("Enter a valid email address, e.g. name@example.com.")
    taken = bool(user_id) and db.profile_exists(user_id)
    if taken:
        st.error(f"'{user_id}' is already enrolled - use another email.")
    st.caption("Use a fixed password of 6-12 characters, lowercase letters/digits only "
               "(no Shift, no Backspace). Type it the way you normally do.")
    feats = read_attempt("enroll_box", ss.enroll_len)
    if feats is not None and not user_id:
        st.warning("Enter a valid email first, then retype.")
    elif feats is not None:
        if ss.enroll_len is None:
            ss.enroll_len = (len(feats) + 4) // 4      # features = 4n - 4 for n keys
        ss.enroll_rows.append(feats)
        st.rerun()

    st.progress(min(len(ss.enroll_rows) / 15, 1.0), text=f"{len(ss.enroll_rows)} / 15 attempts (min 5)")
    c1, c2 = st.columns(2)
    if c1.button("Train profile", disabled=len(ss.enroll_rows) < 5 or not user_id or taken):
        db.save_profile(user_id, np.array(ss.enroll_rows).tolist(), ss.enroll_len)
        ss.enroll_rows, ss.enroll_len = [], None
        st.success(f"Profile saved for '{user_id}'. Go to '2. Live session'.")
    if c2.button("Reset attempts"):
        ss.enroll_rows, ss.enroll_len = [], None
        st.rerun()

# ------------------------------------------------------------------ LIVE
else:
    st.subheader("Live session")
    users = db.list_users()
    if not users:
        st.info("No profile yet. Enroll first.")
        st.stop()
    st.caption("Pick your own profile to test yourself")
    user_id = st.selectbox("Logged-in user", users)
    prof = load_profile(user_id)

    if ss.locked:
        st.error("🔴 SESSION LOCKED - possible hijack. Session terminated.")
        if st.button("Unlock (demo reset)"):
            ss.locked, ss.history, ss.susp_run = False, [], 0
            st.rerun()
        st.stop()

    st.write("Keep typing your password again and again (re-verification). "
             "Let a friend type it to simulate a hijack.")
    feats = read_attempt("live_box", prof["password_len"])
    if feats is not None:
        s = score(prof, feats)
        t = tier(s, prof)
        ss.susp_run = ss.susp_run + 1 if t == "SUSPICIOUS" else 0
        if t == "SUSPICIOUS" and ss.susp_run >= MAX_SUSPICIOUS_IN_ROW:
            t = "LOCKED"
        ss.history.append((s, t))
        # db.log_attempt(datetime.now().isoformat(timespec="seconds"), user_id, typist,
        #                tester, len(ss.history), round(s, 4), t,
        #                round(prof["t_susp"], 4), round(prof["t_lock"], 4))
        if t == "LOCKED":
            ss.locked = True
        st.rerun()

    if ss.history:
        s, t = ss.history[-1]
        {"NORMAL": st.success, "SUSPICIOUS": st.warning, "LOCKED": st.error}[t](
            f"{ {'NORMAL': '🟢', 'SUSPICIOUS': '🟠', 'LOCKED': '🔴'}[t] } {t}   (score {s:.3f})")
        df = pd.DataFrame({"anomaly score": [h[0] for h in ss.history],
                           "suspicious threshold": prof["t_susp"],
                           "lock threshold": prof["t_lock"]})
        st.line_chart(df)
    else:
        st.info("Waiting for the first attempt...")
