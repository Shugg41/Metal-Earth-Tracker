import streamlit as st
import sqlite3
import pandas as pd
import requests
import base64
import io
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
# PAGE CONFIG & THEME
# ─────────────────────────────────────────────
st.set_page_config(page_title="Metal Earth Workbench", layout="wide", page_icon="⚙️")

st.markdown("""
<style>
/* ── Theme: black + hunter green (all colors defined here) ── */
:root {
    --bg:           #0c0e0c;   /* near-black, faint green cast */
    --surface:      #151a15;   /* cards, buttons, inputs */
    --surface2:     #182018;   /* zero-intensity heatmap, hover */
    --border:       #263226;   /* dark green-gray lines */
    --accent:       #7fae7a;   /* light hunter green — text & lines on black */
    --accent-deep:  #3f6f4f;   /* dark hunter green — fills */
    --accent-hover: #8fbe8a;
    --khaki:        #b3a878;   /* camo tan — badges, secondary */
    --amber:        #d9a441;   /* In Progress */
    --done:         #66bb6a;   /* Completed */
    --text:         #e0e0e0;
    --muted:        #888;
}

/* ── Dark base ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
}
[data-testid="stSidebar"] { background-color: var(--surface) !important; }
[data-testid="stHeader"]  { background-color: var(--bg) !important; }

/* ── Phone-first density ── */
.block-container { padding-top: 2.2rem !important; padding-bottom: 2rem !important; }
hr { border-color: var(--border) !important; margin: 0.6rem 0 !important; }
[data-testid="stToolbar"] { display: none !important; }  /* hide Deploy/menu chrome */

/* ── Headings ── */
h1, h2, h3, h4 { color: var(--accent) !important; font-family: 'Georgia', serif; letter-spacing: 1px; }
h2 { font-size: 1.35rem !important; }

/* ── One-line header widgets ── */
.brand-line { color: var(--accent); font-family: 'Georgia', serif; font-size: 1.1rem;
              font-weight: 700; letter-spacing: 1px; margin: 0; }
.stats-line { color: var(--muted); font-size: 0.8rem; margin: 2px 0 8px 0; }
.stats-line b { color: var(--khaki); font-weight: 600; }

/* ── Keyed nowrap containers: keep their columns on ONE row on phones ──
   Streamlit stacks columns below ~640px; for containers whose key starts
   with "nowrap" we keep the row layout (nav bar, back row, log rows). */
div[class*="st-key-nowrap"] [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    gap: 0.4rem !important;
}
div[class*="st-key-nowrap"] [data-testid="stColumn"],
div[class*="st-key-nowrap"] [data-testid="column"] {
    width: auto !important;
    min-width: 0 !important;
}
div[class*="st-key-nowrap"] .stButton > button {
    padding: 0.25rem 0.4rem !important;
    font-size: 0.85rem !important;
}

/* ── Metric tiles (Stats page) ── */
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 16px;
}
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }
[data-testid="stMetricValue"] { color: var(--accent) !important; font-size: 1.6rem; font-weight: 700; }

/* ── Buttons ── */
.stButton > button {
    background: var(--surface) !important;
    color: var(--accent) !important;
    border: 1px solid var(--accent-deep) !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: var(--accent-deep) !important;
    color: #eaf5e8 !important;
}
/* Primary buttons */
.stButton > button[kind="primary"] {
    background: var(--accent-deep) !important;
    color: #eaf5e8 !important;
    border: 1px solid var(--accent-deep) !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--accent) !important;
    color: #0c0e0c !important;
}

/* ── Inputs ── */
input, textarea, [data-baseweb="select"] {
    background-color: var(--surface) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
    border-radius: 6px !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tab"], [data-testid="stTabs"] [role="tab"] p {
    color: var(--muted) !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"],
[data-testid="stTabs"] [role="tab"][aria-selected="true"] p {
    color: var(--accent) !important;
}
[data-baseweb="tab-highlight"] { background-color: var(--accent) !important; }
[data-baseweb="tab-border"]    { background-color: var(--border) !important; }

/* ── Expanders ── */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

/* ── Model cards ── */
.model-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 6px;
    transition: border-color 0.2s, background 0.2s;
}
.model-card:hover { border-color: var(--accent); background: var(--surface2); }
.model-card-title { color: var(--text); font-size: 1rem; font-weight: 600; margin-bottom: 3px; }
.model-card-meta  { color: var(--muted); font-size: 0.78rem; }

/* ── Currently building banner ── */
.building-banner {
    background: linear-gradient(135deg, #101810, #1a2a1a);
    border: 2px solid var(--accent-deep);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
}
.building-banner-title { color: var(--accent); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 6px; }
.building-banner-name  { color: #fff; font-size: 1.1rem; font-weight: 700; }

/* ── Stopwatch display ── */
.stopwatch {
    background: #0e120e;
    border: 2px solid var(--accent-deep);
    border-radius: 16px;
    text-align: center;
    padding: 26px;
    margin: 12px 0;
}
.stopwatch-time {
    font-size: 2.6rem;
    font-weight: 700;
    color: var(--accent);
    font-family: 'Courier New', monospace;
    letter-spacing: 2px;
    white-space: nowrap;
}
.stopwatch-label { color: #667a66; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 2px; margin-top: 8px; }

/* ── Stats cards / chips ── */
.stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    margin-bottom: 12px;
}
.stat-card-value { color: var(--accent); font-size: 2rem; font-weight: 700; }
.stat-card-label { color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
.stat-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 4px; }
.stat-chip {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 12px;
    flex: 1 1 28%;
    text-align: center;
}
.stat-chip-value { color: var(--accent); font-size: 1.15rem; font-weight: 700; }
.stat-chip-label { color: var(--muted); font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1px; }

/* ── Journal timeline ── */
.journal-entry {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent-deep);
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
}
.journal-date { color: var(--khaki); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; }
.journal-body { color: var(--text); font-size: 0.9rem; margin-top: 3px; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border: 1px solid var(--border) !important; border-radius: 8px !important; }

/* ── Success/info/warning ── */
[data-testid="stAlert"] { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GITHUB HELPERS
# ─────────────────────────────────────────────
def gh_headers():
    token = st.secrets.get("GITHUB_TOKEN", "")
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

def gh_repo():
    return st.secrets.get("GITHUB_REPO", "")

def pull_db_from_github():
    try:
        repo = gh_repo()
        if not repo: return False
        url = f"https://api.github.com/repos/{repo}/contents/models_db.db"
        r = requests.get(url, headers=gh_headers(), timeout=15)
        if r.status_code == 200:
            db_bytes = base64.b64decode(r.json()["content"])
            with open("models_db.db", "wb") as f:
                f.write(db_bytes)
            return True
        return False
    except Exception:
        return False

def push_db_to_github():
    try:
        repo = gh_repo()
        if not repo: return False
        with open("models_db.db", "rb") as f:
            db_bytes = f.read()
        b64 = base64.b64encode(db_bytes).decode("utf-8")
        url = f"https://api.github.com/repos/{repo}/contents/models_db.db"
        r   = requests.get(url, headers=gh_headers(), timeout=10)
        sha = r.json().get("sha") if r.status_code == 200 else None
        payload = {"message": f"Update database {datetime.now().strftime('%Y-%m-%d %H:%M')}", "content": b64}
        if sha: payload["sha"] = sha
        r2 = requests.put(url, headers=gh_headers(), json=payload, timeout=30)
        return r2.status_code in (200, 201)
    except Exception:
        return False

def upload_to_github(image_bytes, filename):
    try:
        repo = gh_repo()
        if not repo: return None, "GITHUB_REPO not set."
        path    = f"photos/{filename}"
        api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
        check   = requests.get(api_url, headers=gh_headers(), timeout=10)
        sha     = check.json().get("sha") if check.status_code == 200 else None
        b64     = base64.b64encode(image_bytes).decode("utf-8")
        payload = {"message": f"Add photo: {filename}", "content": b64}
        if sha: payload["sha"] = sha
        response = requests.put(api_url, headers=gh_headers(), json=payload, timeout=20)
        if response.status_code in (200, 201):
            return f"https://raw.githubusercontent.com/{repo}/main/{path}", None
        return None, response.json().get("message", "Upload failed.")
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# STARTUP — pull DB from GitHub once per SERVER boot, not per browser visit.
# This server is the only writer, so once it has the DB its local copy is
# always at least as new as GitHub's — re-pulling on every open just made
# each visit slower (and could clobber local changes whose push had failed).
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading your workshop...")
def _startup_pull():
    pull_db_from_github()
    return True

_startup_pull()

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────
conn = sqlite3.connect('models_db.db', check_same_thread=False)
c    = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS Models
             (model_id       TEXT PRIMARY KEY,
              name           TEXT,
              category       TEXT,
              sheets         REAL,
              status         TEXT DEFAULT 'Not Started',
              difficulty     TEXT,
              difficulty_num INTEGER,
              rating         INTEGER DEFAULT 0,
              notes          TEXT,
              last_worked    TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS Build_Logs
             (log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
              model_id    TEXT,
              start_time  TEXT,
              duration    REAL,
              notes       TEXT,
              is_estimate INTEGER DEFAULT 0)''')

# Migration: add is_estimate to pre-existing DBs that don't have it yet
_existing_cols = [row[1] for row in c.execute("PRAGMA table_info(Build_Logs)").fetchall()]
if 'is_estimate' not in _existing_cols:
    c.execute("ALTER TABLE Build_Logs ADD COLUMN is_estimate INTEGER DEFAULT 0")
    conn.commit()

c.execute('''CREATE TABLE IF NOT EXISTS Photos
             (photo_id    INTEGER PRIMARY KEY AUTOINCREMENT,
              model_id    TEXT,
              url         TEXT,
              caption     TEXT,
              uploaded_at TEXT)''')

# Active timer table — persists across browser sessions
c.execute('''CREATE TABLE IF NOT EXISTS Active_Timer
             (id         INTEGER PRIMARY KEY,
              model_id   TEXT,
              start_time TEXT)''')

# Small key-value store for app state (e.g. last opened model)
c.execute('''CREATE TABLE IF NOT EXISTS App_State
             (key   TEXT PRIMARY KEY,
              value TEXT)''')

conn.commit()

def get_app_state(key):
    row = c.execute("SELECT value FROM App_State WHERE key=?", (key,)).fetchone()
    return row[0] if row else None

def set_app_state(key, value):
    # Local commit only — not worth a GitHub commit per navigation. The value
    # becomes durable whenever the next real save pushes the DB.
    if get_app_state(key) != value:
        c.execute("INSERT OR REPLACE INTO App_State (key, value) VALUES (?,?)", (key, value))
        conn.commit()

# ─────────────────────────────────────────────
# SAVE HELPER
# ─────────────────────────────────────────────
def save():
    """Commit locally, then push to GitHub. Returns True only if the remote
    push succeeded — local commits alone are NOT safe, because the container
    is ephemeral and the only durable copy of the DB lives on GitHub."""
    conn.commit()
    return push_db_to_github()

# ─────────────────────────────────────────────
# GOOGLE SHEETS SYNC (optional, via Apps Script webhook)
# ─────────────────────────────────────────────
def gsheet_webhook():
    return st.secrets.get("GSHEET_WEBHOOK_URL", "")

def _tab_payload(df):
    """Serialize a DataFrame to {columns, rows} with JSON-native types
    (to_json handles NaN -> null and numpy -> native, which raw .tolist() does not)."""
    obj = json.loads(df.to_json(orient="split"))
    return {"columns": obj["columns"], "rows": obj["data"]}

def sync_to_sheet():
    """Push a full snapshot of the collection to the user's Google Sheet via
    their Apps Script web app. Best-effort — returns (ok, message)."""
    url = gsheet_webhook()
    if not url:
        return False, "No GSHEET_WEBHOOK_URL configured."
    try:
        models = pd.read_sql_query("SELECT * FROM Models ORDER BY model_id", conn)
        logs   = pd.read_sql_query("SELECT * FROM Build_Logs ORDER BY model_id, start_time", conn)
        photos = pd.read_sql_query("SELECT * FROM Photos ORDER BY model_id, uploaded_at", conn)
        payload = {
            "secret": st.secrets.get("GSHEET_SECRET", ""),
            "tabs": {
                "Models":     _tab_payload(models),
                "Build Logs": _tab_payload(logs),
                "Photos":     _tab_payload(photos),
            },
        }
        # Apps Script 302-redirects to googleusercontent; requests follows it.
        r = requests.post(url, json=payload, timeout=15)
        try:
            ok_flag = (r.json().get("status") == "ok")
        except Exception:
            ok_flag = r.ok
        return (True, "Synced.") if ok_flag else (False, f"HTTP {r.status_code}: {r.text[:150]}")
    except Exception as e:
        return False, str(e)

# Paste-able Apps Script for the user's Google Sheet (shown on the Export page).
APPS_SCRIPT_CODE = '''const SECRET = "";  // optional: set a password, then put the same value in GSHEET_SECRET

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    if (SECRET && body.secret !== SECRET) {
      return ContentService
        .createTextOutput(JSON.stringify({status: "error", message: "bad secret"}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const tabs = body.tabs || {};
    Object.keys(tabs).forEach(function (name) {
      let sheet = ss.getSheetByName(name);
      if (!sheet) sheet = ss.insertSheet(name);
      sheet.clearContents();
      const cols = tabs[name].columns || [];
      const rows = tabs[name].rows || [];
      const data = [cols].concat(rows);
      if (cols.length) {
        sheet.getRange(1, 1, data.length, cols.length).setValues(data);
      }
    });
    return ContentService
      .createTextOutput(JSON.stringify({status: "ok"}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({status: "error", message: String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}'''

def save_and_report(success_msg="Saved!"):
    """Save and surface the real outcome to the user. On failure we never
    claim success — the change is local-only and at risk until it syncs."""
    with st.spinner("Saving..."):
        ok = save()
    if ok:
        st.session_state['unsynced'] = False
        if success_msg:
            st.success(success_msg)
        # Best-effort live mirror to the user's Google Sheet, only if a webhook
        # is configured. Never blocks or fails the save — just a toast either way.
        if gsheet_webhook():
            sok, smsg = sync_to_sheet()
            st.toast("📊 Google Sheet updated" if sok else f"⚠️ Sheet sync failed: {smsg}")
    else:
        st.session_state['unsynced'] = True
        st.error(
            "⚠️ Saved on this device, but the **GitHub sync failed** — this change "
            "is not backed up and may be lost if the app restarts. Check your "
            "connection and GITHUB_TOKEN, then use **Retry sync** at the top.")
    return ok

# ─────────────────────────────────────────────
# QUERY HELPERS
# ─────────────────────────────────────────────
STATUS_OPTIONS = ['Not Started', 'In Progress', 'Completed', 'On Hold']
STATUS_EMOJI   = {'Not Started': '⬜', 'In Progress': '🔧', 'Completed': '✅', 'On Hold': '⏸️'}

def get_all_models():
    return pd.read_sql_query("SELECT * FROM Models ORDER BY last_worked DESC NULLS LAST", conn)

def get_model(model_id):
    df = pd.read_sql_query("SELECT * FROM Models WHERE model_id=?", conn, params=(model_id,))
    return df.iloc[0] if not df.empty else None

def get_logs(model_id):
    return pd.read_sql_query(
        "SELECT * FROM Build_Logs WHERE model_id=? ORDER BY start_time DESC", conn, params=(model_id,))

def get_photos(model_id):
    return pd.read_sql_query(
        "SELECT * FROM Photos WHERE model_id=? ORDER BY uploaded_at DESC", conn, params=(model_id,))

def total_time_seconds(model_id):
    logs = get_logs(model_id)
    return logs['duration'].sum() if not logs.empty else 0

def get_active_timer():
    row = c.execute("SELECT model_id, start_time FROM Active_Timer WHERE id=1").fetchone()
    return row if row else None

def set_active_timer(model_id, start_time_str):
    c.execute("DELETE FROM Active_Timer")
    c.execute("INSERT INTO Active_Timer (id, model_id, start_time) VALUES (1,?,?)",
              (model_id, start_time_str))
    ok = save()
    if not ok:
        st.session_state['unsynced'] = True
    return ok

def clear_active_timer():
    c.execute("DELETE FROM Active_Timer")
    ok = save()
    if not ok:
        st.session_state['unsynced'] = True
    return ok

def safe_int(val):
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)): return None
        return int(val)
    except (ValueError, TypeError):
        return None

def safe_float(val):
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)): return None
        return float(val)
    except (ValueError, TypeError):
        return None

def fmt_seconds(secs):
    secs = int(secs)
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m:02d}m {s:02d}s"

# ─────────────────────────────────────────────
# NAVIGATION STATE
# ─────────────────────────────────────────────
def _model_exists(mid):
    return mid and c.execute("SELECT 1 FROM Models WHERE model_id=?", (mid,)).fetchone()

if 'page' not in st.session_state:
    # Timer first: on app open, land on the stopwatch of the model you're
    # working on. Priority: running timer → last opened → single In Progress.
    timer_row = get_active_timer()
    land_on = None
    if timer_row and _model_exists(timer_row[0]):
        land_on = timer_row[0]
    if not land_on:
        last_opened = get_app_state('last_opened_model')
        if _model_exists(last_opened):
            land_on = last_opened
    if not land_on:
        in_progress = pd.read_sql_query(
            "SELECT model_id FROM Models WHERE status='In Progress' LIMIT 2", conn)
        if len(in_progress) == 1:
            land_on = in_progress.iloc[0]['model_id']
    if land_on:
        st.session_state.page = 'workbench'
        st.session_state.selected_model = land_on
    else:
        st.session_state.page = 'inventory'
        st.session_state.selected_model = None

# ─────────────────────────────────────────────
# HEADER & GLOBAL STATS
# ─────────────────────────────────────────────
all_models    = get_all_models()
total_secs_db = pd.read_sql_query("SELECT SUM(duration) as s FROM Build_Logs", conn)['s'].iloc[0] or 0

# Add active timer seconds if running
active_timer = get_active_timer()
if active_timer:
    timer_start_dt = datetime.fromisoformat(active_timer[1])
    live_elapsed   = (datetime.now() - timer_start_dt).total_seconds()
    total_secs_db += live_elapsed

total_hours = round(total_secs_db / 3600, 1)
completed   = len(all_models[all_models['status'] == 'Completed']) if not all_models.empty else 0

# Compact one-line header: brand + hours/completed. Everything else lives on Stats.
st.markdown(f"""
<div class='brand-line'>⚙️ Metal Earth Workbench</div>
<div class='stats-line'>⏱ <b>{total_hours}h</b> built &nbsp;·&nbsp; ✅ <b>{completed}</b> done</div>
""", unsafe_allow_html=True)

# Top nav — nowrap keyed container keeps these on one row on phones.
# "⏱ Build" jumps back to the model you're working on, from anywhere.
build_target = None
_timer_row = get_active_timer()
if _timer_row and _model_exists(_timer_row[0]):
    build_target = _timer_row[0]
elif _model_exists(get_app_state('last_opened_model')):
    build_target = get_app_state('last_opened_model')

with st.container(key="nowrap_topnav"):
    if build_target:
        nb, n1, n2, n3 = st.columns(4)
        with nb:
            if st.button("⏱ Build", use_container_width=True, type="primary"):
                st.session_state.page = 'workbench'
                st.session_state.selected_model = build_target
                st.rerun()
    else:
        n1, n2, n3 = st.columns(3)
    with n1:
        if st.button("📦 Kits", use_container_width=True):
            st.session_state.page = 'inventory'
            st.session_state.selected_model = None
            st.rerun()
    with n2:
        if st.button("📊 Stats", use_container_width=True):
            st.session_state.page = 'stats'
            st.session_state.selected_model = None
            st.rerun()
    with n3:
        if st.button("📤 Export", use_container_width=True):
            st.session_state.page = 'export'
            st.session_state.selected_model = None
            st.rerun()

# If a previous save couldn't reach GitHub, the DB is committed locally but
# not backed up. Give the user a one-click recovery instead of silent loss.
if st.session_state.get('unsynced'):
    uc1, uc2 = st.columns([4, 1])
    uc1.warning("⚠️ Some changes aren't backed up to GitHub yet — they'll be lost if the app restarts.")
    with uc2:
        if st.button("🔁 Retry sync", use_container_width=True, type="primary"):
            if push_db_to_github():
                st.session_state['unsynced'] = False
                st.rerun()
            else:
                st.error("Still can't reach GitHub. Check your network and GITHUB_TOKEN.")

st.divider()

# ─────────────────────────────────────────────
# INVENTORY PAGE
# ─────────────────────────────────────────────
if st.session_state.page == 'inventory':

    # ── Currently Building banner (full-width, phone-friendly) ──
    in_progress_models = all_models[all_models['status'] == 'In Progress'] if not all_models.empty else pd.DataFrame()
    # Two GROUP BY queries replace the per-card get_photos/get_logs lookups
    # (previously 2+ queries per model on every rerun).
    time_by_model = dict(c.execute(
        "SELECT model_id, SUM(duration) FROM Build_Logs GROUP BY model_id").fetchall())
    photos_by_model = dict(c.execute(
        "SELECT model_id, COUNT(*) FROM Photos GROUP BY model_id").fetchall())

    if not in_progress_models.empty:
        st.markdown("<div style='color:var(--accent);font-size:0.7rem;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px'>🔧 Currently Building</div>", unsafe_allow_html=True)
        for _, brow in in_progress_models.head(3).iterrows():
            secs = time_by_model.get(brow['model_id']) or 0
            # Add live timer if this model is active
            if active_timer and active_timer[0] == brow['model_id']:
                timer_start_dt = datetime.fromisoformat(active_timer[1])
                secs += (datetime.now() - timer_start_dt).total_seconds()
            time_str = fmt_seconds(secs) if secs > 0 else "Not started"
            st.markdown(f"""
            <div class='building-banner'>
                <div class='building-banner-title'>In Progress</div>
                <div class='building-banner-name'>{brow['name']}</div>
                <div style='color:#888;font-size:0.8rem;margin-top:4px'>⏱ {time_str} logged</div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"▶ Open {brow['name']}", key=f"banner_{brow['model_id']}", use_container_width=True):
                st.session_state.selected_model = brow['model_id']
                st.session_state.page = 'workbench'
                st.rerun()
        st.divider()

    st.markdown("<h2>📦 My Collection</h2>", unsafe_allow_html=True)

    with st.expander("➕ Add a Model to Your Collection"):
        with st.form("add_model", clear_on_submit=True):
            search_id  = st.text_input("Model ID (e.g. ME1054 or MMS073)").strip().upper()
            name_input = st.text_input("Name")
            cat_input  = st.text_input("Category")
            diff_input = st.text_input("Difficulty")
            sheets_val = st.number_input("Sheets", min_value=0.0, step=0.5, value=0.0)

            if st.form_submit_button("Add to Collection"):
                if not search_id:
                    st.error("Please enter a Model ID.")
                elif not name_input:
                    st.error("Please enter a Name.")
                else:
                    exists = c.execute("SELECT 1 FROM Models WHERE model_id=?", (search_id,)).fetchone()
                    if exists:
                        st.warning(f"{search_id} is already in your collection.")
                    else:
                        c.execute(
                            """INSERT INTO Models
                               (model_id, name, category, sheets, status,
                                difficulty, difficulty_num, last_worked)
                               VALUES (?,?,?,?,?,?,?,?)""",
                            (search_id, name_input, cat_input, sheets_val if sheets_val > 0 else None,
                             'Not Started', diff_input, None,
                             str(datetime.now().date())))
                        if save_and_report(f"Added {name_input}!"):
                            st.rerun()

    # Filters — collapsed by default to keep the phone view short
    all_models = get_all_models()
    with st.expander("🔍 Filter & sort"):
        status_filter = st.selectbox("Filter by Status", ['All'] + STATUS_OPTIONS)
        cats = ['All'] + sorted(all_models['category'].dropna().unique().tolist()) if not all_models.empty else ['All']
        cat_filter = st.selectbox("Filter by Category", cats)
        sort_by = st.selectbox("Sort by", ['Last Worked', 'Name', 'Difficulty', 'Category', 'Status'])

    display_df = all_models.copy()
    if status_filter != 'All':
        display_df = display_df[display_df['status'] == status_filter]
    if cat_filter != 'All':
        display_df = display_df[display_df['category'] == cat_filter]

    sort_map = {'Last Worked': 'last_worked', 'Name': 'name',
                'Difficulty': 'difficulty_num', 'Category': 'category', 'Status': 'status'}
    display_df = display_df.sort_values(sort_map[sort_by], ascending=True)

    if display_df.empty:
        st.info("No models yet — add one above!")
    else:
        # Model cards — single-column compact list (phone-first)
        for _, row in display_df.iterrows():
            emoji      = STATUS_EMOJI.get(row['status'], '⬜')
            diff_str   = row['difficulty'] if row['difficulty'] else '—'
            photo_icon = " 📸" if photos_by_model.get(row['model_id']) else ""
            secs       = time_by_model.get(row['model_id']) or 0
            time_str   = fmt_seconds(secs) if secs > 0 else "—"

            # Is this the active timer model?
            timer_icon = ""
            if active_timer and active_timer[0] == row['model_id']:
                timer_icon = " ⏱️"

            status_color = {
                'In Progress': 'var(--amber)', 'Completed': 'var(--done)',
                'Not Started': '#666',    'On Hold': '#888'
            }.get(row['status'], '#666')

            st.markdown(f"""
            <div class='model-card'>
                <div class='model-card-title'>{emoji} {row['name']}{photo_icon}{timer_icon}</div>
                <div class='model-card-meta'>
                    <span style='color:{status_color};font-weight:600'>{row['status']}</span>
                    &nbsp;·&nbsp; ⏱ {time_str} &nbsp;·&nbsp; {row['model_id']} &nbsp;·&nbsp; {row['category'] or '—'} &nbsp;·&nbsp; {diff_str}
                </div>
            </div>""", unsafe_allow_html=True)
            if st.button("Open →", key=f"btn_{row['model_id']}", use_container_width=True):
                st.session_state.selected_model = row['model_id']
                st.session_state.page = 'workbench'
                st.rerun()

# ─────────────────────────────────────────────
# STATS PAGE
# ─────────────────────────────────────────────
elif st.session_state.page == 'stats':
    st.markdown("<h2>📊 Workshop Stats</h2>", unsafe_allow_html=True)

    all_models = get_all_models()
    all_logs   = pd.read_sql_query("SELECT * FROM Build_Logs", conn)

    if all_models.empty:
        st.info("Add some models to see your stats!")
    else:
        # ── Top row stats ──
        # Split logs: estimates count toward total hours only; real sessions
        # drive the session count, average, and heatmap.
        if not all_logs.empty and 'is_estimate' in all_logs.columns:
            real_logs = all_logs[all_logs['is_estimate'].fillna(0) == 0]
        else:
            real_logs = all_logs

        total_sheets     = all_models['sheets'].sum() if 'sheets' in all_models.columns else 0
        total_build_secs = all_logs['duration'].sum() if not all_logs.empty else 0
        avg_session_mins = round((real_logs['duration'].mean() or 0) / 60, 1) if not real_logs.empty else 0
        total_sessions   = len(real_logs)
        est_count        = len(all_logs) - len(real_logs)
        total_photos     = pd.read_sql_query("SELECT COUNT(*) as n FROM Photos", conn)['n'].iloc[0] or 0
        n_in_progress    = len(all_models[all_models['status'] == 'In Progress'])

        # Compact wrapping stat chips (3-up on phones) instead of stacked tiles
        chips = [
            (f"{round(total_build_secs/3600, 1)}h", "Hours Built"),
            (total_sessions,                        "Sessions"),
            (f"{avg_session_mins}m",                "Avg Session"),
            (len(all_models),                       "Kits Owned"),
            (n_in_progress,                         "Building"),
            (f"{int(total_sheets or 0)}",           "Sheets"),
            (total_photos,                          "Photos"),
        ]
        chips_html = "".join(
            f"<div class='stat-chip'><div class='stat-chip-value'>{v}</div>"
            f"<div class='stat-chip-label'>{l}</div></div>"
            for v, l in chips)
        st.markdown(f"<div class='stat-chips'>{chips_html}</div>", unsafe_allow_html=True)
        if est_count:
            st.caption(f"⚠️ {est_count} estimated/backfilled log{'s' if est_count != 1 else ''} "
                       f"included in total hours but excluded from session count, average, and the heatmap.")

        st.divider()

        # ── Collection breakdown ──
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("#### 📂 By Category")
            cat_counts = all_models.groupby('category').size().reset_index(name='count')
            cat_counts = cat_counts.sort_values('count', ascending=False)
            for _, r in cat_counts.iterrows():
                pct = int(r['count'] / len(all_models) * 100)
                st.markdown(f"""
                <div style='margin-bottom:8px'>
                    <div style='display:flex;justify-content:space-between;margin-bottom:3px'>
                        <span style='color:#e0e0e0;font-size:0.85rem'>{r['category']}</span>
                        <span style='color:var(--accent);font-size:0.85rem'>{r['count']}</span>
                    </div>
                    <div style='background:var(--border);border-radius:4px;height:6px'>
                        <div style='background:var(--accent);width:{pct}%;height:6px;border-radius:4px'></div>
                    </div>
                </div>""", unsafe_allow_html=True)

        with col_right:
            st.markdown("#### 📈 By Status")
            status_counts = all_models.groupby('status').size().reset_index(name='count')
            status_colors = {'Completed': 'var(--done)', 'In Progress': 'var(--amber)',
                             'Not Started': '#555',  'On Hold': '#888'}
            for _, r in status_counts.iterrows():
                pct   = int(r['count'] / len(all_models) * 100)
                color = status_colors.get(r['status'], 'var(--accent)')
                st.markdown(f"""
                <div style='margin-bottom:8px'>
                    <div style='display:flex;justify-content:space-between;margin-bottom:3px'>
                        <span style='color:#e0e0e0;font-size:0.85rem'>{r['status']}</span>
                        <span style='font-size:0.85rem;color:{color}'>{r['count']} ({pct}%)</span>
                    </div>
                    <div style='background:var(--border);border-radius:4px;height:6px'>
                        <div style='background:{color};width:{pct}%;height:6px;border-radius:4px'></div>
                    </div>
                </div>""", unsafe_allow_html=True)

        st.divider()

        # ── Build heatmap (last 12 weeks) ──
        if not real_logs.empty:
            st.markdown("#### 🗓️ Build Activity")
            heatmap_logs = real_logs.copy()
            # start_time is stored in mixed formats (ISO from the timer,
            # "%Y-%m-%d %H:%M" from manual logs) — parse flexibly and drop
            # any rows that still won't parse instead of crashing.
            parsed = pd.to_datetime(heatmap_logs['start_time'], format='mixed', errors='coerce')
            heatmap_logs = heatmap_logs.assign(date=parsed.dt.date)
            heatmap_logs = heatmap_logs.dropna(subset=['date'])
            if heatmap_logs.empty:
                st.info("No dated sessions to chart yet.")
            else:
                daily = heatmap_logs.groupby('date')['duration'].sum().reset_index()
                daily.columns = ['date', 'seconds']

                import datetime as dt
                today      = dt.date.today()
                start_date = today - dt.timedelta(weeks=12)
                date_range = pd.date_range(start=start_date, end=today)
                date_df    = pd.DataFrame({'date': date_range.date})
                merged     = date_df.merge(daily, on='date', how='left').fillna(0)
                max_secs   = merged['seconds'].max() or 1

                # Render as a grid of colored squares
                weeks = [merged.iloc[i:i+7] for i in range(0, len(merged), 7)]
                week_html = "<div style='display:flex;gap:3px;flex-wrap:nowrap;overflow-x:auto'>"
                for week in weeks:
                    week_html += "<div style='display:flex;flex-direction:column;gap:3px'>"
                    for _, day_row in week.iterrows():
                        intensity = day_row['seconds'] / max_secs
                        if intensity == 0:
                            color = "var(--surface)"
                        elif intensity < 0.3:
                            color = "#2e4d2e"
                        elif intensity < 0.6:
                            color = "#4a7a4a"
                        else:
                            color = "var(--accent)"
                        mins  = int(day_row['seconds'] // 60)
                        title = f"{day_row['date']}: {mins}min"
                        week_html += f"<div title='{title}' style='width:14px;height:14px;background:{color};border-radius:3px;border:1px solid var(--border)'></div>"
                    week_html += "</div>"
                week_html += "</div>"
                week_html += "<div style='color:#555;font-size:0.7rem;margin-top:6px'>Last 12 weeks — hover for details</div>"
                st.markdown(week_html, unsafe_allow_html=True)

        st.divider()

        # ── Top builds by time ──
        if not all_logs.empty:
            st.markdown("#### 🏆 Most Time Spent")
            model_time = all_logs.groupby('model_id')['duration'].sum().reset_index()
            model_time = model_time.merge(
                all_models[['model_id', 'name', 'status']], on='model_id', how='left')
            model_time = model_time.sort_values('duration', ascending=False).head(5)
            for _, r in model_time.iterrows():
                emoji = STATUS_EMOJI.get(r['status'], '⬜')
                st.markdown(f"""
                <div style='display:flex;justify-content:space-between;padding:8px 12px;
                            background:var(--surface);border-radius:6px;margin-bottom:6px;
                            border:1px solid var(--border)'>
                    <span style='color:#e0e0e0'>{emoji} {r['name']}</span>
                    <span style='color:var(--accent);font-weight:700'>{fmt_seconds(r['duration'])}</span>
                </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# EXPORT PAGE — get a copy of your data that's yours
# ─────────────────────────────────────────────
elif st.session_state.page == 'export':
    st.markdown("<h2>📤 Export Your Data</h2>", unsafe_allow_html=True)
    st.markdown(
        "Your collection, always in sync with your Google Sheet.")

    models_df = get_all_models()
    logs_df   = pd.read_sql_query("SELECT * FROM Build_Logs ORDER BY model_id, start_time", conn)
    photos_df = pd.read_sql_query("SELECT * FROM Photos ORDER BY model_id, uploaded_at", conn)

    # ── Google Sheet sync — primary ─────────────────────────────
    st.markdown("<h3>🔄 Google Sheet sync</h3>", unsafe_allow_html=True)
    if gsheet_webhook():
        st.success("✅ Connected — your sheet auto-updates on every save.")
        st.caption(
            f"{len(models_df)} models · {len(logs_df)} sessions · {len(photos_df)} photos")
        if st.button("🔄 Sync now", type="primary"):
            with st.spinner("Pushing to your Google Sheet..."):
                ok, msg = sync_to_sheet()
            if ok:
                st.success("Google Sheet updated!")
            else:
                st.error(f"Sync failed: {msg}")
    else:
        st.info("Not connected yet. Set it up once below, then it stays in sync automatically.")
        with st.expander("⚙️ One-time setup (about 5 minutes)"):
            st.markdown("""
**1.** Create (or open) a Google Sheet you want your data mirrored into.

**2.** In that sheet: **Extensions → Apps Script**. Delete whatever's there and paste the script below. *(Optional: set `SECRET` to any password to lock down your webhook.)*

**3.** Click **Deploy → New deployment** → gear icon → **Web app**. Set **Execute as: Me** and **Who has access: Anyone**, then **Deploy**. Approve the access prompt (click *Advanced → Go to … (unsafe)* — it's your own script).

**4.** Copy the **Web app URL** it gives you.

**5.** Add it to your app secrets (`.streamlit/secrets.toml`, or *Manage app → Secrets* on Streamlit Cloud):
```toml
GSHEET_WEBHOOK_URL = "https://script.google.com/macros/s/XXXX/exec"
# GSHEET_SECRET = "the-same-password-as-SECRET"   # only if you set one
```

**6.** Reload this app and hit **Sync now**. Every save after that updates the sheet automatically.
""")
            st.caption("Paste this into Apps Script:")
            st.code(APPS_SCRIPT_CODE, language="javascript")

    # ── Download backup (collapsed) ─────────────────────────────
    st.divider()
    with st.expander("⬇️ Download a backup copy"):
        if models_df.empty and logs_df.empty:
            st.info("Nothing to export yet.")
        else:
            stamp = datetime.now().strftime("%Y-%m-%d")
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as xl:
                models_df.to_excel(xl, sheet_name="Models",     index=False)
                logs_df.to_excel(xl,   sheet_name="Build Logs", index=False)
                photos_df.to_excel(xl, sheet_name="Photos",     index=False)
            st.download_button(
                "⬇️ Excel workbook (.xlsx) — Models, Build Logs, Photos",
                data=buf.getvalue(),
                file_name=f"metal_earth_export_{stamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
            d1, d2, d3 = st.columns(3)
            with d1:
                st.download_button("Models.csv", models_df.to_csv(index=False),
                    f"models_{stamp}.csv", "text/csv", use_container_width=True)
            with d2:
                st.download_button("Build Logs.csv", logs_df.to_csv(index=False),
                    f"build_logs_{stamp}.csv", "text/csv", use_container_width=True)
            with d3:
                st.download_button("Photos.csv", photos_df.to_csv(index=False),
                    f"photos_{stamp}.csv", "text/csv", use_container_width=True)

# ─────────────────────────────────────────────
# WORKBENCH PAGE
# ─────────────────────────────────────────────
elif st.session_state.page == 'workbench':
    model_id = st.session_state.selected_model
    model    = get_model(model_id)

    if model is None:
        st.error("Model not found.")
        st.session_state.page = 'inventory'
        st.rerun()

    # Remember where we are so the app reopens right here next time
    set_app_state('last_opened_model', model_id)

    # Compact one-row header: back button + name, then a single info line
    with st.container(key="nowrap_backrow"):
        bc1, bc2 = st.columns([1, 6])
        with bc1:
            if st.button("⬅️", help="Back to collection"):
                st.session_state.page = 'inventory'
                st.session_state.selected_model = None
                st.rerun()
        with bc2:
            st.markdown(f"<h2 style='margin:0'>🔧 {model['name']}</h2>", unsafe_allow_html=True)

    sheets_str = f"{model['sheets']} sheet{'s' if model['sheets'] != 1 else ''}" if pd.notna(model.get('sheets')) else '— sheets'
    st.markdown(
        f"<div class='stats-line'>{model['model_id']} &nbsp;·&nbsp; {model['category'] or '—'} "
        f"&nbsp;·&nbsp; {model['difficulty'] or '—'} &nbsp;·&nbsp; {sheets_str}</div>",
        unsafe_allow_html=True)

    tab_timer, tab_journal, tab_details, tab_photos = st.tabs(
        ["⏱️ Timer", "📖 Journal", "📋 Details", "📸 Photos"])

    # ── TAB: TIMER (first tab — center stage) ──────────────────
    with tab_timer:
        secs_logged = total_time_seconds(model_id)

        # Check for active timer
        active = get_active_timer()
        is_active = active and active[0] == model_id

        # Post-session recap: the session is already saved (nothing can be
        # lost) — this just offers a note + photo while it's fresh.
        recap = st.session_state.get('recap')
        if recap and recap.get('model_id') == model_id and not is_active:
            st.success(f"✅ Logged {fmt_seconds(recap['duration'])} — add a note & photo while it's fresh?")
            recap_note = st.text_input("What did you work on?", key="recap_note",
                                       placeholder="e.g. Finished the wings")
            recap_cam  = st.camera_input("📷 Snap a progress photo (optional)", key="recap_cam")
            recap_up   = None
            if recap_cam is None:
                recap_up = st.file_uploader("…or choose a photo", type=["jpg", "jpeg", "png", "webp"],
                                            key="recap_upload")
            with st.container(key="nowrap_recap"):
                rb1, rb2 = st.columns(2)
                do_save = rb1.button("💾 Save recap", type="primary", use_container_width=True)
                do_skip = rb2.button("Skip", use_container_width=True)
            if do_save:
                if recap_note:
                    c.execute("UPDATE Build_Logs SET notes=? WHERE log_id=?",
                              (recap_note, recap['log_id']))
                photo = recap_cam or recap_up
                photo_err = None
                if photo is not None:
                    with st.spinner("Uploading photo..."):
                        ext = "jpg"
                        if getattr(photo, "name", None) and "." in photo.name:
                            ext = photo.name.rsplit(".", 1)[-1].lower()
                        filename = f"{model_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                        url, photo_err = upload_to_github(photo.getvalue(), filename)
                    if url:
                        c.execute(
                            "INSERT INTO Photos (model_id, url, caption, uploaded_at) VALUES (?,?,?,?)",
                            (model_id, url, recap_note, datetime.now().strftime("%Y-%m-%d %H:%M")))
                if photo_err:
                    st.error(f"Photo upload failed: {photo_err} — note not saved yet, try again.")
                elif save_and_report("Session saved!"):
                    del st.session_state['recap']
                    st.rerun()
            if do_skip:
                del st.session_state['recap']
                st.rerun()
            st.divider()

        if is_active:
            timer_start_dt = datetime.fromisoformat(active[1])

            # Live stopwatch. Streamlit strips <script> from markdown, so the old
            # JS reload never actually ran. A fragment with run_every re-renders
            # just this block once a second — a real ticking clock, no full reload.
            # The *recorded* duration is still derived from the true start time at
            # Stop, so the logged value is unaffected by how often we re-render.
            @st.fragment(run_every=1)
            def _live_stopwatch():
                elapsed       = (datetime.now() - timer_start_dt).total_seconds()
                total_display = secs_logged + elapsed
                h, rem = divmod(int(elapsed), 3600)
                m, s   = divmod(rem, 60)
                st.markdown(f"""
                <div class='stopwatch'>
                    <div class='stopwatch-label'>Session Time</div>
                    <div class='stopwatch-time'>{h:02d}:{m:02d}:{s:02d}</div>
                    <div class='stopwatch-label' style='margin-top:12px'>Total on this kit: {fmt_seconds(total_display)}</div>
                </div>""", unsafe_allow_html=True)
            _live_stopwatch()

            if st.button("⏹️ Stop & Save Session", type="primary", use_container_width=True):
                duration = (datetime.now() - timer_start_dt).total_seconds()
                # Save the session immediately — the note/photo recap that
                # follows is optional, so nothing is lost if it's abandoned.
                c.execute(
                    "INSERT INTO Build_Logs (model_id, start_time, duration, notes) VALUES (?,?,?,?)",
                    (model_id, active[1], duration, ""))
                log_id = c.lastrowid
                c.execute(
                    "UPDATE Models SET last_worked=?, status=? WHERE model_id=?",
                    (str(datetime.now().date()),
                     'In Progress' if model['status'] == 'Not Started' else model['status'],
                     model_id))
                c.execute("DELETE FROM Active_Timer")
                st.session_state['recap'] = {
                    'model_id': model_id, 'log_id': log_id, 'duration': duration}
                # Single commit+push for the whole session so a failed sync
                # is reported instead of silently dropping the logged time.
                if save_and_report(None):
                    st.rerun()

        else:
            # Show total time and start button
            st.markdown(f"""
            <div class='stopwatch'>
                <div class='stopwatch-label'>Total Time on This Kit</div>
                <div class='stopwatch-time'>{fmt_seconds(secs_logged)}</div>
                <div class='stopwatch-label' style='margin-top:12px'>Ready to build</div>
            </div>""", unsafe_allow_html=True)

            # Check if another model has the timer
            if active and active[0] != model_id:
                other = get_model(active[0])
                other_name = other['name'] if other is not None else active[0]
                st.warning(f"⚠️ Timer is currently running on **{other_name}**. Stop that session first, or click below to switch.")
                if st.button(f"🔄 Switch timer to {model['name']}", type="secondary"):
                    # Stop old session without saving
                    clear_active_timer()
                    set_active_timer(model_id, datetime.now().isoformat())
                    st.rerun()
            else:
                if st.button("▶️ Start Build Session", type="primary", use_container_width=True):
                    set_active_timer(model_id, datetime.now().isoformat())
                    st.rerun()

        st.divider()
        st.markdown("**Or log time manually:**")
        with st.form("manual_log"):
            manual_mins = st.number_input("Minutes", min_value=1, value=30)
            manual_note = st.text_input("Note")
            manual_est  = st.checkbox(
                "This is an estimate / bulk backfill",
                help="Counts toward total hours, but excluded from session count, average, and the heatmap.")
            if st.form_submit_button("Log Manual Session"):
                c.execute(
                    "INSERT INTO Build_Logs (model_id, start_time, duration, notes, is_estimate) VALUES (?,?,?,?,?)",
                    (model_id, datetime.now().strftime("%Y-%m-%d %H:%M"), manual_mins * 60,
                     manual_note, 1 if manual_est else 0))
                c.execute("UPDATE Models SET last_worked=? WHERE model_id=?",
                          (str(datetime.now().date()), model_id))
                if save_and_report("Logged!"):
                    st.rerun()

        st.divider()
        st.markdown("#### 📅 Build History")
        logs = get_logs(model_id)
        if logs.empty:
            st.info("No sessions logged yet.")
        else:
            for _, log in logs.iterrows():
                lid = int(log['log_id'])
                editing = st.session_state.get(f"editing_log_{lid}", False)

                if editing:
                    st.markdown(
                        "<div style='background:var(--surface);border:1px solid var(--accent);"
                        "border-radius:8px;padding:12px;margin-bottom:8px'>",
                        unsafe_allow_html=True)
                    ec1, ec2 = st.columns([1, 2])
                    with ec1:
                        new_mins = st.number_input(
                            "Minutes", min_value=0.0, step=1.0,
                            value=round(log['duration'] / 60, 1),
                            key=f"edit_mins_{lid}")
                    with ec2:
                        new_note = st.text_input(
                            "Note", value=log['notes'] or "", key=f"edit_note_{lid}")
                    new_est = st.checkbox(
                        "Estimate / bulk backfill (excluded from average, session count, heatmap)",
                        value=bool(log['is_estimate']) if 'is_estimate' in log and pd.notna(log['is_estimate']) else False,
                        key=f"edit_est_{lid}")
                    sc1, sc2, _ = st.columns([1, 1, 3])
                    with sc1:
                        if st.button("💾 Save", key=f"save_log_{lid}", type="primary"):
                            c.execute(
                                "UPDATE Build_Logs SET duration=?, notes=?, is_estimate=? WHERE log_id=?",
                                (new_mins * 60, new_note, 1 if new_est else 0, lid))
                            if save_and_report("Saved!"):
                                st.session_state[f"editing_log_{lid}"] = False
                                st.rerun()
                    with sc2:
                        if st.button("Cancel", key=f"cancel_log_{lid}"):
                            st.session_state[f"editing_log_{lid}"] = False
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    is_est = bool(log['is_estimate']) if 'is_estimate' in log and pd.notna(log['is_estimate']) else False
                    est_badge = " <span style='background:#243024;color:var(--accent);font-size:0.6rem;padding:1px 5px;border-radius:4px;letter-spacing:1px'>EST</span>" if is_est else ""
                    # One row per session on phones: text block + two icon buttons
                    log_note_html = f"<br><span style='color:#e0e0e0'>{log['notes']}</span>" if log['notes'] else ""
                    with st.container(key=f"nowrap_logrow_{lid}"):
                        rc1, rc2, rc3 = st.columns([8, 1, 1])
                        rc1.markdown(
                            f"<div style='font-size:0.85rem;line-height:1.5'>"
                            f"<span style='color:var(--accent);font-weight:600'>{fmt_seconds(log['duration'])}</span>{est_badge}"
                            f" <span style='color:#888'>· {log['start_time']}</span>"
                            f"{log_note_html}"
                            f"</div>",
                            unsafe_allow_html=True)
                        with rc2:
                            if st.button("✏️", key=f"edit_btn_{lid}", help="Edit this session"):
                                st.session_state[f"editing_log_{lid}"] = True
                                st.rerun()
                        with rc3:
                            if st.button("🗑️", key=f"del_log_{lid}", help="Delete this session"):
                                c.execute("DELETE FROM Build_Logs WHERE log_id=?", (lid,))
                                if save_and_report(None):
                                    st.rerun()

    # ── TAB: JOURNAL — the build's story, newest first ──────────
    with tab_journal:
        j_logs   = get_logs(model_id)
        j_photos = get_photos(model_id)

        entries = []
        for _, log in j_logs.iterrows():
            ts = pd.to_datetime(log['start_time'], format='mixed', errors='coerce')
            entries.append({'ts': ts, 'kind': 'session',
                            'duration': log['duration'], 'note': log['notes'],
                            'is_est': bool(log['is_estimate']) if pd.notna(log.get('is_estimate')) else False})
        for _, photo in j_photos.iterrows():
            ts = pd.to_datetime(photo['uploaded_at'], format='mixed', errors='coerce')
            entries.append({'ts': ts, 'kind': 'photo',
                            'url': photo['url'], 'caption': photo['caption']})

        if not entries:
            st.info("Nothing here yet — log a session or add a photo and the story builds itself.")
        else:
            # Newest first; undated entries sink to the bottom
            entries.sort(key=lambda e: pd.Timestamp.min if pd.isna(e['ts']) else e['ts'], reverse=True)
            total_secs = total_time_seconds(model_id)
            total_str  = fmt_seconds(total_secs) if total_secs else "0m"
            st.markdown(
                f"<div class='stats-line'>{len(j_logs)} session{'s' if len(j_logs) != 1 else ''} · "
                f"{len(j_photos)} photo{'s' if len(j_photos) != 1 else ''} · ⏱ {total_str} total</div>",
                unsafe_allow_html=True)
            for e in entries:
                date_str = e['ts'].strftime('%b %d, %Y · %H:%M') if not pd.isna(e['ts']) else 'Undated'
                if e['kind'] == 'session':
                    est_tag = " (estimate)" if e['is_est'] else ""
                    note_html = f"<div class='journal-body'>{e['note']}</div>" if e['note'] else ""
                    st.markdown(f"""
                    <div class='journal-entry'>
                        <div class='journal-date'>⏱ {date_str} — {fmt_seconds(e['duration'])}{est_tag}</div>
                        {note_html}
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='journal-entry'><div class='journal-date'>📸 {date_str}</div></div>",
                                unsafe_allow_html=True)
                    st.image(e['url'], use_container_width=True)
                    if e['caption']:
                        st.caption(e['caption'])

    # ── TAB: DETAILS ───────────────────────────────
    with tab_details:
        with st.form("edit_model"):
            new_status = st.selectbox("Status", STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(model['status']) if model['status'] in STATUS_OPTIONS else 0)
            new_rating = st.slider("My Rating (1–10)", 1, 10,
                int(model['rating']) if model['rating'] else 1)
            new_notes  = st.text_area("Notes / Tips",
                value=str(model['notes']) if model['notes'] else "")
            if st.form_submit_button("💾 Save Changes"):
                c.execute("UPDATE Models SET status=?, rating=?, notes=? WHERE model_id=?",
                          (new_status, new_rating, new_notes, model_id))
                if save_and_report("Saved!"):
                    st.rerun()

        if st.button("🗑️ Remove from Collection", type="secondary"):
            c.execute("DELETE FROM Models WHERE model_id=?",     (model_id,))
            c.execute("DELETE FROM Build_Logs WHERE model_id=?", (model_id,))
            c.execute("DELETE FROM Photos WHERE model_id=?",     (model_id,))
            if save_and_report(None):
                st.session_state.page = 'inventory'
                st.session_state.selected_model = None
                st.rerun()

    # ── TAB: PHOTOS ────────────────────────────────
    with tab_photos:
        photos = get_photos(model_id)

        with st.expander("📤 Upload a Progress Photo"):
            uploaded_file = st.file_uploader(
                "Choose an image", type=["jpg", "jpeg", "png", "webp"],
                key=f"uploader_{model_id}")
            caption_input = st.text_input("Caption (optional, e.g. 'Wings done!')")
            if uploaded_file is not None:
                st.image(uploaded_file, caption="Preview", width=300)
                if st.button("📤 Upload to Gallery", type="primary"):
                    with st.spinner("Uploading to GitHub..."):
                        image_bytes = uploaded_file.read()
                        ext         = uploaded_file.name.rsplit(".", 1)[-1].lower()
                        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename    = f"{model_id}_{timestamp}.{ext}"
                        url, err    = upload_to_github(image_bytes, filename)
                    if url:
                        c.execute(
                            "INSERT INTO Photos (model_id, url, caption, uploaded_at) VALUES (?,?,?,?)",
                            (model_id, url, caption_input, datetime.now().strftime("%Y-%m-%d %H:%M")))
                        if save_and_report("Photo uploaded!"):
                            st.rerun()
                    else:
                        st.error(f"Upload failed: {err}")

        if photos.empty:
            st.info("No photos yet. Document your build progress!")
        else:
            st.write(f"**{len(photos)} photo{'s' if len(photos) > 1 else ''}**")
            cols = st.columns(3)
            for i, (_, photo) in enumerate(photos.iterrows()):
                with cols[i % 3]:
                    st.image(photo['url'], use_container_width=True)
                    if photo['caption']:
                        st.caption(photo['caption'])
                    st.caption(f"🕐 {photo['uploaded_at']}")
                    if st.button("🗑️", key=f"del_photo_{photo['photo_id']}", help="Delete photo"):
                        c.execute("DELETE FROM Photos WHERE photo_id=?", (photo['photo_id'],))
                        if save_and_report(None):
                            st.rerun()
