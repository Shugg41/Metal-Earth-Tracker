import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURATION & DATABASE ---
st.set_page_config(page_title="Metal Earth Workbench", layout="centered")
conn = sqlite3.connect('models_db.db', check_same_thread=False)
c = conn.cursor()

# Ensure table schema is correct (adding columns for your Glide features)
c.execute('''CREATE TABLE IF NOT EXISTS Models 
             (Model_ID TEXT PRIMARY KEY, Name TEXT, Brand TEXT, Product_line TEXT, 
              Status TEXT, Difficulty TEXT, Rating TEXT, Notes TEXT, Last_Worked TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS Build_Logs 
             (Log_ID INTEGER PRIMARY KEY AUTOINCREMENT, Model_ID TEXT, 
              Start_Time TEXT, Duration REAL, Notes TEXT)''')
conn.commit()

# --- STATE MANAGEMENT ---
if 'selected_model' not in st.session_state: st.session_state.selected_model = None

# --- UI: MASTER LIST (HOME) ---
if st.session_state.selected_model is None:
    st.title("⚙️ Metal Earth Workbench")
    
    with st.expander("➕ Add New Model"):
        with st.form("add_model"):
            new_id = st.text_input("Model ID (e.g. MMS180)")
            new_name = st.text_input("Name")
            new_brand = st.text_input("Brand")
            new_line = st.text_input("Product Line")
            if st.form_submit_button("Create Kit"):
                c.execute("INSERT OR IGNORE INTO Models (Model_ID, Name, Brand, Product_line, Status, Last_Worked) VALUES (?,?,?,?,?,?)", 
                          (new_id, new_name, new_brand, new_line, 'Not Started', datetime.now().date()))
                conn.commit()
                st.rerun()

    st.header("Inventory")
    models = pd.read_sql_query("SELECT * FROM Models ORDER BY Last_Worked DESC", conn)
    
    for _, row in models.iterrows():
        # Replicating Glide card-like style
        with st.container():
            col1, col2 = st.columns([3, 1])
            col1.subheader(row['Name'])
            col1.write(f"Status: {row['Status']} | Difficulty: {row.get('Difficulty', 'N/A')}")
            if col2.button("Open Workbench", key=f"btn_{row['Model_ID']}"):
                st.session_state.selected_model = row['Model_ID']
                st.rerun()
            st.divider()

# --- UI: DETAIL VIEW (WORKBENCH) ---
else:
    model_id = st.session_state.selected_model
    model = pd.read_sql_query(f"SELECT * FROM Models WHERE Model_ID='{model_id}'", conn).iloc[0]
    
    if st.button("⬅️ Back to Inventory"):
        st.session_state.selected_model = None
        st.rerun()
        
    st.title(f"{model['Name']}")
    st.caption(f"Brand: {model['Brand']} | Line: {model['Product_line']} | Rating: {model.get('Rating', 'N/A')}")
    
    logs = pd.read_sql_query(f"SELECT * FROM Build_Logs WHERE Model_ID='{model_id}'", conn)
    total_min = round(logs['Duration'].sum() / 60, 1) if not logs.empty else 0
    st.metric("Total Build Time (Minutes)", total_min)

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

    with st.expander("✏️ Edit Model Details / Manual Log"):
        with st.form("edit_model"):
            e_diff = st.text_input("Difficulty", value=str(model.get('Difficulty', '')))
            e_rate = st.text_input("Rating", value=str(model.get('Rating', '')))
            e_note = st.text_area("Notes", value=str(model.get('Notes', '')))
            m_min = st.number_input("Add Missing Time (Minutes)", min_value=0)
            if st.form_submit_button("Save Updates"):
                c.execute("UPDATE Models SET Difficulty=?, Rating=?, Notes=? WHERE Model_ID=?", (e_diff, e_rate, e_note, model_id))
                if m_min > 0:
                    c.execute("INSERT INTO Build_Logs (Model_ID, Duration) VALUES (?,?)", (model_id, m_min * 60))
                conn.commit()
                st.rerun()

    st.subheader("Build History")
    st.dataframe(logs[["Start_Time", "Duration", "Notes"]].sort_values(by="Start_Time", ascending=False))
