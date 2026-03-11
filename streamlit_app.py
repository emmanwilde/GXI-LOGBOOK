import streamlit as st
import pandas as pd
import sqlite3
import io

# Password protection
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.set_page_config(page_title="Login - Transaction Logbook", layout="centered")
    st.title("🔐 Login Required")
    password = st.text_input("Enter Password", type="password")
    if password == "PA$$WORD":
        st.session_state.authenticated = True
        st.rerun()
    elif password:
        st.error("Incorrect password")
    st.stop()

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

# 2. Web App UI
st.set_page_config(page_title="Transaction Logbook", layout="wide")
init_db()

st.title("🏦 Transaction Logbook Manager")
st.write("Upload your daily CSV files below to update the logbook. Duplicates are automatically removed.")

# --- FILE UPLOADER ---
uploaded_files = st.file_uploader("Drag and drop your CSV files here", type="csv", accept_multiple_files=True)

if uploaded_files:
    conn = sqlite3.connect("data.db")
    new_rows = 0
    
    for uploaded_file in uploaded_files:
        if "Summary" not in uploaded_file.name:
            df = pd.read_csv(uploaded_file)
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
                    continue 
    conn.commit()
    conn.close()
    if new_rows > 0:
        st.success(f"Done! Added {new_rows} new unique transactions.")
        st.rerun()

# --- LOAD DATA ---
conn = sqlite3.connect("data.db")
df = pd.read_sql_query("SELECT * FROM logs", conn)
conn.close()

if not df.empty:
    df['full_dt'] = pd.to_datetime(df['transaction_date_time'])
    df['Just Date'] = df['full_dt'].dt.date
    
    # Filters
    st.write("---")
    f_col1, f_col2 = st.columns(2)
    unique_dates = sorted(df['Just Date'].unique(), reverse=True)
    unique_branches = sorted(df['branch_name'].unique())
    
    with f_col1:
        selected_date = st.selectbox("📅 Filter by Date", ["All Dates"] + [d.strftime("%Y-%m-%d") for d in unique_dates])
    with f_col2:
        selected_branch = st.selectbox("🏢 Filter by Branch Name", ["All Branches"] + unique_branches)

    filtered_df = df.copy()
    if selected_date != "All Dates":
        filtered_df = filtered_df[filtered_df['Just Date'].astype(str) == selected_date]
    if selected_branch != "All Branches":
        filtered_df = filtered_df[filtered_df['branch_name'] == selected_branch]

    filtered_df = filtered_df.sort_values(by=['Just Date', 'branch_name'], ascending=[False, True])

    # Display
    tab1, tab2 = st.tabs(["📋 Logbook View", "🔍 Full Masterlist"])
    with tab1:
        display_cols = ['Just Date', 'transaction_amount', 'branch_name', 'transaction_code', 'channel', 'settlement_amount']
        logbook_view = filtered_df[display_cols].copy()
        logbook_view.columns = ["Date", "Amount", "Branch Name", "Trans. Code", "Channel", "Settlement"]
        st.dataframe(logbook_view, use_container_width=True, hide_index=True)
    
    with tab2:
        st.dataframe(filtered_df.drop(columns=['full_dt', 'Just Date']), use_container_width=True, hide_index=True)
else:
    st.info("Logbook is empty. Upload CSV files to begin.")
