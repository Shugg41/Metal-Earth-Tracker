import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- DATABASE SETUP ---
def get_db():
    conn = sqlite3.connect('models_db.db', check_same_thread=False)
    return conn

# Create tables
conn = get_db()
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS Models 
             (Model_ID TEXT PRIMARY KEY, Name TEXT, Status TEXT, Last_Worked TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS Build_Logs 
             (Log_ID INTEGER PRIMARY KEY AUTOINCREMENT, Model_ID TEXT, 
              Start_Time TEXT, End_Time TEXT, Duration REAL, Notes TEXT, Image_Path TEXT)''')

# Hard-coded injection (Only runs if DB is empty)
c.execute("SELECT count(*) FROM Models")
if c.fetchone()[0] == 0:
    models = [('MMS180', 'P-51D Mustang', 'Complete', '2026-05-28'), ('MMS325', 'Black Panther', 'Complete', '2026-05-28')]
    c.executemany("INSERT INTO Models VALUES (?,?,?,?)", models)
    conn.commit()

# --- APP UI ---
st.title("⚙️ Metal Earth Workbench")

# Navigation logic: Use session state to track if we are viewing a specific model
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = None

# --- MASTER VIEW (LIST) ---
if st.session_state.selected_model is None:
    st.header("Your Inventory")
    models = pd.read_sql_query("SELECT * FROM Models ORDER BY Last_Worked DESC", conn)
    
    for i, row in models.iterrows():
        if st.button(f"{row['Name']} (Last: {row['Last_Worked']})", key=row['Model_ID']):
            st.session_state.selected_model = row['Model_ID']
            st.rerun()

# --- DETAIL VIEW ---
else:
    model_id = st.session_state.selected_model
    model = pd.read_sql_query(f"SELECT * FROM Models WHERE Model_ID='{model_id}'", conn).iloc[0]
    
    if st.button("⬅️ Back to Inventory"):
        st.session_state.selected_model = None
        st.rerun()
        
    st.header(f"Workbench: {model['Name']}")
    
    # Timer logic
    if 'start_time' not in st.session_state:
        if st.button("▶️ Start Session"):
            st.session_state.start_time = datetime.now()
    else:
        if st.button("⏹️ Stop Session"):
            duration = (datetime.now() - st.session_state.start_time).total_seconds()
            c.execute("INSERT INTO Build_Logs (Model_ID, Start_Time, End_Time, Duration) VALUES (?,?,?,?)",
                      (model_id, st.session_state.start_time, datetime.now(), duration))
            c.execute("UPDATE Models SET Last_Worked=? WHERE Model_ID=?", (datetime.now().date(), model_id))
            conn.commit()
            del st.session_state.start_time
            st.success("Session logged!")
            st.rerun()

    # Display Logs
    st.subheader("Build History")
    logs = pd.read_sql_query(f"SELECT * FROM Build_Logs WHERE Model_ID='{model_id}'", conn)
    st.dataframe(logs)
