import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Metal Earth Workbench", layout="centered")

# --- DATABASE SETUP ---
conn = sqlite3.connect('models_db.db', check_same_thread=False)
c = conn.cursor()

# Ensure schema is up to date
c.execute('''CREATE TABLE IF NOT EXISTS Models 
             (Model_ID TEXT PRIMARY KEY, Name TEXT, Brand TEXT, Product_line TEXT, 
              Status TEXT, Difficulty TEXT, Rating TEXT, Notes TEXT, Last_Worked TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS Build_Logs 
             (Log_ID INTEGER PRIMARY KEY AUTOINCREMENT, Model_ID TEXT, 
              Start_Time TEXT, Duration REAL, Notes TEXT)''')
conn.commit()

# --- NAVIGATION ---
if 'selected_model' not in st.session_state: st.session_state.selected_model = None

# --- MASTER VIEW ---
if st.session_state.selected_model is None:
    st.title("⚙️ Metal Earth Workbench")
    with st.expander("➕ Add New Model"):
        with st.form("add_model"):
            new_id = st.text_input("Model ID")
            new_name = st.text_input("Name")
            if st.form_submit_button("Create Kit"):
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
    # Fetch row as a dictionary-like object to handle missing columns safely
    df = pd.read_sql_query(f"SELECT * FROM Models WHERE Model_ID='{model_id}'", conn)
    model = df.iloc[0]
    
    if st.button("⬅️ Back to Inventory"):
        st.session_state.selected_model = None
        st.rerun()
        
    st.title(f"{model['Name']}")
    # Use .get() to safely access columns that might be missing in older DB files
    brand = model.get('Brand', 'N/A') if 'Brand' in model else 'N/A'
    line = model.get('Product_line', 'N/A') if 'Product_line' in model else 'N/A'
    rating = model.get('Rating', 'N/A') if 'Rating' in model else 'N/A'
    st.caption(f"Brand: {brand} | Line: {line} | Rating: {rating}")
    
    logs = pd.read_sql_query(f"SELECT * FROM Build_Logs WHERE Model_ID='{model_id}'", conn)
    st.metric("Total Time (Minutes)", round(logs['Duration'].sum() / 60, 1) if not logs.empty else 0)

    # Timer logic
    if 'timer_start' not in st.session_state:
        if st.button("▶️ Start Session"):
            st.session_state.timer_start = datetime.now()
            st.rerun()
    else:
        if st.button("⏹️ Stop Session"):
            duration = (datetime.now() - st.session_state.timer_start).total_seconds()
            c.execute("INSERT INTO Build_Logs (Model_ID, Start_Time, Duration) VALUES (?,?,?)",
                      (model_id, st.session_state.timer_start.strftime("%Y-%m-%d %H:%M"), duration))
            c.execute("UPDATE Models SET Last_Worked=? WHERE Model_ID=?", (datetime.now().date(), model_id))
            conn.commit()
            del st.session_state.timer_start
            st.rerun()

    with st.expander("✏️ Edit Model Details"):
        with st.form("edit_model"):
            e_diff = st.text_input("Difficulty", value=model.get('Difficulty', '') if 'Difficulty' in model else '')
            e_rate = st.text_input("Rating", value=model.get('Rating', '') if 'Rating' in model else '')
            e_note = st.text_area("Notes", value=model.get('Notes', '') if 'Notes' in model else '')
            if st.form_submit_button("Update Info"):
                # Ensure the columns exist before updating by re-running the creation logic if needed
                c.execute("UPDATE Models SET Difficulty=?, Rating=?, Notes=? WHERE Model_ID=?", (e_diff, e_rate, e_note, model_id))
                conn.commit()
                st.rerun()

    st.subheader("Build History")
    st.dataframe(logs[["Start_Time", "Duration", "Notes"]])
