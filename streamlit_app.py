import streamlit as st
import pandas as pd
import imaplib
import email
import io
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
DB_NAME = "logbook_records.db"

def init_db():
    """Creates the database table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # We use 'Transaction Code' as a UNIQUE key to prevent duplicates
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (trans_code TEXT PRIMARY KEY, 
                  date_time TEXT, 
                  branch TEXT, 
                  channel TEXT, 
                  amount REAL, 
                  net_mdr REAL, 
                  settlement REAL)''')
    conn.commit()
    conn.close()

def save_to_db(df):
    """Saves new records to the database, skipping duplicates."""
    conn = sqlite3.connect(DB_NAME)
    new_records = 0
    for _, row in df.iterrows():
        try:
            conn.execute("""INSERT INTO transactions VALUES (?,?,?,?,?,?,?)""", 
                         (str(row['Transaction Code']), 
                          str(row['Transaction Date Time']), 
                          row['Branch Name'], 
                          row['Channel'], 
                          row['Transaction Amount'], 
                          row['Net MDR'], 
                          row['Settlement Amount']))
            new_records += 1
        except sqlite3.IntegrityError:
            # This happens if 'Transaction Code' already exists in the DB
            continue 
    conn.commit()
    conn.close()
    return new_records

def load_from_db():
    """Reads all saved records from the database."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date_time DESC", conn)
    conn.close()
    return df

# --- GMAIL FETCHING LOGIC ---
def fetch_emails(user_email, password, sender_email):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user_email, password)
        mail.select("inbox")
        # Search for emails from the last 7 days to keep it fast
        status, messages = mail.search(None, f'FROM "{sender_email}"')
        
        if status != "OK" or not messages[0]:
            return None, "No emails found."

        all_dfs = []
        mail_ids = messages[0].split()
        for i in mail_ids[-15:]: # Check last 15 emails
            res, msg_data = mail.fetch(i, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    for part in msg.walk():
                        filename = part.get_filename()
                        if filename and filename.endswith('.csv') and "Summary" not in filename:
                            content = part.get_payload(decode=True)
                            all_dfs.append(pd.read_csv(io.BytesIO(content)))
        mail.logout()
        return pd.concat(all_dfs, ignore_index=True) if all_dfs else None, "Success"
    except Exception as e:
        return None, str(e)

# --- STREAMLIT UI ---
st.set_page_config(page_title="Company Logbook App", layout="wide")
init_db()

st.title("🏦 Company Transaction Logbook")
st.info("This app pulls CSVs from Gmail and saves them to a permanent database. Duplicates are automatically blocked.")

# Sidebar for Settings
with st.sidebar:
    st.header("Sync Settings")
    u_email = st.text_input("Gmail Address")
    u_pass = st.text_input("App Password", type="password")
    s_email = st.text_input("Sender Email")
    sync_btn = st.button("🔄 Sync New Emails")

# Main Logic
if sync_btn:
    raw_df, msg = fetch_emails(u_email, u_pass, s_email)
    if raw_df is not None:
        added = save_to_db(raw_df)
        st.success(f"Sync Complete! Added {added} new unique transactions.")
    else:
        st.warning(f"Sync failed or no new data: {msg}")

# Always show the Database content
st.subheader("Your Digital Logbook (Saved Data)")
logbook_data = load_from_db()

if not logbook_data.empty:
    st.dataframe(logbook_data, use_container_width=True)
    # Total Calculation
    st.metric("Total Settlement Value", f"₱{logbook_data['settlement'].sum():,.2f}")
else:
    st.write("No data saved yet. Fill in settings and click Sync.")
