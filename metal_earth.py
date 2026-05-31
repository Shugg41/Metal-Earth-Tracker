import streamlit as st
import sqlite3
import pandas as pd
import requests
import base64
import os
from datetime import datetime

# ─────────────────────────────────────────────
# PAGE CONFIG & THEME
# ─────────────────────────────────────────────
st.set_page_config(page_title="Metal Earth Workbench", layout="wide", page_icon="⚙️")

st.markdown("""
<style>
/* ── Dark industrial base ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: #0e0e0e !important;
    color: #e0e0e0 !important;
}
[data-testid="stSidebar"] { background-color: #1a1a1a !important; }
[data-testid="stHeader"]  { background-color: #0e0e0e !important; }

/* ── Headings ── */
h1, h2, h3, h4 { color: #c8a84b !important; font-family: 'Georgia', serif; letter-spacing: 1px; }

/* ── Metric tiles ── */
[data-testid="stMetric"] {
    background: #1c1c1c;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 12px 16px;
}
[data-testid="stMetricLabel"] { color: #888 !important; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }
[data-testid="stMetricValue"] { color: #c8a84b !important; font-size: 1.6rem; font-weight: 700; }

/* ── Buttons ── */
.stButton > button {
    background: #1c1c1c !important;
    color: #c8a84b !important;
    border: 1px solid #c8a84b !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #c8a84b !important;
    color: #0e0e0e !important;
}
/* Primary buttons */
.stButton > button[kind="primary"] {
    background: #c8a84b !important;
    color: #0e0e0e !important;
    border: 1px solid #c8a84b !important;
}
.stButton > button[kind="primary"]:hover {
    background: #e5c76b !important;
}

/* ── Inputs ── */
input, textarea, [data-baseweb="select"] {
    background-color: #1c1c1c !important;
    color: #e0e0e0 !important;
    border-color: #333 !important;
    border-radius: 6px !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] button {
    color: #888 !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #c8a84b !important;
    border-bottom: 2px solid #c8a84b !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    background: #1c1c1c !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 8px !important;
}

/* ── Divider ── */
hr { border-color: #2a2a2a !important; }

/* ── Model cards ── */
.model-card {
    background: #1c1c1c;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
}
.model-card:hover { border-color: #c8a84b; background: #222; }
.model-card-title { color: #e0e0e0; font-size: 1rem; font-weight: 600; margin-bottom: 4px; }
.model-card-meta  { color: #888; font-size: 0.78rem; }
.model-card-status-inprogress { color: #f0a500; font-weight: 700; }
.model-card-status-completed  { color: #4caf50; font-weight: 700; }
.model-card-status-notstarted { color: #666;    font-weight: 700; }
.model-card-status-onhold     { color: #888;    font-weight: 700; }

/* ── Currently building banner ── */
.building-banner {
    background: linear-gradient(135deg, #1a1400, #2a2000);
    border: 2px solid #c8a84b;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 16px;
}
.building-banner-title { color: #c8a84b; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 6px; }
.building-banner-name  { color: #fff; font-size: 1.1rem; font-weight: 700; }

/* ── Stopwatch display ── */
.stopwatch {
    background: #111;
    border: 2px solid #c8a84b;
    border-radius: 16px;
    text-align: center;
    padding: 32px;
    margin: 16px 0;
}
.stopwatch-time {
    font-size: 4rem;
    font-weight: 700;
    color: #c8a84b;
    font-family: 'Courier New', monospace;
    letter-spacing: 4px;
}
.stopwatch-label { color: #666; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 2px; margin-top: 8px; }

/* ── Stats cards ── */
.stat-card {
    background: #1c1c1c;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    margin-bottom: 12px;
}
.stat-card-value { color: #c8a84b; font-size: 2rem; font-weight: 700; }
.stat-card-label { color: #888; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border: 1px solid #2a2a2a !important; border-radius: 8px !important; }

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
# STARTUP — pull DB from GitHub
# ─────────────────────────────────────────────
if 'db_loaded' not in st.session_state:
    with st.spinner("Loading your workshop..."):
        pull_db_from_github()
    st.session_state.db_loaded = True

# ─────────────────────────────────────────────
# MASTER CSV
# ─────────────────────────────────────────────
@st.cache_data
def load_master():
    try:
        df = pd.read_csv('metal_earth_models.csv')
        df.columns = df.columns.str.lower().str.strip()
        return df
    except FileNotFoundError:
        return pd.DataFrame()

master_df = load_master()

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
              notes       TEXT)''')

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

conn.commit()

# ─────────────────────────────────────────────
# SAVE HELPER
# ─────────────────────────────────────────────
def save():
    conn.commit()
    push_db_to_github()

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
    save()

def clear_active_timer():
    c.execute("DELETE FROM Active_Timer")
    save()

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
if 'page' not in st.session_state:
    st.session_state.page = 'inventory'
if 'selected_model' not in st.session_state:
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

total_hours  = round(total_secs_db / 3600, 1)
completed    = len(all_models[all_models['status'] == 'Completed'])    if not all_models.empty else 0
in_progress  = len(all_models[all_models['status'] == 'In Progress'])  if not all_models.empty else 0
total_owned  = len(all_models)
total_photos = pd.read_sql_query("SELECT COUNT(*) as n FROM Photos", conn)['n'].iloc[0] or 0

st.markdown("<h1 style='margin-bottom:0'>⚙️ Metal Earth Workbench</h1>", unsafe_allow_html=True)

# Top nav
nav_col1, nav_col2, nav_col3, nav_spacer = st.columns([1, 1, 1, 5])
with nav_col1:
    if st.button("📦 Collection", use_container_width=True):
        st.session_state.page = 'inventory'
        st.session_state.selected_model = None
        st.rerun()
with nav_col2:
    if st.button("📊 Stats", use_container_width=True):
        st.session_state.page = 'stats'
        st.session_state.selected_model = None
        st.rerun()

st.divider()

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("🗂️ Total Owned",      total_owned)
m2.metric("✅ Completed",         completed)
m3.metric("🔧 In Progress",       in_progress)
m4.metric("⏱️ Total Hours Built", total_hours)
m5.metric("📸 Progress Photos",   total_photos)

st.divider()

# ─────────────────────────────────────────────
# INVENTORY PAGE
# ─────────────────────────────────────────────
if st.session_state.page == 'inventory':

    # ── Currently Building banner ──
    in_progress_models = all_models[all_models['status'] == 'In Progress'] if not all_models.empty else pd.DataFrame()
    if not in_progress_models.empty:
        st.markdown("<div style='color:#c8a84b;font-size:0.7rem;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px'>🔧 Currently Building</div>", unsafe_allow_html=True)
        banner_cols = st.columns(len(in_progress_models.head(3)))
        for idx, (_, brow) in enumerate(in_progress_models.head(3).iterrows()):
            with banner_cols[idx]:
                secs = total_time_seconds(brow['model_id'])
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
                if st.button(f"Open {brow['model_id']}", key=f"banner_{brow['model_id']}"):
                    st.session_state.selected_model = brow['model_id']
                    st.session_state.page = 'workbench'
                    st.rerun()
        st.divider()

    st.markdown("<h2>📦 My Collection</h2>", unsafe_allow_html=True)

    with st.expander("➕ Add a Model to Your Collection"):
        with st.form("add_model", clear_on_submit=True):
            search_id    = st.text_input("Model ID (e.g. ME1054 or MMS073)").strip().upper()
            name_val     = cat_val = diff_val = ''
            diff_num_val = sheets_val = None
            auto_filled  = False

            if search_id and not master_df.empty:
                match = master_df[master_df['model_id'].astype(str).str.upper() == search_id]
                if not match.empty:
                    row          = match.iloc[0]
                    name_val     = str(row.get('name', ''))
                    cat_val      = str(row.get('category', ''))
                    diff_val     = str(row.get('difficulty', ''))
                    diff_num_val = safe_int(row.get('difficulty_num'))
                    sheets_val   = safe_float(row.get('sheets'))
                    auto_filled  = True

            if auto_filled:
                sheets_display = f"{sheets_val} sheets" if sheets_val is not None else "? sheets"
                st.success(f"✓ Found: **{name_val}** — {cat_val} | {diff_val} | {sheets_display}")

            name_input = st.text_input("Name",       value=name_val)
            cat_input  = st.text_input("Category",   value=cat_val)
            diff_input = st.text_input("Difficulty", value=diff_val)

            if st.form_submit_button("Add to Collection"):
                if not search_id:
                    st.error("Please enter a Model ID.")
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
                            (search_id, name_input, cat_input, sheets_val,
                             'Not Started', diff_input, diff_num_val,
                             str(datetime.now().date())))
                        with st.spinner("Saving..."):
                            save()
                        st.success(f"Added {name_input}!")
                        st.cache_data.clear()
                        st.rerun()

    # Filters
    all_models = get_all_models()
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        status_filter = st.selectbox("Filter by Status", ['All'] + STATUS_OPTIONS)
    with col_f2:
        cats = ['All'] + sorted(all_models['category'].dropna().unique().tolist()) if not all_models.empty else ['All']
        cat_filter = st.selectbox("Filter by Category", cats)
    with col_f3:
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
        # Model cards — 2 columns
        card_cols = st.columns(2)
        for i, (_, row) in enumerate(display_df.iterrows()):
            with card_cols[i % 2]:
                emoji      = STATUS_EMOJI.get(row['status'], '⬜')
                sheets_str = f"{row['sheets']}sh" if pd.notna(row.get('sheets')) and row.get('sheets') else '?sh'
                diff_str   = row['difficulty'] if row['difficulty'] else '—'
                photos     = get_photos(row['model_id'])
                photo_icon = " 📸" if not photos.empty else ""
                secs       = total_time_seconds(row['model_id'])
                time_str   = fmt_seconds(secs) if secs > 0 else "No time logged"

                # Is this the active timer model?
                timer_icon = ""
                if active_timer and active_timer[0] == row['model_id']:
                    timer_icon = " ⏱️"

                status_color = {
                    'In Progress': '#f0a500', 'Completed': '#4caf50',
                    'Not Started': '#666',    'On Hold': '#888'
                }.get(row['status'], '#666')

                st.markdown(f"""
                <div class='model-card'>
                    <div class='model-card-title'>{emoji} {row['name']}{photo_icon}{timer_icon}</div>
                    <div class='model-card-meta'>
                        {row['model_id']} &nbsp;·&nbsp; {row['category'] or '—'} &nbsp;·&nbsp; {diff_str} &nbsp;·&nbsp; {sheets_str}
                    </div>
                    <div style='margin-top:6px;font-size:0.8rem;color:{status_color};font-weight:600'>{row['status']}</div>
                    <div style='font-size:0.75rem;color:#555;margin-top:2px'>⏱ {time_str}</div>
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
        total_sheets = all_models['sheets'].sum() if 'sheets' in all_models.columns else 0
        total_build_secs = all_logs['duration'].sum() if not all_logs.empty else 0
        avg_session_mins = round((all_logs['duration'].mean() or 0) / 60, 1) if not all_logs.empty else 0
        total_sessions   = len(all_logs)

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("🔩 Total Sheets Punched", f"{int(total_sheets or 0)}")
        s2.metric("⏱️ Total Hours Built",    f"{round(total_build_secs/3600, 1)}")
        s3.metric("📋 Total Sessions",        total_sessions)
        s4.metric("⏰ Avg Session Length",    f"{avg_session_mins} min")

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
                        <span style='color:#c8a84b;font-size:0.85rem'>{r['count']}</span>
                    </div>
                    <div style='background:#2a2a2a;border-radius:4px;height:6px'>
                        <div style='background:#c8a84b;width:{pct}%;height:6px;border-radius:4px'></div>
                    </div>
                </div>""", unsafe_allow_html=True)

        with col_right:
            st.markdown("#### 📈 By Status")
            status_counts = all_models.groupby('status').size().reset_index(name='count')
            status_colors = {'Completed': '#4caf50', 'In Progress': '#f0a500',
                             'Not Started': '#555',  'On Hold': '#888'}
            for _, r in status_counts.iterrows():
                pct   = int(r['count'] / len(all_models) * 100)
                color = status_colors.get(r['status'], '#c8a84b')
                st.markdown(f"""
                <div style='margin-bottom:8px'>
                    <div style='display:flex;justify-content:space-between;margin-bottom:3px'>
                        <span style='color:#e0e0e0;font-size:0.85rem'>{r['status']}</span>
                        <span style='font-size:0.85rem;color:{color}'>{r['count']} ({pct}%)</span>
                    </div>
                    <div style='background:#2a2a2a;border-radius:4px;height:6px'>
                        <div style='background:{color};width:{pct}%;height:6px;border-radius:4px'></div>
                    </div>
                </div>""", unsafe_allow_html=True)

        st.divider()

        # ── Build heatmap (last 12 weeks) ──
        if not all_logs.empty:
            st.markdown("#### 🗓️ Build Activity")
            all_logs['date'] = pd.to_datetime(all_logs['start_time']).dt.date
            daily = all_logs.groupby('date')['duration'].sum().reset_index()
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
                        color = "#1c1c1c"
                    elif intensity < 0.3:
                        color = "#5a3e00"
                    elif intensity < 0.6:
                        color = "#9a6a00"
                    else:
                        color = "#c8a84b"
                    mins  = int(day_row['seconds'] // 60)
                    title = f"{day_row['date']}: {mins}min"
                    week_html += f"<div title='{title}' style='width:14px;height:14px;background:{color};border-radius:3px;border:1px solid #2a2a2a'></div>"
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
                            background:#1c1c1c;border-radius:6px;margin-bottom:6px;
                            border:1px solid #2a2a2a'>
                    <span style='color:#e0e0e0'>{emoji} {r['name']}</span>
                    <span style='color:#c8a84b;font-weight:700'>{fmt_seconds(r['duration'])}</span>
                </div>""", unsafe_allow_html=True)

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

    if st.button("⬅️ Back to Collection"):
        st.session_state.page = 'inventory'
        st.session_state.selected_model = None
        st.rerun()

    st.markdown(f"<h2>🔧 {model['name']}</h2>", unsafe_allow_html=True)

    inf1, inf2, inf3, inf4 = st.columns(4)
    inf1.metric("Model ID",   model['model_id'])
    inf2.metric("Category",   model['category'] or '—')
    inf3.metric("Difficulty", model['difficulty'] or '—')
    inf4.metric("Sheets",     model['sheets'] if pd.notna(model.get('sheets')) else '—')

    st.divider()

    tab_timer, tab_details, tab_photos = st.tabs(["⏱️ Build Timer", "📋 Details", "📸 Progress Photos"])

    # ── TAB: TIMER (first tab — center stage) ──────────────────
    with tab_timer:
        secs_logged = total_time_seconds(model_id)

        # Check for active timer
        active = get_active_timer()
        is_active = active and active[0] == model_id

        if is_active:
            timer_start_dt = datetime.fromisoformat(active[1])
            elapsed        = (datetime.now() - timer_start_dt).total_seconds()
            total_display  = secs_logged + elapsed

            # Big stopwatch display
            h, rem = divmod(int(elapsed), 3600)
            m, s   = divmod(rem, 60)
            st.markdown(f"""
            <div class='stopwatch'>
                <div class='stopwatch-label'>Session Time</div>
                <div class='stopwatch-time'>{h:02d}:{m:02d}:{s:02d}</div>
                <div class='stopwatch-label' style='margin-top:12px'>Total on this kit: {fmt_seconds(total_display)}</div>
            </div>""", unsafe_allow_html=True)

            st.markdown("<div style='text-align:center'>Page auto-refreshes every 30 seconds while timer runs</div>",
                        unsafe_allow_html=True)

            session_note = st.text_input("Session note (optional)", key="session_note_active")
            stop_col, _ = st.columns([1, 2])
            with stop_col:
                if st.button("⏹️ Stop & Save Session", type="primary", use_container_width=True):
                    duration = (datetime.now() - timer_start_dt).total_seconds()
                    c.execute(
                        "INSERT INTO Build_Logs (model_id, start_time, duration, notes) VALUES (?,?,?,?)",
                        (model_id, active[1], duration, session_note))
                    c.execute(
                        "UPDATE Models SET last_worked=?, status=? WHERE model_id=?",
                        (str(datetime.now().date()),
                         'In Progress' if model['status'] == 'Not Started' else model['status'],
                         model_id))
                    clear_active_timer()
                    st.success(f"✅ Logged {fmt_seconds(duration)}!")
                    st.rerun()

            # Auto-refresh every 30s so stopwatch visually updates
            st.markdown("""
            <script>
            setTimeout(function() { window.location.reload(); }, 30000);
            </script>""", unsafe_allow_html=True)

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
                start_col, _ = st.columns([1, 2])
                with start_col:
                    if st.button("▶️ Start Build Session", type="primary", use_container_width=True):
                        set_active_timer(model_id, datetime.now().isoformat())
                        st.rerun()

        st.divider()
        st.markdown("**Or log time manually:**")
        with st.form("manual_log"):
            manual_mins = st.number_input("Minutes", min_value=1, value=30)
            manual_note = st.text_input("Note")
            if st.form_submit_button("Log Manual Session"):
                c.execute(
                    "INSERT INTO Build_Logs (model_id, start_time, duration, notes) VALUES (?,?,?,?)",
                    (model_id, datetime.now().strftime("%Y-%m-%d %H:%M"), manual_mins * 60, manual_note))
                c.execute("UPDATE Models SET last_worked=? WHERE model_id=?",
                          (str(datetime.now().date()), model_id))
                with st.spinner("Saving..."):
                    save()
                st.success("Logged!")
                st.rerun()

        st.divider()
        st.markdown("#### 📅 Build History")
        logs = get_logs(model_id)
        if logs.empty:
            st.info("No sessions logged yet.")
        else:
            logs_display = logs[['start_time', 'duration', 'notes']].copy()
            logs_display['duration'] = logs_display['duration'].apply(fmt_seconds)
            logs_display.columns = ['Date/Time', 'Duration', 'Notes']
            st.dataframe(logs_display, use_container_width=True, hide_index=True)

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
                with st.spinner("Saving..."):
                    save()
                st.success("Saved!")
                st.rerun()

        if st.button("🗑️ Remove from Collection", type="secondary"):
            c.execute("DELETE FROM Models WHERE model_id=?",     (model_id,))
            c.execute("DELETE FROM Build_Logs WHERE model_id=?", (model_id,))
            c.execute("DELETE FROM Photos WHERE model_id=?",     (model_id,))
            with st.spinner("Saving..."):
                save()
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
                        with st.spinner("Saving..."):
                            save()
                        st.success("Photo uploaded!")
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
                        with st.spinner("Saving..."):
                            save()
                        st.rerun()
