"""Streamlit prototype: keystroke-based continuous authentication.
Run:  streamlit run app.py
"""
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from features import events_to_features
from model import fit_profile, score, tier

PROFILE_DIR = Path("profiles")
PROFILE_DIR.mkdir(exist_ok=True)
MAX_SUSPICIOUS_IN_ROW = 3          # 3 suspicious attempts in a row -> lock

keystroke = components.declare_component("keystroke", path="components/keystroke")

st.set_page_config(page_title="Keystroke Continuous Auth", page_icon="⌨️")
st.title("⌨️ Continuous Authentication (Keystroke Dynamics)")

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
    user_id = st.text_input("User ID").strip()
    st.caption("Use a fixed password of 6-12 characters, lowercase letters/digits only "
               "(no Shift, no Backspace). Type it the way you normally do.")
    feats = read_attempt("enroll_box", ss.enroll_len)
    if feats is not None and not user_id:
        st.warning("Enter a User ID first, then retype.")
    elif feats is not None:
        if ss.enroll_len is None:
            ss.enroll_len = (len(feats) + 4) // 4      # features = 4n - 4 for n keys
        ss.enroll_rows.append(feats)
        st.rerun()

    st.progress(min(len(ss.enroll_rows) / 15, 1.0), text=f"{len(ss.enroll_rows)} / 15 attempts (min 5)")
    c1, c2 = st.columns(2)
    if c1.button("Train profile", disabled=len(ss.enroll_rows) < 5 or not user_id):
        prof = fit_profile(np.array(ss.enroll_rows))
        prof["password_len"] = ss.enroll_len
        joblib.dump(prof, PROFILE_DIR / f"live_{user_id}.joblib")
        ss.enroll_rows, ss.enroll_len = [], None
        st.success(f"Profile saved for '{user_id}'. Go to '2. Live session'.")
    if c2.button("Reset attempts"):
        ss.enroll_rows, ss.enroll_len = [], None
        st.rerun()

# ------------------------------------------------------------------ LIVE
else:
    st.subheader("Live session")
    users = sorted(p.stem[5:] for p in PROFILE_DIR.glob("live_*.joblib"))
    if not users:
        st.info("No profile yet. Enroll first.")
        st.stop()
    user_id = st.selectbox("Logged-in user", users)
    prof = joblib.load(PROFILE_DIR / f"live_{user_id}.joblib")

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
