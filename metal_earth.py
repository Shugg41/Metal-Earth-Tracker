import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# --- PAGE SETUP ---
st.set_page_config(page_title="Metal Earth Workbench", layout="centered")
st.title("⚙️ Metal Earth Workbench")

# Ensure image directory exists
if not os.path.exists("images"): os.makedirs("images")

# --- DATABASE SETUP ---
conn = sqlite3.connect('models_db.db', check_same_thread=False)
c = conn.cursor()

# Tables (ID link established)
c.execute('''CREATE TABLE IF NOT EXISTS Models 
             (Model_ID TEXT PRIMARY KEY, Name TEXT, Status TEXT, Last_Worked TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS Build_Logs 
             (Log_ID INTEGER PRIMARY KEY AUTOINCREMENT, Model_ID TEXT, 
              Start_Time TEXT, End_Time TEXT, Duration REAL, Notes TEXT, Image_Path TEXT)''')
conn.commit()

# --- INITIALIZATION ---
if pd.read_sql_query("SELECT count(*) FROM Models", conn).iloc[0,0] == 0:
    c.executemany("INSERT INTO Models VALUES (?,?,?,?)", 
                  [('MMS180', 'P-51D Mustang', 'Complete', '2026-05-28'), 
                   ('MMS325', 'Black Panther', 'Complete', '2026-05-28')])
    conn.commit()

# --- NAVIGATION ---
if 'selected_model' not in st.session_state: st.session_state.selected_model = None

# --- MASTER VIEW ---
if st.session_state.selected_model is None:
    st.header("Inventory")
    models = pd.read_sql_query("SELECT * FROM Models ORDER BY Last_Worked DESC", conn)
    for _, row in models.iterrows():
        if st.button(f"{row['Name']} (Last: {row['Last_Worked']})", key=row['Model_ID']):
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
    
    # Timer Functionality
    if 'timer_start' not in st.session_state:
        if st.button("▶️ Start Session"):
            st.session_state.timer_start = datetime.now()
    else:
        if st.button("⏹️ Stop Session"):
            duration = (datetime.now() - st.session_state.timer_start).total_seconds()
            c.execute("INSERT INTO Build_Logs (Model_ID, Start_Time, End_Time, Duration) VALUES (?,?,?,?)",
                      (model_id, st.session_state.timer_start, datetime.now(), duration))
            c.execute("UPDATE Models SET Last_Worked=? WHERE Model_ID=?", (datetime.now().date(), model_id))
            conn.commit()
            del st.session_state.timer_start
            st.success("Session logged!")
            st.rerun()

    # Manual Add & Photo
    with st.expander("➕ Add Manual Log / Photo"):
        notes = st.text_input("Notes")
        uploaded_file = st.file_uploader("Progress Photo", type=['jpg', 'png'])
        if st.button("Save Manual Entry"):
            img_path = None
            if uploaded_file:
                img_path = f"images/{model_id}_{datetime.now().strftime('%Y%m%d%H%M')}.jpg"
                with open(img_path, "wb") as f: f.write(uploaded_file.getbuffer())
            c.execute("INSERT INTO Build_Logs (Model_ID, Notes, Image_Path) VALUES (?,?,?)", (model_id, notes, img_path))
            conn.commit()
            st.rerun()

    # Log History Table
    st.subheader("History")
    logs = pd.read_sql_query(f"SELECT * FROM Build_Logs WHERE Model_ID='{model_id}'", conn)
    st.dataframe(logs)
