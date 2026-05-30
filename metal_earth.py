import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Metal Earth Workbench", layout="centered")
st.title("⚙️ Metal Earth Workbench")

conn = sqlite3.connect('models_db.db', check_same_thread=False)
c = conn.cursor()

c.execute('CREATE TABLE IF NOT EXISTS Models (Model_ID TEXT PRIMARY KEY, Name TEXT, Status TEXT, Last_Worked TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS Build_Logs (Log_ID INTEGER PRIMARY KEY AUTOINCREMENT, Model_ID TEXT, Start_Time TEXT, Duration REAL, Notes TEXT)')
conn.commit()

# --- NAVIGATION ---
if 'selected_model' not in st.session_state: st.session_state.selected_model = None

# --- MASTER VIEW ---
if st.session_state.selected_model is None:
    # ADD NEW MODEL FORM
    with st.expander("➕ Add New Model"):
        with st.form("add_model"):
            new_id = st.text_input("Model ID (e.g., MMS180)")
            new_name = st.text_input("Model Name")
            if st.form_submit_button("Create Kit"):
                if new_id:
                    c.execute("INSERT OR IGNORE INTO Models (Model_ID, Name, Status, Last_Worked) VALUES (?,?,?,?)", 
                              (new_id, new_name, 'Not Started', datetime.now().date()))
                    conn.commit()
                    st.rerun()

    st.header("Inventory")
    models = pd.read_sql_query("SELECT * FROM Models ORDER BY Last_Worked DESC", conn)
    for _, row in models.iterrows():
        if st.button(f"{row['Name']}", key=row['Model_ID']):
            st.session_state.selected_model = row['Model_ID']
            st.rerun()

# --- DETAIL VIEW (THE WORKBENCH) ---
else:
    model_id = st.session_state.selected_model
    model = pd.read_sql_query(f"SELECT * FROM Models WHERE Model_ID='{model_id}'", conn).iloc[0]
    
    if st.button("⬅️ Back"):
        st.session_state.selected_model = None
        st.rerun()
        
    st.header(f"Workbench: {model['Name']}")
    
    logs = pd.read_sql_query(f"SELECT * FROM Build_Logs WHERE Model_ID='{model_id}'", conn)
    total_min = round(logs['Duration'].sum() / 60, 1) if not logs.empty else 0
    st.metric("Total Time Spent (Minutes)", total_min)

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
