import streamlit as st
import pandas as pd
import json
import os
from google.cloud import firestore
import google.oauth2.service_account

def get_firestore_client():
    if not hasattr(st, 'secrets') or 'firebase' not in st.secrets:
        st.error("⚠️ Firebase credentials not configured in Streamlit secrets.")
        st.info("Go to App settings > Secrets and add your Firebase service account JSON.")
        st.stop()
    
    try:
        creds_dict = dict(st.secrets['firebase'])
        credentials = google.oauth2.service_account.Credentials.from_service_account_info(creds_dict)
        return firestore.Client(credentials=credentials)
    except Exception as e:
        st.error(f"Failed to initialize Firestore: {e}")
        st.stop()

FIRESTORE_HEADERS = [
    'Branch Name',
    'Branch Display Name',
    'Branch Code',
    'MQR Code',
    'Transaction Code',
    'Transaction Date Time',
    'Channel',
    'Type',
    'Transaction Amount',
    'Net MDR',
    'Settlement Amount',
    'Remark'
]

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.set_page_config(page_title="Login - Transaction Logbook", layout="centered")
    st.title("🔐 Login Required")
    password = st.text_input("Enter Password", type="password")
    if password == "gwapako10":
        st.session_state.authenticated = True
        st.rerun()
    elif password:
        st.error("Incorrect password")
    st.stop()

@st.cache_data(ttl=60)
def load_firestore_data():
    db = get_firestore_client()
    docs = db.collection('transactions').get()
    data = []
    for doc in docs:
        doc_data = doc.to_dict()
        row = {}
        for header in FIRESTORE_HEADERS:
            for key in doc_data.keys():
                if key.lower() == header.lower() or key == header:
                    row[header] = doc_data[key]
                    break
            else:
                row[header] = ''
        data.append(row)
    return pd.DataFrame(data)

st.set_page_config(page_title="Transaction Logbook", layout="wide")

st.title("🏦 Transaction Logbook Manager")
st.write("Data loaded from Firestore database.")

df = load_firestore_data()

if not df.empty:
    df['full_dt'] = pd.to_datetime(df['Transaction Date Time'], errors='coerce')
    df['Just Date'] = df['full_dt'].dt.date
    
    unique_dates = sorted(df['Just Date'].dropna().unique())
    min_date = min(unique_dates) if unique_dates else None
    max_date = max(unique_dates) if unique_dates else None
    unique_branches = sorted(df['Branch Name'].dropna().unique())
else:
    unique_dates = []
    min_date = None
    max_date = None
    unique_branches = []

st.write("---")

if not df.empty:
    left_col, right_col = st.columns([2, 1])

    with left_col:
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            date_range = st.date_input("📅 Date Range", value=(max_date, max_date), min_value=min_date, max_value=max_date)
        with f_col2:
            selected_branch = st.selectbox("🏢 Branch", ["All Branches"] + unique_branches)
        
        filtered_df = df.copy()
        if len(date_range) == 2:
            filtered_df = filtered_df[(filtered_df['Just Date'] >= date_range[0]) & (filtered_df['Just Date'] <= date_range[1])]
        elif len(date_range) == 1:
            filtered_df = filtered_df[filtered_df['Just Date'] == date_range[0]]
        if selected_branch != "All Branches":
            filtered_df = filtered_df[filtered_df['Branch Name'] == selected_branch]

        filtered_df = filtered_df.sort_values(by=['Just Date', 'Branch Name'], ascending=[False, True])

        tab1, tab2 = st.tabs(["📋 Logbook View", "🔍 Full Masterlist"])
        with tab1:
            display_cols = ['Just Date', 'Transaction Amount', 'Branch Name', 'Transaction Code', 'Channel', 'Settlement Amount']
            logbook_view = filtered_df[display_cols].copy()
            logbook_view.columns = ["Date", "Amount", "Branch Name", "Trans. Code", "Channel", "Settlement"]
            max_rows = min(len(logbook_view), 100)
            row_height = 35
            height = max_rows * row_height + 40
            st.dataframe(logbook_view.head(100), use_container_width=True, hide_index=True, height=height)
        
        with tab2:
            full_df = filtered_df.drop(columns=['full_dt', 'Just Date'], errors='ignore')
            max_rows = min(len(full_df), 100)
            row_height = 35
            height = max_rows * row_height + 40
            st.dataframe(full_df.head(100), use_container_width=True, hide_index=True, height=height)

    with right_col:
        st.markdown("### 📊 Summary")
        
        total_transactions = 0
        total_amount = 0.0
        total_mdr = 0.0
        total_settlement = 0.0
        
        if 'Transaction Amount' in filtered_df.columns:
            total_transactions = int(len(filtered_df))
            total_amount = float(filtered_df['Transaction Amount'].sum())
        if 'Net MDR' in filtered_df.columns:
            total_mdr = float(filtered_df['Net MDR'].sum())
        if 'Settlement Amount' in filtered_df.columns:
            total_settlement = float(filtered_df['Settlement Amount'].sum())
        
        st.markdown("""
        <div style="text-align: center;">
            <div style="font-size: 14px; color: gray;">Total Transactions</div>
            <div style="font-size: 24px; font-weight: bold;">""" + str(total_transactions) + """</div>
            <div style="font-size: 14px; color: gray; margin-top: 10px;">Total Amount</div>
            <div style="font-size: 24px; font-weight: bold;">₱""" + "{:,.2f}".format(total_amount) + """</div>
            <div style="font-size: 14px; color: gray; margin-top: 10px;">Total MDR</div>
            <div style="font-size: 24px; font-weight: bold;">₱""" + "{:,.2f}".format(total_mdr) + """</div>
            <div style="font-size: 14px; color: gray; margin-top: 10px;">Total Settlement</div>
            <div style="font-size: 24px; font-weight: bold;">₱""" + "{:,.2f}".format(total_settlement) + """</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("---")
        st.subheader("🏢 By Branch")
        branch_summary = filtered_df.groupby('Branch Name').agg({
            'Transaction Amount': 'sum',
            'Net MDR': 'sum',
            'Settlement Amount': 'sum'
        }).reset_index()
        branch_summary.columns = ["Branch", "Amount", "MDR", "Settlement"]
        branch_summary["Amount"] = branch_summary["Amount"].apply(lambda x: f"₱{x:,.2f}")
        branch_summary["MDR"] = branch_summary["MDR"].apply(lambda x: f"₱{x:,.2f}")
        branch_summary["Settlement"] = branch_summary["Settlement"].apply(lambda x: f"₱{x:,.2f}")
        st.dataframe(branch_summary, use_container_width=True, hide_index=True)
        
        st.write("---")
        st.subheader("📅 By Date")
        date_summary = filtered_df.groupby('Just Date').agg({
            'Transaction Amount': 'sum',
            'Net MDR': 'sum',
            'Settlement Amount': 'sum'
        }).reset_index()
        date_summary.columns = ["Date", "Amount", "MDR", "Settlement"]
        date_summary["Amount"] = date_summary["Amount"].apply(lambda x: f"₱{x:,.2f}")
        date_summary["MDR"] = date_summary["MDR"].apply(lambda x: f"₱{x:,.2f}")
        date_summary["Settlement"] = date_summary["Settlement"].apply(lambda x: f"₱{x:,.2f}")
        st.dataframe(date_summary, use_container_width=True, hide_index=True)
else:
    st.info("No data found in Firestore.")