import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Metal Earth Workbench", layout="wide")
st.title("⚙️ Metal Earth Workbench")

# --- DATABASE SETUP ---
conn = sqlite3.connect('models_db.db', check_same_thread=False)
c = conn.cursor()

# Updated schema to include your specific Glide fields
c.execute('''CREATE TABLE IF NOT EXISTS Models 
             (Model_ID TEXT PRIMARY KEY, Name TEXT, Brand TEXT, Product_line TEXT, 
              Premium TEXT, Status TEXT, Difficulty INTEGER, Rating INTEGER, Notes TEXT, Last_Worked TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS Build_Logs 
             (Log_ID INTEGER PRIMARY KEY AUTOINCREMENT, Model_ID TEXT, 
              Start_Time TEXT, Duration REAL, Notes TEXT)''')
conn.commit()

# --- OPTIONS FOR SELECTORS ---
PRODUCT_LINES = ["Character", "Architecture", "Car", "Plane", "Other Vehicle", "Animal", "Person", "Marvel", "Star Wars", "Ships", "Watercraft", "Space", "Astronomy", "Musical Instruments", "Tanks", "Armor", "Dinosaurs", "Paleontology", "Bugs", "Insects", "Plants", "Flowers", "Wild West", "Fantasy", "Steampunk", "Harry Potter", "Disney Parks Exclusives", "Lord of the Rings", "Game of Thrones", "Doctor Who", "Transformers", "Batman", "DC Comics"]

# --- NAVIGATION ---
if 'selected_model' not in st.session_state: st.session_state.selected_model = None

# --- MASTER LIST ---
if st.session_state.selected_model is None:
    with st.expander("➕ Add New Model"):
        with st.form("add_model"):
            col1, col2 = st.columns(2)
            new_id = col1.text_input("Model ID")
            new_name = col2.text_input("Name")
            new_brand = col1.selectbox("Brand", ["Metal Earth", "Other"])
            new_line = col2.multiselect("Product Line", PRODUCT_LINES)
            new_premium = col1.radio("Premium Model?", ["Yes", "No"])
            if st.form_submit_button("Create Kit"):
                c.execute("INSERT OR IGNORE INTO Models (Model_ID, Name, Brand, Product_line, Premium, Status, Last_Worked) VALUES (?,?,?,?,?,?,?)", 
                          (new_id, new_name, new_brand, ", ".join(new_line), new_premium, 'Not Started', datetime.now().date()))
                conn.commit()
                st.rerun()

    st.header("Inventory")
    models = pd.read_sql_query("SELECT * FROM Models ORDER BY Last_Worked DESC", conn)
    for _, row in models.iterrows():
        if st.button(f"{row['Name']} ({row.get('Status', 'Not Started')})", key=row['Model_ID']):
            st.session_state.selected_model = row['Model_ID']
            st.rerun()

# --- DETAIL VIEW (THE WORKBENCH) ---
else:
    model_id = st.session_state.selected_model
    df = pd.read_sql_query(f"SELECT * FROM Models WHERE Model_ID='{model_id}'", conn)
    model = df.iloc[0]
    
    if st.button("⬅️ Back"):
        st.session_state.selected_model = None
        st.rerun()
        
    st.header(f"Workbench: {model['Name']}")
    
    # Comprehensive Edit Form
    with st.expander("✏️ Edit Model Details"):
        with st.form("edit_model"):
            c1, c2 = st.columns(2)
            e_brand = c1.selectbox("Brand", ["Metal Earth", "Other"], index=0 if model.get('Brand')=="Metal Earth" else 1)
            e_line = c2.multiselect("Product Line", PRODUCT_LINES, default=model.get('Product_line', '').split(", ") if model.get('Product_line') else [])
            e_prem = c1.radio("Premium?", ["Yes", "No"], index=0 if model.get('Premium')=="Yes" else 1)
            e_stat = c2.selectbox("Status", ["Complete", "Not Started", "In Progress"], index=["Complete", "Not Started", "In Progress"].index(model.get('Status', 'Not Started')))
            e_diff = c1.slider("Difficulty", 1, 10, int(model.get('Difficulty') or 1))
            e_rate = c2.slider("Rating", 1, 10, int(model.get('Rating') or 1))
            e_note = st.text_area("Notes", value=str(model.get('Notes', '')))
            
            if st.form_submit_button("Save Updates"):
                c.execute("UPDATE Models SET Brand=?, Product_line=?, Premium=?, Status=?, Difficulty=?, Rating=?, Notes=? WHERE Model_ID=?", 
                          (e_brand, ", ".join(e_line), e_prem, e_stat, e_diff, e_rate, e_note, model_id))
                conn.commit()
                st.rerun()

    # Timer & History
    logs = pd.read_sql_query(f"SELECT * FROM Build_Logs WHERE Model_ID='{model_id}'", conn)
    st.metric("Total Time (Minutes)", round(logs['Duration'].sum() / 60, 1) if not logs.empty else 0)
    # ... (Rest of Timer logic remains the same)
