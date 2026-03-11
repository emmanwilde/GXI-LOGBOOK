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

# --- PROCESS DATA ---
if not df.empty:
    df['full_dt'] = pd.to_datetime(df['transaction_date_time'])
    df['Just Date'] = df['full_dt'].dt.date
    
    unique_dates = sorted(df['Just Date'].unique())
    min_date = min(unique_dates)
    max_date = max(unique_dates)
    unique_branches = sorted(df['branch_name'].unique())
else:
    unique_dates = []
    min_date = None
    max_date = None
    unique_branches = []

# --- MAIN LAYOUT ---
st.write("---")

if not df.empty:
    # Filters
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        date_range = st.date_input("📅 Date Range", value=(max_date, max_date), min_value=min_date, max_value=max_date)
    with f_col2:
        selected_branch = st.selectbox("🏢 Branch", ["All Branches"] + unique_branches)
    
    # Apply filters
    filtered_df = df.copy()
    if len(date_range) == 2:
        filtered_df = filtered_df[(filtered_df['Just Date'] >= date_range[0]) & (filtered_df['Just Date'] <= date_range[1])]
    elif len(date_range) == 1:
        filtered_df = filtered_df[filtered_df['Just Date'] == date_range[0]]
    if selected_branch != "All Branches":
        filtered_df = filtered_df[filtered_df['branch_name'] == selected_branch]

    filtered_df = filtered_df.sort_values(by=['Just Date', 'branch_name'], ascending=[False, True])

    # Two column layout
    left_col, right_col = st.columns([2, 1])

    with left_col:
        tab1, tab2 = st.tabs(["📋 Logbook View", "🔍 Full Masterlist"])
        with tab1:
            display_cols = ['Just Date', 'transaction_amount', 'branch_name', 'transaction_code', 'channel', 'settlement_amount']
            logbook_view = filtered_df[display_cols].copy()
            logbook_view.columns = ["Date", "Amount", "Branch Name", "Trans. Code", "Channel", "Settlement"]
            if len(logbook_view) > 100:
                st.dataframe(logbook_view.head(100), use_container_width=True, hide_index=True)
                st.caption(f"Showing first 100 of {len(logbook_view)} rows")
            else:
                st.dataframe(logbook_view, use_container_width=True, hide_index=True)
        
        with tab2:
            full_df = filtered_df.drop(columns=['full_dt', 'Just Date'])
            if len(full_df) > 100:
                st.dataframe(full_df.head(100), use_container_width=True, hide_index=True)
                st.caption(f"Showing first 100 of {len(full_df)} rows")
            else:
                st.dataframe(full_df, use_container_width=True, hide_index=True)

    with right_col:
        st.subheader("📊 Summary")
        
        total_transactions = len(filtered_df)
        total_amount = filtered_df['transaction_amount'].sum()
        total_mdr = filtered_df['net_mdr'].sum()
        total_settlement = filtered_df['settlement_amount'].sum()
        
        st.metric("Total Transactions", f"{total_transactions:,}")
        st.metric("Total Amount", f"${total_amount:,.2f}")
        st.metric("Total MDR", f"${total_mdr:,.2f}")
        st.metric("Total Settlement", f"${total_settlement:,.2f}")
        
        st.write("---")
        st.subheader("🏢 By Branch")
        branch_summary = filtered_df.groupby('branch_name').agg({
            'transaction_amount': 'sum',
            'net_mdr': 'sum',
            'settlement_amount': 'sum'
        }).reset_index()
        branch_summary.columns = ["Branch", "Amount", "MDR", "Settlement"]
        st.dataframe(branch_summary, use_container_width=True, hide_index=True)
        
        st.write("---")
        st.subheader("📅 By Date")
        date_summary = filtered_df.groupby('Just Date').agg({
            'transaction_amount': 'sum',
            'net_mdr': 'sum',
            'settlement_amount': 'sum'
        }).reset_index()
        date_summary.columns = ["Date", "Amount", "MDR", "Settlement"]
        st.dataframe(date_summary, use_container_width=True, hide_index=True)
else:
    st.info("Logbook is empty. Upload CSV files to begin.")
