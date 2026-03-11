import streamlit as st
import pandas as pd
import gdown
import os
import sqlite3

# 1. Database Setup (Added all your requested columns)
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    # We create the table with all columns. Transaction Code is the "ID" to prevent duplicates.
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
st.set_page_config(page_title="Full Transaction Logbook", layout="wide")
init_db()

st.title("📋 Full Transaction Logbook")
st.write("This app syncs with Google Drive and displays all transaction details.")

# Sidebar for Google Drive Folder ID
with st.sidebar:
    st.header("Settings")
    folder_id = st.text_input("Google Drive Folder ID")
    sync_btn = st.button("🔄 Sync New Files")

# 3. Processing Logic
if sync_btn and folder_id:
    with st.spinner("Downloading and processing files..."):
        try:
            output_dir = "temp_csvs"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Download folder contents
            gdown.download_folder(id=folder_id, output=output_dir, quiet=True, remaining_ok=True)
            
            conn = sqlite3.connect("data.db")
            new_rows = 0
            
            for filename in os.listdir(output_dir):
                # We only want the detail files, not the "Summary" files
                if filename.endswith(".csv") and "Summary" not in filename:
                    path = os.path.join(output_dir, filename)
                    df = pd.read_csv(path)
                    
                    for _, row in df.iterrows():
                        try:
                            # Inserting every column into the database
                            conn.execute("""INSERT INTO logs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", 
                                       (str(row.get('Branch Name', '')),
                                        str(row.get('Branch Display Name', '')),
                                        str(row.get('Branch Code', '')),
                                        str(row.get('MQR Code', '')),
                                        str(row.get('Transaction Code', '')),
                                        str(row.get('Transaction Date Time', '')),
                                        str(row.get('Channel', '')),
                                        str(row.get('Type', '')),
                                        float(row.get('Transaction Amount', 0)),
                                        float(row.get('Net MDR', 0)),
                                        float(row.get('Settlement Amount', 0)),
                                        str(row.get('Remark', ''))))
                            new_rows += 1
                        except sqlite3.IntegrityError:
                            continue # This skips rows that are already in the database
            
            conn.commit()
            conn.close()
            st.success(f"Sync complete! Added {new_rows} new transactions.")
            
        except Exception as e:
            st.error(f"Error: {e}")

# 4. Display the Data
st.subheader("Stored Transactions")
conn = sqlite3.connect("data.db")
# This pulls everything from the database
full_df = pd.read_sql_query("SELECT * FROM logs ORDER BY transaction_date_time DESC", conn)
conn.close()

if not full_df.empty:
    # Optional: Format the numbers to look like currency
    st.dataframe(full_df, use_container_width=True)
    
    # Summary Metrics at the top
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Transactions", len(full_df))
    with col2:
        total_settled = full_df['settlement_amount'].sum()
        st.metric("Total Settlement", f"₱{total_settled:,.2f}")

    # Export button
    csv = full_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download All Data as CSV", csv, "full_logbook.csv", "text/csv")
else:
    st.info("No data in the database yet. Enter your Folder ID and click Sync.")
