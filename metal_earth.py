import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- DATABASE SETUP ---
# SQLite is our temporary "local" storage while we build.
conn = sqlite3.connect('models_db.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS Models (Model_ID TEXT PRIMARY KEY, Name TEXT, Status TEXT, Last_Worked TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS Build_Logs (Log_ID INTEGER PRIMARY KEY AUTOINCREMENT, Model_ID TEXT, Start_Time TEXT, Duration REAL, Notes TEXT)')
conn.commit()

# --- INITIALIZATION ---
c.execute("SELECT count(*) FROM Models")
if c.fetchone()[0] == 0:
    c.executemany("INSERT INTO Models VALUES (?,?,?,?)", 
                  [('MMS180', 'P-51D Mustang', 'Complete', '2026-05-28'), ('MMS325', 'Black Panther', 'Complete', '2026-05-28')])
    conn.commit()

# --- NAVIGATION ---
if 'selected_model' not in st.session_state: st.session_state.selected_model = None

# --- UI LOGIC ---
if st.session_state.selected_model is None:
    st.header("Inventory")
    models = pd.read_sql_query("SELECT * FROM Models ORDER BY Last_Worked DESC", conn)
    for _, row in models.iterrows():
        if st.button(f"{row['Name']}", key=row['Model_ID']):
            st.session_state.selected_model = row['Model_ID']
            st.rerun()
else:
    model_id = st.session_state.selected_model
    model = pd.read_sql_query(f"SELECT * FROM Models WHERE Model_ID='{model_id}'", conn).iloc[0]
    
    if st.button("⬅️ Back"):
        st.session_state.selected_model = None
        st.rerun()
        
    st.header(f"Workbench: {model['Name']}")
    
    # --- METRICS ---
    logs = pd.read_sql_query(f"SELECT * FROM Build_Logs WHERE Model_ID='{model_id}'", conn)
    total_min = round(logs['Duration'].sum() / 60, 1) if not logs.empty else 0
    st.metric("Total Time Spent (Minutes)", total_min)

    # --- TIMER ---
    if 'timer_start' not in st.session_state:
        if st.button("▶️ Start Session"):
            st.session_state.timer_start = datetime.now()
            st.rerun()
    else:
        if st.button("⏹️ Stop Session"):
            duration = (datetime.now() - st.session_state.timer_start).total_seconds()
            c.execute("INSERT INTO Build_Logs (Model_ID, Start_Time, Duration) VALUES (?,?,?)",
                      (model_id, st.session_state.timer_start, duration))
            c.execute("UPDATE Models SET Last_Worked=? WHERE Model_ID=?", (datetime.now().date(), model_id))
            conn.commit()
            del st.session_state.timer_start
            st.rerun()

    # --- MANUAL ENTRY ---
    with st.expander("➕ Add Missing Time"):
        with st.form("manual"):
            m_min = st.number_input("Minutes Worked", min_value=1)
            m_note = st.text_input("Notes")
            if st.form_submit_button("Log"):
                c.execute("INSERT INTO Build_Logs (Model_ID, Duration, Notes) VALUES (?,?,?)", 
                          (model_id, m_min * 60, m_note))
                conn.commit()
                st.rerun()

    st.subheader("Build History")
    st.dataframe(logs[["Start_Time", "Duration", "Notes"]])
