import streamlit as st
import sqlite3
import pandas as pd
import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Metal Earth Tracker", page_icon="⚙️", layout="centered")
st.title("⚙️ Metal Earth Workbench")

# --- DATABASE SETUP ---
db_file = 'metal_earth.db'
conn = sqlite3.connect(db_file, check_same_thread=False)
c = conn.cursor()

# Create Tables (Updated to match the 8 fields in the injection)
c.execute('''CREATE TABLE IF NOT EXISTS Models (
    Model_ID TEXT PRIMARY KEY, Name TEXT, Brand TEXT, Product_line TEXT, 
    Status TEXT, Difficulty TEXT, Rating TEXT, Total_Build_Time REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS Build_Logs (
    Log_ID INTEGER PRIMARY KEY AUTOINCREMENT, 
    Model_ID TEXT, Date TEXT, Session_Duration REAL)''')
conn.commit()

# --- HARD-CODED DATA INJECTION ---
def initialize_db():
    c.execute("SELECT count(*) FROM Models")
    if c.fetchone()[0] == 0:
        # Inject Models (Must have 8 values per row to match table above)
        models_data = [
            ('MMS180', 'P-51D Mustang "Sweet Arlene"', 'Metal Earth', 'Standard', 'Complete', '7', '7', 9.999),
            ('MMS325', 'Black Panther', 'Metal Earth', 'Marvel', 'Complete', '9.5', '10', 0),
            ('MMS123', 'Monarch Butterfly', 'Metal Earth', 'Standard', 'Complete', '2', '2', 0),
            ('MMS568', 'USPS LLV Mail Truck', 'Metal Earth', 'Standard', 'Not Started', '4', '0', 0),
            ('SYS', 'SYS', 'Other', 'Other', 'In Progress', '0', '0', 0)
        ]
        c.executemany("INSERT OR IGNORE INTO Models VALUES (?,?,?,?,?,?,?,?)", models_data)
        
        # Inject Logs
        logs_data = [('MMS180', '2026-05-28', 9.999)]
        c.executemany("INSERT INTO Build_Logs (Model_ID, Date, Session_Duration) VALUES (?,?,?)", logs_data)
        
        conn.commit()
        st.success("Historical data successfully injected!")
        st.rerun()

initialize_db()

# --- LOAD DATA ---
models_df = pd.read_sql_query("SELECT * FROM Models", conn)
logs_df = pd.read_sql_query("SELECT * FROM Build_Logs", conn)

# --- APP NAVIGATION ---
tab1, tab2, tab3 = st.tabs(["📋 Dashboard", "⏱️ Workbench", "📦 Inventory"])

with tab1:
    st.header("Lifetime Stats")
    total_hours = round(logs_df['Session_Duration'].sum() / 3600, 1) if not logs_df.empty else 0
    completed_kits = len(models_df[models_df['Status'] == 'Complete']) if not models_df.empty else 0
    st.metric("Total Build Time (Hours)", total_hours)
    st.metric("Completed Models", completed_kits)

with tab2:
    st.header("Log a Build Session")
    if not models_df.empty:
        model_list = models_df['Model_ID'] + " - " + models_df['Name']
        selected_kit = st.selectbox("Select Model:", model_list)
        kit_id = selected_kit.split(" - ")[0]
        
        minutes = st.number_input("Minutes Worked:", min_value=1, value=30)
        if st.button("💾 Save Session"):
            c.execute("INSERT INTO Build_Logs (Model_ID, Date, Session_Duration) VALUES (?, ?, ?)", 
                      (kit_id, datetime.datetime.now().strftime("%Y-%m-%d"), minutes * 60))
            conn.commit()
            st.rerun()

with tab3:
    st.header("Master Inventory")
    st.dataframe(models_df[["Model_ID", "Name", "Status", "Difficulty"]], use_container_width=True)
