import streamlit as st
import sqlite3
import pandas as pd
import datetime
import os

# --- PAGE SETUP ---
st.set_page_config(page_title="Metal Earth Tracker", page_icon="⚙️", layout="centered")
st.title("⚙️ Metal Earth Workbench")

# --- DATABASE SETUP ---
db_file = 'metal_earth.db'
conn = sqlite3.connect(db_file, check_same_thread=False)
c = conn.cursor()

# Create Tables
c.execute('''CREATE TABLE IF NOT EXISTS Models (Model_ID TEXT PRIMARY KEY, Name TEXT, Brand TEXT, Product_line TEXT, Status TEXT, Difficulty TEXT, Rating TEXT, Total_Build_Time REAL, Display_Time TEXT, Image TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS Build_Logs (Log_ID INTEGER PRIMARY KEY AUTOINCREMENT, Model_ID TEXT, Date TEXT, Start_Time TEXT, End_Time TEXT, Session_Duration REAL, Formatted_Duration TEXT, Model_Name_display TEXT)''')

# --- BAKE IN DATA (ONLY RUNS ONCE) ---
def initialize_db():
    # Check if data exists
    c.execute("SELECT count(*) FROM Models")
    if c.fetchone()[0] == 0:
        # Import Models
        models_csv = pd.read_csv('Models.csv')
        models_csv.to_sql('Models', conn, if_exists='append', index=False)
        # Import Logs
        logs_csv = pd.read_csv('Build_Logs.csv')
        logs_csv.to_sql('Build_Logs', conn, if_exists='append', index=False)
        conn.commit()
        st.success("Historical data baked in successfully!")

initialize_db()

# --- LOAD DATA ---
models_df = pd.read_sql_query("SELECT * FROM Models", conn)
logs_df = pd.read_sql_query("SELECT * FROM Build_Logs", conn)

# --- APP NAVIGATION ---
tab1, tab2, tab3, tab4 = st.tabs(["📋 Dashboard", "⏱️ Workbench", "📦 Inventory", "💾 Export Data"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("Lifetime Stats")
    col1, col2 = st.columns(2)
    total_hours = round(logs_df['Session_Duration'].sum() / 3600, 1) if not logs_df.empty else 0
    completed_kits = len(models_df[models_df['Status'] == 'Complete'])
    col1.metric("Total Build Time (Hours)", total_hours)
    col2.metric("Completed Models", completed_kits)

# --- TAB 2: WORKBENCH ---
with tab2:
    st.header("Log a Build Session")
    model_list = models_df['Model_ID'] + " - " + models_df['Name']
    selected_kit = st.selectbox("Select Model:", model_list)
    kit_id = selected_kit.split(" - ")[0]
    
    minutes_worked = st.number_input("Minutes Worked:", min_value=1, value=30)
    if st.button("💾 Save Session"):
        c.execute("INSERT INTO Build_Logs (Model_ID, Date, Session_Duration) VALUES (?, ?, ?)", 
                  (kit_id, datetime.datetime.now().strftime("%Y-%m-%d"), minutes_worked * 60))
        conn.commit()
        st.success("Session logged!")
        st.rerun()

# --- TAB 3: INVENTORY ---
with tab3:
    st.header("Master Inventory")
    st.dataframe(models_df[["Model_ID", "Name", "Status", "Difficulty"]], use_container_width=True)

# --- TAB 4: EXPORT ---
with tab4:
    st.header("💾 Export Data")
    if st.download_button("Download Models CSV", models_df.to_csv(index=False), "models_export.csv"):
        pass
