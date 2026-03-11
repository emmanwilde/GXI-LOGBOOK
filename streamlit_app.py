import streamlit as st
import pandas as pd
import gdown
import os
import sqlite3
from datetime import datetime

# 1. Database Setup
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (branch_name TEXT, 
                  branch_display_name TEXT, 
                  branch_code TEXT, 
                  mqr_code TEXT, 
                  transaction_code TEXT PRIMARY KEY, 
                  transaction_date_time TEXT, 
                  channel TEXT, 
                  type TEXT, 
                  transaction_amount REAL, 
                  net_mdr REAL, 
                  settlement_amount REAL, 
                  remark TEXT)''')
    conn.commit()
    conn.close()

# 2. Web Interface Configuration
st.set_page_config(page_title="Filtered Logbook", layout="wide")
init_db()

st.title("🏦 Smart Transaction Logbook")

# Sidebar for Syncing and Filtering
with st.sidebar:
    st.header("1. Sync Data")
    folder_id = st.text_input("Google Drive Folder ID")
    sync_btn = st.button("🔄 Sync New Files")
    
    st.divider()
    
    st.header("2. Filter Logbook")
    # We will populate these filters after loading the data
    st.info("Use the filters below to clean up your Logbook View.")

# 3. Processing Logic (Google Drive Sync)
if sync_btn and folder_id:
    with st.spinner("Downloading and processing..."):
        try:
            output_dir = "temp_csvs"
            if not os.path.exists(output_dir): os.makedirs(output_dir)
            gdown.download_folder(id=folder_id, output=output_dir, quiet=True, remaining_ok=True)
            
            conn = sqlite3.connect("data.db")
            new_rows = 0
            for filename in os.listdir(output_dir):
                if filename.endswith(".csv") and "Summary" not in filename:
                    df = pd.read_csv(os.path.join(output_dir, filename))
                    for _, row in df.iterrows():
                        try:
                            conn.execute("""INSERT INTO logs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", 
                                       (str(row.get('Branch Name', '')), str(row.get('Branch Display Name', '')),
                                        str(row.get('Branch Code', '')), str(row.get('MQR Code', '')),
                                        str(row.get('Transaction Code', '')), str(row.get('Transaction Date Time', '')),
                                        str(row.get('Channel', '')), str(row.get('Type', '')),
                                        float(row.get('Transaction Amount', 0)), float(row.get('Net MDR', 0)),
                                        float(row.get('Settlement Amount', 0)), str(row.get('Remark', ''))))
                            new_rows += 1
                        except sqlite3.IntegrityError: continue 
            conn.commit()
            conn.close()
            st.success(f"Sync complete! Added {new_rows} new transactions.")
        except Exception as e:
            st.error(f"Error: {e}")

# 4. Data Loading & Filtering
conn = sqlite3.connect("data.db")
df = pd.read_sql_query("SELECT * FROM logs", conn)
conn.close()

if not df.empty:
    # --- DATA PREPARATION ---
    # Convert 'transaction_date_time' to a proper date object
    df['full_dt'] = pd.to_datetime(df['transaction_date_time'])
    df['Just Date'] = df['full_dt'].dt.date  # Creates the YYYY-MM-DD format
    
    # --- SIDEBAR FILTERS ---
    unique_dates = sorted(df['Just Date'].unique(), reverse=True)
    unique_branches = sorted(df['branch_name'].unique())
    
    with st.sidebar:
        selected_date = st.selectbox("Select Date", ["All Dates"] + [d.strftime("%Y-%m-%d") for d in unique_dates])
        selected_branch = st.selectbox("Select Branch", ["All Branches"] + unique_branches)

    # Apply Filters
    filtered_df = df.copy()
    if selected_date != "All Dates":
        filtered_df = filtered_df[filtered_df['Just Date'].astype(str) == selected_date]
    if selected_branch != "All Branches":
        filtered_df = filtered_df[filtered_df['branch_name'] == selected_branch]

    # --- SORTING ---
    # Sort by Date (Descending) and then Branch Name (Alphabetical A-Z)
    filtered_df = filtered_df.sort_values(by=['Just Date', 'branch_name'], ascending=[False, True])

    # --- TABS ---
    tab1, tab2 = st.tabs(["📋 Filtered Logbook", "🔍 Full Masterlist"])

    with tab1:
        st.subheader(f"Logbook: {selected_date} | {selected_branch}")
        
        # Display requested columns
        display_cols = ['Just Date', 'transaction_amount', 'branch_name', 'transaction_code', 'settlement_amount']
        logbook_view = filtered_df[display_cols].copy()
        
        # Rename for the physical logbook
        logbook_view.columns = ["Date", "Amount", "Branch Name", "Trans. Code", "Settlement"]
        
        st.dataframe(logbook_view, use_container_width=True, hide_index=True)
        
        # Metrics for the filtered view
        c1, c2 = st.columns(2)
        c1.metric("Transaction Count", len(logbook_view))
        c2.metric("Total Settlement", f"₱{logbook_view['Settlement'].sum():,.2f}")

    with tab2:
        st.subheader("Raw Data (All Columns)")
        st.dataframe(filtered_df.drop(columns=['full_dt', 'Just Date']), use_container_width=True)

else:
    st.info("Database is empty. Please enter your Google Drive Folder ID and click Sync.")
