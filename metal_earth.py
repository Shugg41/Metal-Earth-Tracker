import streamlit as st
import sqlite3
import pandas as pd
import datetime

st.set_page_config(page_title="Metal Earth Tracker", page_icon="⚙️", layout="centered")
st.title("⚙️ Metal Earth Workbench")

# --- DATABASE SETUP ---
conn = sqlite3.connect('metal_earth.db', check_same_thread=False)
c = conn.cursor()

# FORCE RE-CREATION: Drop tables so we start perfectly fresh every time
c.execute('DROP TABLE IF EXISTS Models')
c.execute('DROP TABLE IF EXISTS Build_Logs')

c.execute('''CREATE TABLE Models (
    Model_ID TEXT PRIMARY KEY, Name TEXT, Brand TEXT, Product_line TEXT, 
    Status TEXT, Difficulty TEXT, Rating TEXT, Total_Build_Time REAL)''')

c.execute('''CREATE TABLE Build_Logs (
    Log_ID INTEGER PRIMARY KEY AUTOINCREMENT, 
    Model_ID TEXT, Date TEXT, Session_Duration REAL)''')
conn.commit()

# --- DATA INJECTION ---
# This will now run every time, ensuring tables are perfectly aligned with data
models_data = [
    ('MMS180', 'P-51D Mustang Sweet Arlene', 'Metal Earth', 'Standard', 'Complete', '7', '7', 9.999),
    ('MMS325', 'Black Panther', 'Metal Earth', 'Marvel', 'Complete', '9.5', '10', 0),
    ('MMS123', 'Monarch Butterfly', 'Metal Earth', 'Standard', 'Complete', '2', '2', 0),
    ('MMS568', 'USPS LLV Mail Truck', 'Metal Earth', 'Standard', 'Not Started', '4', '0', 0),
    ('SYS', 'SYS', 'Other', 'Other', 'In Progress', '0', '0', 0)
]
c.executemany("INSERT INTO Models VALUES (?,?,?,?,?,?,?,?)", models_data)

logs_data = [('MMS180', '2026-05-28', 9.999)]
c.executemany("INSERT INTO Build_Logs (Model_ID, Date, Session_Duration) VALUES (?,?,?)", logs_data)
conn.commit()

# --- APP INTERFACE ---
models_df = pd.read_sql_query("SELECT * FROM Models", conn)
logs_df = pd.read_sql_query("SELECT * FROM Build_Logs", conn)

tab1, tab2, tab3 = st.tabs(["📋 Dashboard", "⏱️ Workbench", "📦 Inventory"])

with tab1:
    st.header("Lifetime Stats")
    st.metric("Total Build Time (Hours)", round(logs_df['Session_Duration'].sum() / 3600, 1) if not logs_df.empty else 0)
    st.metric("Completed Models", len(models_df[models_df['Status'] == 'Complete']) if not models_df.empty else 0)

with tab2:
    st.header("Log Session")
    model_list = models_df['Model_ID'] + " - " + models_df['Name']
    selected = st.selectbox("Select Model:", model_list)
    kit_id = selected.split(" - ")[0]
    mins = st.number_input("Minutes:", min_value=1, value=30)
    if st.button("Save"):
        c.execute("INSERT INTO Build_Logs (Model_ID, Date, Session_Duration) VALUES (?, ?, ?)", 
                  (kit_id, datetime.datetime.now().strftime("%Y-%m-%d"), mins * 60))
        conn.commit()
        st.rerun()

with tab3:
    st.header("Inventory")
    st.dataframe(models_df[["Model_ID", "Name", "Status", "Difficulty"]], use_container_width=True)
