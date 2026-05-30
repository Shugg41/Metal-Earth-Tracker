import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Metal Earth Workbench", layout="wide")

# ─────────────────────────────────────────────
# 1. LOAD MASTER CSV (the reference list)
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
# 2. DATABASE SETUP  — CREATE ONLY IF NOT EXISTS
#    (never DROP — that was wiping your data!)
# ─────────────────────────────────────────────
conn = sqlite3.connect('models_db.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS Models
             (model_id    TEXT PRIMARY KEY,
              name        TEXT,
              category    TEXT,
              sheets      REAL,
              status      TEXT DEFAULT 'Not Started',
              difficulty  TEXT,
              difficulty_num INTEGER,
              rating      INTEGER DEFAULT 0,
              notes       TEXT,
              last_worked TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS Build_Logs
             (log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
              model_id    TEXT,
              start_time  TEXT,
              duration    REAL,
              notes       TEXT)''')
conn.commit()

# ─────────────────────────────────────────────
# 3. HELPERS
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

def total_time_minutes(model_id):
    logs = get_logs(model_id)
    if logs.empty:
        return 0
    return round(logs['duration'].sum() / 60, 1)

# ─────────────────────────────────────────────
# 4. NAVIGATION STATE
# ─────────────────────────────────────────────
if 'page' not in st.session_state:
    st.session_state.page = 'inventory'
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = None

# ─────────────────────────────────────────────
# 5. DASHBOARD / STATS  (always visible at top)
# ─────────────────────────────────────────────
all_models = get_all_models()

total_seconds = pd.read_sql_query(
    "SELECT SUM(duration) as s FROM Build_Logs", conn)['s'].iloc[0] or 0
total_hours   = round(total_seconds / 3600, 1)
completed     = len(all_models[all_models['status'] == 'Completed']) if not all_models.empty else 0
in_progress   = len(all_models[all_models['status'] == 'In Progress']) if not all_models.empty else 0
total_owned   = len(all_models)

st.title("⚙️ Metal Earth Workbench")
c1, c2, c3, c4 = st.columns(4)
c1.metric("🗂️ Total Owned",       total_owned)
c2.metric("✅ Completed",          completed)
c3.metric("🔧 In Progress",        in_progress)
c4.metric("⏱️ Total Hours Built",  total_hours)

st.divider()

# ─────────────────────────────────────────────
# 6.  INVENTORY PAGE
# ─────────────────────────────────────────────
if st.session_state.page == 'inventory':

    st.header("📦 My Collection")

    # ── ADD MODEL FORM ─────────────────────────────
    with st.expander("➕ Add a Model to Your Collection"):
        with st.form("add_model", clear_on_submit=True):
            search_id = st.text_input("Model ID (e.g. ME1054 or MMS073)").strip().upper()

            # Auto-fill from CSV
            name_val = cat_val = diff_val = diff_num = sheets_val = ''
            auto_filled = False
            if search_id and not master_df.empty:
                match = master_df[master_df['model_id'].astype(str).str.upper() == search_id]
                if not match.empty:
                    row = match.iloc[0]
                    name_val     = str(row.get('name', ''))
                    cat_val      = str(row.get('category', ''))
                    diff_val     = str(row.get('difficulty', ''))
                    diff_num     = row.get('difficulty_num', None)
                    sheets_val   = row.get('sheets', None)
                    auto_filled  = True

            if auto_filled:
                st.success(f"✓ Found: **{name_val}** — {cat_val} | {diff_val} | {sheets_val} sheets")

            # Manual overrides always available
            name_input  = st.text_input("Name",       value=name_val)
            cat_input   = st.text_input("Category",   value=cat_val)
            diff_input  = st.text_input("Difficulty", value=diff_val)

            submitted = st.form_submit_button("Add to Collection")
            if submitted:
                if not search_id:
                    st.error("Please enter a Model ID.")
                else:
                    # Check for duplicate
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
                            (search_id, name_input, cat_input,
                             sheets_val if sheets_val != '' else None,
                             'Not Started', diff_input,
                             int(diff_num) if diff_num and str(diff_num) != 'nan' else None,
                             str(datetime.now().date())))
                        conn.commit()
                        st.success(f"Added {name_input}!")
                        st.cache_data.clear()
                        st.rerun()

    # ── FILTERS ────────────────────────────────────
    all_models = get_all_models()
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        status_filter = st.selectbox("Filter by Status",
            ['All'] + STATUS_OPTIONS)
    with col_f2:
        cats = ['All'] + sorted(all_models['category'].dropna().unique().tolist()) if not all_models.empty else ['All']
        cat_filter = st.selectbox("Filter by Category", cats)
    with col_f3:
        sort_by = st.selectbox("Sort by",
            ['Last Worked', 'Name', 'Difficulty', 'Category', 'Status'])

    # Apply filters
    display_df = all_models.copy()
    if status_filter != 'All':
        display_df = display_df[display_df['status'] == status_filter]
    if cat_filter != 'All':
        display_df = display_df[display_df['category'] == cat_filter]

    sort_map = {
        'Last Worked': 'last_worked',
        'Name': 'name',
        'Difficulty': 'difficulty_num',
        'Category': 'category',
        'Status': 'status',
    }
    display_df = display_df.sort_values(sort_map[sort_by], ascending=True)

    # ── MODEL LIST ─────────────────────────────────
    if display_df.empty:
        st.info("No models match your filters, or your collection is empty. Add one above!")
    else:
        STATUS_EMOJI = {
            'Not Started': '⬜', 'In Progress': '🔧',
            'Completed': '✅', 'On Hold': '⏸️'
        }
        for _, row in display_df.iterrows():
            emoji = STATUS_EMOJI.get(row['status'], '⬜')
            sheets_str = f" • {row['sheets']}sh" if pd.notna(row.get('sheets')) and row.get('sheets') else ''
            label = f"{emoji} {row['name']}  ({row['model_id']}){sheets_str}  — {row['status']}"
            if st.button(label, key=f"btn_{row['model_id']}", use_container_width=True):
                st.session_state.selected_model = row['model_id']
                st.session_state.page = 'workbench'
                st.rerun()

# ─────────────────────────────────────────────
# 7.  WORKBENCH (DETAIL) PAGE
# ─────────────────────────────────────────────
elif st.session_state.page == 'workbench':
    model_id = st.session_state.selected_model
    model = get_model(model_id)

    if model is None:
        st.error("Model not found.")
        st.session_state.page = 'inventory'
        st.rerun()

    if st.button("⬅️ Back to Inventory"):
        st.session_state.page = 'inventory'
        st.session_state.selected_model = None
        st.rerun()

    st.title(f"🔧 {model['name']}")

    # Info strip
    inf1, inf2, inf3, inf4 = st.columns(4)
    inf1.metric("Model ID",   model['model_id'])
    inf2.metric("Category",   model['category'] or '—')
    inf3.metric("Difficulty", model['difficulty'] or '—')
    inf4.metric("Sheets",     model['sheets'] if pd.notna(model.get('sheets')) else '—')

    st.divider()

    left, right = st.columns([1, 1])

    # ── STATUS + RATING + NOTES ────────────────────
    with left:
        st.subheader("📋 Model Details")
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
                conn.commit()
                st.success("Saved!")
                st.rerun()

        # Delete button (outside form so it doesn't conflict)
        if st.button("🗑️ Remove from Collection", type="secondary"):
            c.execute("DELETE FROM Models WHERE model_id=?", (model_id,))
            c.execute("DELETE FROM Build_Logs WHERE model_id=?", (model_id,))
            conn.commit()
            st.session_state.page = 'inventory'
            st.session_state.selected_model = None
            st.rerun()

    # ── BUILD TIMER + LOG ──────────────────────────
    with right:
        st.subheader("⏱️ Build Sessions")
        st.metric("Total Time on This Kit", f"{total_time_minutes(model_id)} min")

        # Live timer
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
                     duration,
                     session_note))
                c.execute("UPDATE Models SET last_worked=?, status=? WHERE model_id=?",
                    (str(datetime.now().date()),
                     'In Progress' if model['status'] == 'Not Started' else model['status'],
                     model_id))
                conn.commit()
                del st.session_state.timer_start
                st.success(f"Logged {round(duration/60, 1)} minutes!")
                st.rerun()

        # Manual time entry
        st.write("---")
        st.write("**Or log time manually:**")
        with st.form("manual_log"):
            manual_mins = st.number_input("Minutes", min_value=1, value=30)
            manual_note = st.text_input("Note")
            if st.form_submit_button("Log Manual Session"):
                c.execute(
                    "INSERT INTO Build_Logs (model_id, start_time, duration, notes) VALUES (?,?,?,?)",
                    (model_id,
                     datetime.now().strftime("%Y-%m-%d %H:%M"),
                     manual_mins * 60,
                     manual_note))
                c.execute("UPDATE Models SET last_worked=? WHERE model_id=?",
                    (str(datetime.now().date()), model_id))
                conn.commit()
                st.success("Logged!")
                st.rerun()

    # ── BUILD HISTORY TABLE ────────────────────────
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
