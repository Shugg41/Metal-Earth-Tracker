import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Metal Earth Workbench", layout="wide")
st.title("⚙️ Metal Earth Workbench")

# --- DATA LOAD ---
# The app will look for the CSV file you just uploaded to GitHub
try:
    master_df = pd.read_csv('metal_earth_models.csv')
    # Standardize column names to lowercase to prevent mapping errors
    master_df.columns = master_df.columns.str.lower()
except FileNotFoundError:
    st.error("Missing 'metal_earth_models.csv'. Please upload it to your GitHub repo.")
    master_df = pd.DataFrame(columns=['model_id', 'name', 'difficulty', 'category'])

# --- DATABASE SETUP ---
conn = sqlite3.connect('models_db.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS Models 
             (model_id TEXT PRIMARY KEY, name TEXT, category TEXT, 
              status TEXT, difficulty TEXT, rating INTEGER, notes TEXT, last_worked TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS Build_Logs 
             (log_id INTEGER PRIMARY KEY AUTOINCREMENT, model_id TEXT, 
              start_time TEXT, duration REAL, notes TEXT)''')
conn.commit()

# --- NAVIGATION ---
if 'selected_model' not in st.session_state: st.session_state.selected_model = None

# --- MASTER LIST (HOME) ---
if st.session_state.selected_model is None:
    with st.expander("➕ Add New Model"):
        with st.form("add_model"):
            search_id = st.text_input("Enter Model ID (e.g., MMS180) to Auto-Fill")
            
            # Lookup logic
            match = master_df[master_df['model_id'].str.upper() == search_id.upper()]
            
            if not match.empty:
                st.success(f"Found: {match.iloc[0]['name']}")
                name_val = match.iloc[0]['name']
                cat_val = match.iloc[0]['category']
                diff_val = match.iloc[0]['difficulty']
            else:
                name_val = st.text_input("Name")
                cat_val = st.text_input("Category")
                diff_val = st.text_input("Difficulty")

            if st.form_submit_button("Create Kit"):
                c.execute("INSERT OR IGNORE INTO Models (model_id, name, category, status, difficulty, last_worked) VALUES (?,?,?,?,?,?)", 
                          (search_id, name_val, cat_val, 'Not Started', diff_val, datetime.now().date()))
                conn.commit()
                st.rerun()

    st.header("Inventory")
    models = pd.read_sql_query("SELECT * FROM Models ORDER BY last_worked DESC", conn)
    for _, row in models.iterrows():
        if st.button(f"{row['name']} ({row.get('status', 'Not Started')})", key=row['model_id']):
            st.session_state.selected_model = row['model_id']
            st.rerun()

# --- DETAIL VIEW (THE WORKBENCH) ---
else:
    model_id = st.session_state.selected_model
    # Fetch model row
    model = pd.read_sql_query(f"SELECT * FROM Models WHERE model_id='{model_id}'", conn).iloc[0]
    
    if st.button("⬅️ Back"):
        st.session_state.selected_model = None
        st.rerun()
        
    st.title(f"Workbench: {model['name']}")
    
    # Edit Form
    with st.expander("✏️ Edit Model Details"):
        with st.form("edit_model"):
            e_rate = st.slider("Rating", 1, 10, int(model.get('rating') or 1))
            e_note = st.text_area("Notes", value=str(model.get('notes') or ""))
            if st.form_submit_button("Save"):
                c.execute("UPDATE Models SET rating=?, notes=? WHERE model_id=?", (e_rate, e_note, model_id))
                conn.commit()
                st.rerun()

    # Metrics & Timer
    logs = pd.read_sql_query(f"SELECT * FROM Build_Logs WHERE model_id='{model_id}'", conn)
    st.metric("Total Time (Minutes)", round(logs['duration'].sum() / 60, 1) if not logs.empty else 0)

    if 'timer_start' not in st.session_state:
        if st.button("▶️ Start Session"):
            st.session_state.timer_start = datetime.now()
            st.rerun()
    else:
        if st.button("⏹️ Stop Session"):
            duration = (datetime.now() - st.session_state.timer_start).total_seconds()
            c.execute("INSERT INTO Build_Logs (model_id, start_time, duration) VALUES (?,?,?)",
                      (model_id, st.session_state.timer_start.strftime("%Y-%m-%d %H:%M"), duration))
            c.execute("UPDATE Models SET last_worked=? WHERE model_id=?", (datetime.now().date(), model_id))
            conn.commit()
            del st.session_state.timer_start
            st.rerun()

    st.subheader("Build History")
    st.dataframe(logs[["start_time", "duration", "notes"]])
