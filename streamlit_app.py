import streamlit as st
import pandas as pd
import imaplib
import email
import io
import sqlite3

# 1. Setup Database
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id TEXT PRIMARY KEY, date TEXT, branch TEXT, 
                  channel TEXT, amount REAL, settlement REAL)''')
    conn.commit()
    conn.close()

# 2. Gmail Fetching
def fetch_data(email_user, email_pass, target_sender):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_pass)
        mail.select("inbox")
        _, data = mail.search(None, f'FROM "{target_sender}"')
        
        ids = data[0].split()
        new_rows = 0
        conn = sqlite3.connect("data.db")
        
        # Check last 10 emails
        for i in ids[-10:]:
            _, msg_data = mail.fetch(i, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            for part in msg.walk():
                fname = part.get_filename()
                if fname and fname.endswith('.csv') and "Summary" not in fname:
                    df = pd.read_csv(io.BytesIO(part.get_payload(decode=True)))
                    for _, row in df.iterrows():
                        try:
                            conn.execute("INSERT INTO logs VALUES (?,?,?,?,?,?)", 
                                       (str(row['Transaction Code']), str(row['Transaction Date Time']), 
                                        row['Branch Name'], row['Channel'], 
                                        row['Transaction Amount'], row['Settlement Amount']))
                            new_rows += 1
                        except: continue # Skip duplicates
        conn.commit()
        conn.close()
        mail.logout()
        return f"Done! Added {new_rows} new records."
    except Exception as e:
        return f"Error: {str(e)}"

# 3. Web Interface
st.set_page_config(page_title="My Company Logbook", layout="wide")
init_db()

st.title("📊 Transaction Logbook")

with st.sidebar:
    st.header("Sync from Gmail")
    user = st.text_input("Your Gmail")
    pw = st.text_input("App Password", type="password")
    sender = st.text_input("Sender Email")
    if st.button("Start Sync"):
        result = fetch_data(user, pw, sender)
        st.write(result)

# Display Data
conn = sqlite3.connect("data.db")
stored_df = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC", conn)
conn.close()

if not stored_df.empty:
    st.write(f"Showing {len(stored_df)} total records")
    st.dataframe(stored_df, use_container_width=True)
else:
    st.info("Logbook is empty. Use the sidebar to sync data from Gmail.")
