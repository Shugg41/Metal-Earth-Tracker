import streamlit as st
import sqlite3
import pandas as pd
import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Metal Earth Tracker", page_icon="⚙️", layout="centered")
st.title("⚙️ Metal Earth Workbench")

# --- DATABASE SETUP (SQLite) ---
# This automatically creates the file 'metal_earth.db' in your GitHub repo/Streamlit app
conn = sqlite3.connect('metal_earth.db', check_same_thread=False)
c = conn.cursor()

# Create Tables if they don't exist
c.execute('''
    CREATE TABLE IF NOT EXISTS Models (
        Model_ID TEXT PRIMARY KEY,
        Name TEXT,
        Brand TEXT,
        Product_Line TEXT,
        Status TEXT,
        Difficulty TEXT,
        Reference_URL TEXT,
        Rating TEXT,
        Final_Review TEXT,
        Image TEXT
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS Build_Logs (
        Log_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Model_ID TEXT,
        Date TEXT,
        Start_Time TEXT,
        End_Time TEXT,
        Duration INTEGER,
        Session_Notes TEXT,
        Progress_Image TEXT,
        FOREIGN KEY(Model_ID) REFERENCES Models(Model_ID)
    )
''')
conn.commit()

# --- LOAD DATA ---
def load_models():
    return pd.read_sql_query("SELECT * FROM Models", conn)

def load_logs():
    return pd.read_sql_query("SELECT * FROM Build_Logs", conn)

models_df = load_models()
logs_df = load_logs()

# --- APP NAVIGATION ---
tab1, tab2, tab3, tab4 = st.tabs(["📋 Dashboard", "⏱️ Workbench", "📦 Inventory", "💾 Export Data"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("Lifetime Stats")
    col1, col2 = st.columns(2)
    
    total_seconds = logs_df['Duration'].sum() if not logs_df.empty else 0
    total_hours = round(total_seconds / 3600, 1)
    completed_kits = len(models_df[models_df['Status'] == 'Completed']) if not models_df.empty else 0
    
    col1.metric("Total Build Time (Hours)", total_hours)
    col2.metric("Completed Models", completed_kits)

    st.divider()
    st.subheader("Active Workbench (In Progress)")
    if not models_df.empty:
        active_models = models_df[models_df['Status'] == 'In Progress']
        if active_models.empty:
            st.info("No models currently in progress. Start one in the Inventory tab!")
        else:
            for index, row in active_models.iterrows():
                st.write(f"**{row['Name']}** ({row['Model_ID']}) - {row['Brand']}")

# --- TAB 2: WORKBENCH (LOGGING TIME) ---
with tab2:
    st.header("Log a Build Session")
    
    if models_df.empty:
        st.warning("Go to the Inventory tab to add a model first!")
    else:
        # Dropdown to select kit
        model_list = models_df['Model_ID'] + " - " + models_df['Name']
        selected_kit = st.selectbox("Select Model:", model_list)
        kit_id = selected_kit.split(" - ")[0]
        
        st.write("---")
        minutes_worked = st.number_input("Minutes Worked:", min_value=1, value=30)
        session_notes = st.text_input("Session Notes (Optional):")
        
        if st.button("💾 Save Session"):
            duration_seconds = minutes_worked * 60
            today_date = datetime.datetime.now().strftime("%Y-%m-%d")
            
            c.execute("INSERT INTO Build_Logs (Model_ID, Date, Duration, Session_Notes) VALUES (?, ?, ?, ?)", 
                      (kit_id, today_date, duration_seconds, session_notes))
            conn.commit()
            st.success(f"Successfully logged {minutes_worked} minutes for {kit_id}!")
            st.rerun()

# --- TAB 3: INVENTORY ---
with tab3:
    st.header("Master Inventory")
    
    # Form to add new kits
    with st.expander("➕ Add New Kit"):
        with st.form("new_kit_form"):
            new_id = st.text_input("Model ID (e.g. MMS180)")
            new_name = st.text_input("Name")
            new_brand = st.text_input("Brand", value="Metal Earth")
            new_status = st.selectbox("Status", ["Not Started", "In Progress", "Completed"])
            new_diff = st.selectbox("Difficulty", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
            submit_kit = st.form_submit_button("Add Kit")
            
            if submit_kit and new_id and new_name:
                try:
                    c.execute("INSERT INTO Models (Model_ID, Name, Brand, Status, Difficulty) VALUES (?, ?, ?, ?, ?)",
                              (new_id, new_name, new_brand, new_status, new_diff))
                    conn.commit()
                    st.success(f"{new_name} added to inventory!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("A model with that ID already exists!")

    if not models_df.empty:
        st.dataframe(models_df[["Model_ID", "Name", "Brand", "Status", "Difficulty"]], use_container_width=True)

# --- TAB 4: EXPORT DATA (YOUR 20-YEAR PLAN) ---
with tab4:
    st.header("💾 Your Data, Forever")
    st.write("Since your data lives securely in this app's local database, you can extract it to spreadsheet format at any time.")
    
    if not models_df.empty:
        models_csv = models_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Models Inventory (CSV)", models_csv, "metal_earth_models.csv", "text/csv")
        
    if not logs_df.empty:
        logs_csv = logs_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Build Logs (CSV)", logs_csv, "metal_earth_logs.csv", "text/csv")
