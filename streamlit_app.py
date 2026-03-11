import streamlit as st
import pandas as pd
import gdown
import os
import sqlite3

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
st.set_page_config(page_title="Transaction Manager", layout="wide")
init_db()

st.title("🏦 Transaction Logbook Manager")

# Sidebar for Google Drive
with st.sidebar:
    st.header("Sync Source")
    folder_id = st.text_input("Google Drive Folder ID")
    sync_btn = st.button("🔄 Sync New Files")
    st.divider()
    st.info("The app automatically prevents duplicate entries using the Transaction Code.")

# 3. Processing Logic
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

# 4. Display Logic with Tabs
conn = sqlite3.connect("data.db")
full_df = pd.read_sql_query("SELECT * FROM logs ORDER BY transaction_date_time DESC", conn)
conn.close()

if not full_df.empty:
    # Summary Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Entries", len(full_df))
    m2.metric("Total Amount", f"₱{full_df['transaction_amount'].sum():,.2f}")
    m3.metric("Net Settlement", f"₱{full_df['settlement_amount'].sum():,.2f}")

    # Create the Tabs
    tab1, tab2 = st.tabs(["📋 Simplified Logbook", "🔍 All Transaction Details"])

    with tab1:
        st.subheader("Daily Logbook View")
        # Selecting only the 5 columns you requested
        logbook_cols = [
            'transaction_date_time', 
            'transaction_amount', 
            'branch_name', 
            'transaction_code', 
            'settlement_amount'
        ]
        logbook_df = full_df[logbook_cols].copy()
        
        # Rename for better reading
        logbook_df.columns = ["Date & Time", "Amount", "Branch", "Trans. Code", "Settlement"]
        
        st.dataframe(logbook_df, use_container_width=True)
        
        # Specific download for this view
        csv_log = logbook_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download This Logbook", csv_log, "daily_logbook.csv", "text/csv")

    with tab2:
        st.subheader("Complete Data Masterlist")
        st.dataframe(full_df, use_container_width=True)
        
        # Specific download for all data
        csv_full = full_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Full Masterlist", csv_full, "full_details.csv", "text/csv")
else:
    st.info("No data found. Please sync with your Google Drive folder.")
