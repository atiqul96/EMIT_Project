"""Turso (libSQL) storage: enrolled profiles and the live attempt log.
Uses Turso's HTTP API, so no native driver is needed.
Settings: TURSO_DATABASE_URL and TURSO_AUTH_TOKEN, from the environment or .streamlit/secrets.toml.
"""
import json
import os

import requests
import streamlit as st

LOG_COLUMNS = ["time", "user", "typist", "tester", "attempt", "score", "tier", "t_susp", "t_lock"]
TIMEOUT = 15   # seconds


def _setting(name):
    value = os.environ.get(name)
    if value:
        return value
    try:
        value = st.secrets.get(name)
    except Exception:       # no secrets.toml at all
        value = None
    if not value:
        raise RuntimeError(f"{name} is not set (see .streamlit/secrets.toml.example).")
    return value


def _encode(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    return {"type": "text", "value": str(value)}


def _decode(cell):
    if cell["type"] == "null":
        return None
    return int(cell["value"]) if cell["type"] == "integer" else cell["value"]


def _execute(sql, args=()):
    """Run one statement and return its rows as a list of dicts."""
    url = _setting("TURSO_DATABASE_URL").replace("libsql://", "https://", 1).rstrip("/")
    stmt = {"sql": sql, "args": [_encode(a) for a in args]}
    r = requests.post(f"{url}/v2/pipeline", timeout=TIMEOUT,
                      headers={"Authorization": f"Bearer {_setting('TURSO_AUTH_TOKEN')}"},
                      json={"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]})
    r.raise_for_status()
    first = r.json()["results"][0]
    if first["type"] == "error":
        raise RuntimeError(f"Turso error: {first['error']['message']}")
    result = first["response"]["result"]
    cols = [c["name"] for c in result["cols"]]
    return [dict(zip(cols, map(_decode, row))) for row in result["rows"]]


def init_schema():
    _execute("""CREATE TABLE IF NOT EXISTS profiles (
                    email TEXT PRIMARY KEY,
                    password_len INTEGER NOT NULL,
                    features TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
    _execute("""CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT, user TEXT, typist TEXT, tester TEXT, attempt INTEGER,
                    score REAL, tier TEXT, t_susp REAL, t_lock REAL)""")


def save_profile(email, rows, password_len):
    _execute("INSERT INTO profiles (email, password_len, features) VALUES (?, ?, ?)",
             (email, password_len, json.dumps(rows)))


def profile_exists(email):
    return bool(_execute("SELECT 1 FROM profiles WHERE email = ?", (email,)))


def list_users():
    return [r["email"] for r in _execute("SELECT email FROM profiles ORDER BY email")]


def load_enrollment(email):
    """Return (feature rows, password length) for one enrolled user."""
    row = _execute("SELECT features, password_len FROM profiles WHERE email = ?", (email,))[0]
    return json.loads(row["features"]), row["password_len"]


def log_attempt(*values):
    """values: one entry per LOG_COLUMNS."""
    marks = ", ".join("?" * len(LOG_COLUMNS))
    _execute(f"INSERT INTO attempts ({', '.join(LOG_COLUMNS)}) VALUES ({marks})", values)


def fetch_attempts():
    return _execute(f"SELECT {', '.join(LOG_COLUMNS)} FROM attempts ORDER BY id")
