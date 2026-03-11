import streamlit as st
import pandas as pd
import gdown
import os
import sqlite3
from datetime import datetime

# --- CONFIGURATION ---
# Your specific Google Drive Folder ID
FOLDER_ID = "1wj_ogjhv0akqxuvZF4y6FO4dAQLf7fk4"

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

# 2. Sync Function
def sync_data():
    output_dir = "temp_csvs"
    if not os.path.exists(output_dir): 
        os.makedirs(output_dir)
    
    # Download folder contents from hardcoded ID
    gdown.download_folder(id=FOLDER_ID, output=output_dir, quiet=True, remaining_ok=True)
    
    conn = sqlite3.connect("data.db")
    new_rows = 0
    
    # Process files
    for filename in os.listdir(output_dir):
        if filename.endswith(".csv") and "Summary" not in filename:
            try:
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
                    except sqlite3.IntegrityError: 
                        continue # Skip duplicates
            except Exception:
                continue
    
    conn.commit()
    conn.close()
    return new_rows

# 3. Web App UI
st.set_page_config(page_title="Transaction Logbook", layout="wide")
init_db()

st.title("🏦 Transaction Logbook Automator")

# --- TOP CONTROLS ---
# Row for Refresh Button and Info
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🔄 Refresh & Sync Data"):
        with st.spinner("Syncing..."):
            new_added = sync_data()
            st.toast(f"Sync complete! Added {new_added} new entries.")
            st.rerun()

# Load Data for Filtering
conn = sqlite3.connect("data.db")
df = pd.read_sql_query("SELECT * FROM logs", conn)
conn.close()

if not df.empty:
    # Prepare date info
    df['full_dt'] = pd.to_datetime(df['transaction_date_time'])
    df['Just Date'] = df['full_dt'].dt.date
    
    # --- FILTERS ABOVE TABLES ---
    st.write("### Filters")
    f_col1, f_col2 = st.columns(2)
    
    unique_dates = sorted(df['Just Date'].unique(), reverse=True)
    unique_branches = sorted(df['branch_name'].unique())
    
    with f_col1:
        selected_date = st.selectbox("📅 Filter by Date", ["All Dates"] + [d.strftime("%Y-%m-%d") for d in unique_dates])
    with f_col2:
        selected_branch = st.selectbox("🏢 Filter by Branch Name", ["All Branches"] + unique_branches)

    # Apply Filtering
    filtered_df = df.copy()
    if selected_date != "All Dates":
        filtered_df = filtered_df[filtered_df['Just Date'].astype(str) == selected_date]
    if selected_branch != "All Branches":
        filtered_df = filtered_df[filtered_df['branch_name'] == selected_branch]

    # Sort: Date (Newest first) then Branch Name (Alphabetical A-Z)
    filtered_df = filtered_df.sort_values(by=['Just Date', 'branch_name'], ascending=[False, True])

    # --- SUMMARY METRICS ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Selected Entries", len(filtered_df))
    m2.metric("Total Amount", f"₱{filtered_df['transaction_amount'].sum():,.2f}")
    m3.metric("Net Settlement", f"₱{filtered_df['settlement_amount'].sum():,.2f}")

    # --- TABS FOR TABLES ---
    tab1, tab2 = st.tabs(["📋 Logbook View", "🔍 Full Masterlist"])

    with tab1:
        # Display the 5 columns you requested
        display_cols = ['Just Date', 'transaction_amount', 'branch_name', 'transaction_code', 'settlement_amount']
        logbook_view = filtered_df[display_cols].copy()
        logbook_view.columns = ["Date", "Amount", "Branch Name", "Trans. Code", "Settlement"]
        
        st.dataframe(logbook_view, use_container_width=True, hide_index=True)
        
        csv_log = logbook_view.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Logbook CSV", csv_log, f"logbook_{selected_date}.csv", "text/csv")

    with tab2:
        st.dataframe(filtered_df.drop(columns=['full_dt', 'Just Date']), use_container_width=True, hide_index=True)
        
        csv_full = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Full Masterlist", csv_full, "full_masterlist.csv", "text/csv")

else:
    st.info("The database is currently empty. Click the 'Refresh & Sync Data' button above to pull files from Google Drive.")
