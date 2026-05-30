import streamlit as st
import sqlite3
import pandas as pd
import datetime
import os

st.set_page_config(page_title="Metal Earth Tracker", page_icon="⚙️", layout="centered")
st.title("⚙️ Metal Earth Workbench")

# --- DATABASE SETUP ---
# SQLite creates this file in the server's working directory
db_file = 'metal_earth.db'
conn = sqlite3.connect(db_file, check_same_thread=False)
c = conn.cursor()

# Create Tables
c.execute('''CREATE TABLE IF NOT EXISTS Models (
    Model_ID TEXT PRIMARY KEY, Name TEXT, Brand TEXT, Product_line TEXT, Status TEXT, 
    Difficulty TEXT, Rating TEXT, Total_Build_Time REAL, Display_Time TEXT, Image TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS Build_Logs (
    Log_ID INTEGER PRIMARY KEY AUTOINCREMENT, 
    Model_ID TEXT, Date TEXT, Start_Time TEXT, End_Time TEXT, Session_Duration REAL, 
    Formatted_Duration TEXT, Model_Name_display TEXT)''')
conn.commit()

# --- BAKE IN DATA ---
def initialize_db():
    c.execute("SELECT count(*) FROM Models")
    if c.fetchone()[0] == 0:
        st.write("Database is empty. Attempting to import CSVs...")
        try:
            # Import Models
            models_csv = pd.read_csv('Models.csv')
            models_csv.to_sql('Models', conn, if_exists='append', index=False)
            
            # Import Logs
            logs_csv = pd.read_csv('Build_Logs.csv')
            logs_clean = logs_csv[['Model_ID', 'Date', 'Session_Duration']]
            logs_clean.to_sql('Build_Logs', conn, if_exists='append', index=False)
            
            conn.commit()
            st.success("Historical data successfully baked in!")
            st.rerun()
        except Exception as e:
            st.error(f"Error importing data: {e}")
            st.write("Check that 'Models.csv' and 'Build_Logs.csv' are in the same folder as 'metal_earth.py' on GitHub.")

initialize_db()

# --- LOAD DATA ---
models_df = pd.read_sql_query("SELECT * FROM Models", conn)
logs_df = pd.read_sql_query("SELECT * FROM Build_Logs", conn)

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📋 Dashboard", "⏱️ Workbench", "📦 Inventory"])

with tab1:
    st.header("Lifetime Stats")
    if not models_df.empty:
        st.write(f"Models in DB: {len(models_df)}")
        total_hours = round(logs_df['Session_Duration'].sum() / 3600, 1) if not logs_df.empty else 0
        st.metric("Total Build Time (Hours)", total_hours)
    else:
        st.warning("No data found in database.")

with tab2:
    st.header("Log a Build Session")
    if not models_df.empty:
        model_list = models_df['Model_ID'] + " - " + models_df['Name']
        selected_kit = st.selectbox("Select Model:", model_list)
        # (Rest of logging logic...)
        
with tab3:
    st.header("Master Inventory")
    st.dataframe(models_df)
