import streamlit as st
import pandas as pd
import gdown
import os
import sqlite3

# 1. Database Setup
def init_db():
    conn = sqlite3.connect("logbook.db")
    conn.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id TEXT PRIMARY KEY, date TEXT, branch TEXT, 
                  channel TEXT, amount REAL, settlement REAL)''')
    conn.close()

# 2. Main App UI
st.set_page_config(page_title="G-Drive Logbook", layout="wide")
init_db()

st.title("📂 Google Drive Logbook Automator")
st.write("This app reads CSVs from your shared Google Drive folder and saves them here.")

# Sidebar for the Folder ID
with st.sidebar:
    folder_id = st.text_input("Enter Google Drive Folder ID", help="The long string of letters at the end of your folder link.")
    sync_btn = st.button("Sync Files Now")

if sync_btn and folder_id:
    with st.spinner("Accessing Google Drive..."):
        # This downloads the files from the folder
        try:
            # We use gdown to list and download files
            output_dir = "temp_csvs"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Download all files from folder
            gdown.download_folder(id=folder_id, output=output_dir, quiet=True, remaining_ok=True)
            
            # Process the files
            conn = sqlite3.connect("logbook.db")
            new_count = 0
            
            for filename in os.listdir(output_dir):
                if filename.endswith(".csv") and "Summary" not in filename:
                    path = os.path.join(output_dir, filename)
                    df = pd.read_csv(path)
                    
                    for _, row in df.iterrows():
                        try:
                            conn.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?)", 
                                       (str(row['Transaction Code']), str(row['Transaction Date Time']), 
                                        row['Branch Name'], row['Channel'], 
                                        row['Transaction Amount'], row['Settlement Amount']))
                            new_count += 1
                        except:
                            continue # Skip if already in database
            
            conn.commit()
            conn.close()
            st.success(f"Success! Processed files and found {new_count} new transactions.")
            
        except Exception as e:
            st.error(f"Make sure the folder is 'Shared with anyone with the link'. Error: {e}")

# 3. Show the Logbook
st.subheader("Your Physical Logbook View")
conn = sqlite3.connect("logbook.db")
final_df = pd.read_sql_query("SELECT date, branch, channel, amount, settlement FROM transactions ORDER BY date DESC", conn)
conn.close()

if not final_df.empty:
    # Rename columns to match your physical logbook exactly
    final_df.columns = ["Date/Time", "Branch", "Payment Method", "Total Amount", "Net Settlement"]
    st.dataframe(final_df, use_container_width=True)
    
    # Download for your records
    csv = final_df.to_csv(index=False).encode('utf-8')
    st.download_button("Export to Excel/CSV", csv, "my_logbook.csv", "text/csv")
else:
    st.info("No data yet. Enter your Folder ID in the sidebar and click Sync.")
