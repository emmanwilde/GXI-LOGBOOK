import streamlit as st
import pandas as pd
import imaplib
import email
import io
import sqlite3

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("logbook.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (trans_code TEXT PRIMARY KEY, date_time TEXT, branch TEXT, 
                  channel TEXT, amount REAL, net_mdr REAL, settlement REAL)''')
    conn.commit()
    conn.close()

# --- APP UI ---
st.title("📋 My Logbook App")

try:
    init_db()
    st.success("Database Ready!")
except Exception as e:
    st.error(f"Database Error: {e}")

st.write("If you see this, the app is running! Use the sidebar to sync.")

# --- SIDEBAR ---
with st.sidebar:
    u_email = st.text_input("Gmail Address")
    u_pass = st.text_input("App Password", type="password")
    if st.button("Sync Now"):
        st.write("Attempting to sync...")
        # (Gmail logic goes here)
