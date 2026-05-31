import streamlit as st
import sqlite3
import pandas as pd
import requests
import base64
import os
from datetime import datetime

st.set_page_config(page_title="Metal Earth Workbench", layout="wide")

# ─────────────────────────────────────────────
# GITHUB HELPERS
# ─────────────────────────────────────────────
def gh_headers():
    token = st.secrets.get("GITHUB_TOKEN", "")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def gh_repo():
    return st.secrets.get("GITHUB_REPO", "")

def pull_db_from_github():
    """Download models_db.db from GitHub if it exists. Returns True if loaded."""
    try:
        repo = gh_repo()
        if not repo:
            return False
        url = f"https://api.github.com/repos/{repo}/contents/models_db.db"
        r = requests.get(url, headers=gh_headers(), timeout=15)
        if r.status_code == 200:
            data = r.json()
            db_bytes = base64.b64decode(data["content"])
            with open("models_db.db", "wb") as f:
                f.write(db_bytes)
            return True
        return False
    except Exception:
        return False

def push_db_to_github():
    """Upload current models_db.db to GitHub repo root."""
    try:
        repo = gh_repo()
        if not repo:
            return False
        with open("models_db.db", "rb") as f:
            db_bytes = f.read()
        b64 = base64.b64encode(db_bytes).decode("utf-8")
        url = f"https://api.github.com/repos/{repo}/contents/models_db.db"
        # Get existing SHA if file already exists
        r = requests.get(url, headers=gh_headers(), timeout=10)
        sha = r.json().get("sha") if r.status_code == 200 else None
        payload = {
            "message": f"Update database {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "content": b64,
        }
        if sha:
            payload["sha"] = sha
        r2 = requests.put(url, headers=gh_headers(), json=payload, timeout=30)
        return r2.status_code in (200, 201)
    except Exception:
        return False

def upload_to_github(image_bytes, filename):
    """Upload image bytes to GitHub repo /photos folder. Returns (url, error)."""
    try:
        repo = gh_repo()
        if not repo:
            return None, "GITHUB_REPO not set in Streamlit secrets."
        path    = f"photos/{filename}"
        api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
        check   = requests.get(api_url, headers=gh_headers(), timeout=10)
        sha     = check.json().get("sha") if check.status_code == 200 else None
        b64     = base64.b64encode(image_bytes).decode("utf-8")
        payload = {"message": f"Add progress photo: {filename}", "content": b64}
        if sha:
            payload["sha"] = sha
        response = requests.put(api_url, headers=gh_headers(), json=payload, timeout=20)
        if response.status_code in (200, 201):
            raw_url = f"https://raw.githubusercontent.com/{repo}/main/{path}"
            return raw_url, None
        else:
            return None, response.json().get("message", "GitHub upload failed.")
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# 1. PULL DATABASE FROM GITHUB ON STARTUP
# ─────────────────────────────────────────────
if 'db_loaded' not in st.session_state:
    with st.spinner("Loading your collection..."):
        pull_db_from_github()
    st.session_state.db_loaded = True

# ─────────────────────────────────────────────
# 2. LOAD MASTER CSV
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
# 3. DATABASE SETUP
# ─────────────────────────────────────────────
conn = sqlite3.connect('models_db.db', check_same_thread=False)
c = conn.cursor()

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

conn.commit()

# ─────────────────────────────────────────────
# 4. SAVE HELPER — call after every data change
# ─────────────────────────────────────────────
def save():
    """Commit to SQLite and push database to GitHub."""
    conn.commit()
    push_db_to_github()

# ─────────────────────────────────────────────
# 5. QUERY HELPERS
# ─────────────────────────────────────────────
STATUS_OPTIONS = ['Not Started', 'In Progress', 'Completed', 'On Hold']

def get_all_models():
    return pd.read_sql_query(
        "SELECT * FROM Models ORDER BY last_worked DESC NULLS LAST", conn)

def get_model(model_id):
    df = pd.read_sql_query(
        "SELECT * FROM Models WHERE model_id=?", conn, params=(model_id,))
    return df.iloc[0] if not df.empty else None

def get_logs(model_id):
    return pd.read_sql_query(
        "SELECT * FROM Build_Logs WHERE model_id=? ORDER BY start_time DESC",
        conn, params=(model_id,))

def get_photos(model_id):
    return pd.read_sql_query(
        "SELECT * FROM Photos WHERE model_id=? ORDER BY uploaded_at DESC",
        conn, params=(model_id,))

def total_time_minutes(model_id):
    logs = get_logs(model_id)
    if logs.empty:
        return 0
    return round(logs['duration'].sum() / 60, 1)

def safe_int(val):
    """Safely convert pandas/numpy numeric to plain Python int, or None."""
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        return int(val)
    except (ValueError, TypeError):
        return None

def safe_float(val):
    """Safely convert pandas/numpy numeric to plain Python float, or None."""
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        return float(val)
    except (ValueError, TypeError):
        return None

# ─────────────────────────────────────────────
# 6. NAVIGATION STATE
# ─────────────────────────────────────────────
if 'page' not in st.session_state:
    st.session_state.page = 'inventory'
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = None

# ─────────────────────────────────────────────
# 7. DASHBOARD STATS
# ─────────────────────────────────────────────
all_models = get_all_models()

total_seconds = pd.read_sql_query(
    "SELECT SUM(duration) as s FROM Build_Logs", conn)['s'].iloc[0] or 0
total_hours   = round(total_seconds / 3600, 1)
completed     = len(all_models[all_models['status'] == 'Completed']) if not all_models.empty else 0
in_progress   = len(all_models[all_models['status'] == 'In Progress']) if not all_models.empty else 0
total_owned   = len(all_models)
total_photos  = pd.read_sql_query("SELECT COUNT(*) as n FROM Photos", conn)['n'].iloc[0] or 0

st.title("⚙️ Metal Earth Workbench")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🗂️ Total Owned",      total_owned)
c2.metric("✅ Completed",         completed)
c3.metric("🔧 In Progress",       in_progress)
c4.metric("⏱️ Total Hours Built", total_hours)
c5.metric("📸 Progress Photos",   total_photos)

st.divider()

# ─────────────────────────────────────────────
# 8. INVENTORY PAGE
# ─────────────────────────────────────────────
if st.session_state.page == 'inventory':

    st.header("📦 My Collection")

    with st.expander("➕ Add a Model to Your Collection"):
        with st.form("add_model", clear_on_submit=True):
            search_id = st.text_input("Model ID (e.g. ME1054 or MMS073)").strip().upper()

            name_val     = ''
            cat_val      = ''
            diff_val     = ''
            diff_num_val = None
            sheets_val   = None
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
                    exists = c.execute(
                        "SELECT 1 FROM Models WHERE model_id=?", (search_id,)).fetchone()
                    if exists:
                        st.warning(f"{search_id} is already in your collection.")
                    else:
                        c.execute(
                            """INSERT INTO Models
                               (model_id, name, category, sheets, status,
                                difficulty, difficulty_num, last_worked)
                               VALUES (?,?,?,?,?,?,?,?)""",
                            (search_id,
                             name_input,
                             cat_input,
                             sheets_val,
                             'Not Started',
                             diff_input,
                             diff_num_val,
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
        sort_by = st.selectbox("Sort by",
            ['Last Worked', 'Name', 'Difficulty', 'Category', 'Status'])

    display_df = all_models.copy()
    if status_filter != 'All':
        display_df = display_df[display_df['status'] == status_filter]
    if cat_filter != 'All':
        display_df = display_df[display_df['category'] == cat_filter]

    sort_map = {
        'Last Worked': 'last_worked', 'Name': 'name',
        'Difficulty': 'difficulty_num', 'Category': 'category', 'Status': 'status',
    }
    display_df = display_df.sort_values(sort_map[sort_by], ascending=True)

    STATUS_EMOJI = {
        'Not Started': '⬜', 'In Progress': '🔧',
        'Completed': '✅', 'On Hold': '⏸️'
    }

    if display_df.empty:
        st.info("No models yet. Add one above!")
    else:
        for _, row in display_df.iterrows():
            emoji      = STATUS_EMOJI.get(row['status'], '⬜')
            sheets_str = f" • {row['sheets']}sh" if pd.notna(row.get('sheets')) and row.get('sheets') else ''
            photos     = get_photos(row['model_id'])
            thumb      = "  📸" if not photos.empty else ""
            label      = f"{emoji} {row['name']}  ({row['model_id']}){sheets_str}  — {row['status']}{thumb}"
            if st.button(label, key=f"btn_{row['model_id']}", use_container_width=True):
                st.session_state.selected_model = row['model_id']
                st.session_state.page = 'workbench'
                st.rerun()

# ─────────────────────────────────────────────
# 9. WORKBENCH PAGE
# ─────────────────────────────────────────────
elif st.session_state.page == 'workbench':
    model_id = st.session_state.selected_model
    model    = get_model(model_id)

    if model is None:
        st.error("Model not found.")
        st.session_state.page = 'inventory'
        st.rerun()

    if st.button("⬅️ Back to Inventory"):
        st.session_state.page = 'inventory'
        st.session_state.selected_model = None
        st.rerun()

    st.title(f"🔧 {model['name']}")

    inf1, inf2, inf3, inf4 = st.columns(4)
    inf1.metric("Model ID",   model['model_id'])
    inf2.metric("Category",   model['category'] or '—')
    inf3.metric("Difficulty", model['difficulty'] or '—')
    inf4.metric("Sheets",     model['sheets'] if pd.notna(model.get('sheets')) else '—')

    st.divider()

    tab_details, tab_timer, tab_photos = st.tabs(["📋 Details", "⏱️ Build Timer", "📸 Progress Photos"])

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
                c.execute(
                    "UPDATE Models SET status=?, rating=?, notes=? WHERE model_id=?",
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

    # ── TAB: TIMER ─────────────────────────────────
    with tab_timer:
        st.metric("Total Time on This Kit", f"{total_time_minutes(model_id)} min")

        if 'timer_start' not in st.session_state:
            if st.button("▶️ Start Build Session", type="primary"):
                st.session_state.timer_start = datetime.now()
                st.rerun()
        else:
            elapsed = (datetime.now() - st.session_state.timer_start).total_seconds()
            st.info(f"⏳ Session running... {int(elapsed // 60)}m {int(elapsed % 60)}s elapsed")
            session_note = st.text_input("Session note (optional)")
            if st.button("⏹️ Stop & Save Session", type="primary"):
                duration = (datetime.now() - st.session_state.timer_start).total_seconds()
                c.execute(
                    "INSERT INTO Build_Logs (model_id, start_time, duration, notes) VALUES (?,?,?,?)",
                    (model_id,
                     st.session_state.timer_start.strftime("%Y-%m-%d %H:%M"),
                     duration, session_note))
                c.execute(
                    "UPDATE Models SET last_worked=?, status=? WHERE model_id=?",
                    (str(datetime.now().date()),
                     'In Progress' if model['status'] == 'Not Started' else model['status'],
                     model_id))
                with st.spinner("Saving..."):
                    save()
                del st.session_state.timer_start
                st.success(f"Logged {round(duration/60, 1)} minutes!")
                st.rerun()

        st.write("---")
        st.write("**Or log time manually:**")
        with st.form("manual_log"):
            manual_mins = st.number_input("Minutes", min_value=1, value=30)
            manual_note = st.text_input("Note")
            if st.form_submit_button("Log Manual Session"):
                c.execute(
                    "INSERT INTO Build_Logs (model_id, start_time, duration, notes) VALUES (?,?,?,?)",
                    (model_id, datetime.now().strftime("%Y-%m-%d %H:%M"),
                     manual_mins * 60, manual_note))
                c.execute("UPDATE Models SET last_worked=? WHERE model_id=?",
                    (str(datetime.now().date()), model_id))
                with st.spinner("Saving..."):
                    save()
                st.success("Logged!")
                st.rerun()

        st.divider()
        st.subheader("📅 Build History")
        logs = get_logs(model_id)
        if logs.empty:
            st.info("No sessions logged yet.")
        else:
            logs_display = logs[['start_time', 'duration', 'notes']].copy()
            logs_display['duration'] = logs_display['duration'].apply(
                lambda s: f"{int(s//60)}m {int(s%60)}s")
            logs_display.columns = ['Date/Time', 'Duration', 'Notes']
            st.dataframe(logs_display, use_container_width=True, hide_index=True)

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
                            (model_id, url, caption_input,
                             datetime.now().strftime("%Y-%m-%d %H:%M")))
                        with st.spinner("Saving..."):
                            save()
                        st.success("Photo uploaded!")
                        st.rerun()
                    else:
                        st.error(f"Upload failed: {err}")
                        st.info("Make sure GITHUB_TOKEN and GITHUB_REPO are set in your Streamlit secrets.")

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
