import streamlit as st
import requests
import pandas as pd

# ==========================
# CONFIG
# ==========================

API_KEY = "aa506fd9cd8b7234dc9e9a31ee4724a9"

st.title("Legislative Bill Search")

# Initialize selected_labels
selected_labels = []

# -------------------------
# Session State
# -------------------------

if "bills" not in st.session_state:
    st.session_state.bills = []

# -------------------------
# Cached API Functions
# -------------------------

@st.cache_data
def get_active_session(state):
    """Return the active regular session ID and name for a state."""
    url = f"https://api.legiscan.com/?key={API_KEY}&op=getSessionList&state={state}"
    data = requests.get(url).json()
    
    for session in data.get("sessions", []):
        if session.get("sine_die") == 0 and session.get("special") == 0:
            return session["session_id"], session["session_name"]
    
    return None, None


@st.cache_data
def get_bills(session_id):
    """Return all bills for a given session."""
    url = f"https://api.legiscan.com/?key={API_KEY}&op=getMasterList&id={session_id}"
    data = requests.get(url).json()
    
    bills = []
    for key, bill in data.get("masterlist", {}).items():
        if key == "session":
            continue
        bills.append(bill)
    return bills


@st.cache_data
def get_bill_details(bill_id):
    """Return full details of a bill."""
    url = f"https://api.legiscan.com/?key={API_KEY}&op=getBill&id={bill_id}"
    data = requests.get(url).json()
    return data["bill"]

# ==========================
# Search Inputs
# ==========================

state = st.text_input("State abbreviation (NY, CA, TX)").upper()
keyword_input = st.text_input("Keywords (comma separated)")

if st.button("Search Bills"):
    if not state:
        st.error("Please enter a state abbreviation.")
        st.stop()
    
    keywords = [k.strip().lower() for k in keyword_input.split(",") if k.strip()]

    session_id, session_name = get_active_session(state)
    if not session_id:
        st.error("No active regular session found.")
        st.stop()
    
    st.success(f"Active session: {session_name}")

    bills = get_bills(session_id)

    # Filter by keywords if provided
    filtered = []
    for bill in bills:
        title = str(bill.get("title", "")).lower()
        description = str(bill.get("description", "")).lower()
        searchable = title + " " + description
        if not keywords or any(k in searchable for k in keywords):
            filtered.append(bill)
    
    st.session_state.bills = filtered

# ==========================
# Display Bills & Multiselect
# ==========================

if st.session_state.bills:
    st.write(f"### {len(st.session_state.bills)} Bills Found")

    # Map display label -> bill_id
    bill_options = {
        f"{bill.get('number','Unknown')} — {bill.get('title','No title')}": bill["bill_id"]
        for bill in st.session_state.bills
    }

    selected_labels = st.multiselect(
        "Select bills to get detailed information:",
        options=list(bill_options.keys())
    )

# ==========================
# Download Selected Bills
# ==========================
if selected_labels:
    if st.button("Download Selected Bill Information"):

        rows = []

        for label in selected_labels:

            bill_id = bill_options[label]

            bill_info = get_bill_details(bill_id)

            rows.append({
                "bill_id": bill_info.get("bill_id"),
                "bill_number": bill_info.get("bill_number"),
                "title": bill_info.get("title"),
                "description": bill_info.get("description"),
                "status": bill_info.get("status"),
                "status_date": bill_info.get("status_date"),
                "introduced_date": bill_info.get("introduced_date"),
                "last_action": bill_info.get("last_action"),
                "last_action_date": bill_info.get("last_action_date"),
                "url": bill_info.get("url"),
                "state": bill_info.get("state")
            })

        df = pd.DataFrame(rows)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Bill Information CSV",
            data=csv,
            file_name="selected_bill_details.csv",
            mime="text/csv"
        )

#if selected_labels:
    #if st.button("Download Selected Bill Information"):
        #all_bill_data = []

        #for label in selected_labels:
            #bill_id = bill_options[label]
            #bill_info = get_bill_details(bill_id)
            #df = pd.json_normalize(bill_info)
            #all_bill_data.append(df)

        #final_df = pd.concat(all_bill_data, ignore_index=True)
        #csv = final_df.to_csv(index=False).encode("utf-8")

        #st.download_button(
            #label="Download CSV",
            #data=csv,
            #file_name="selected_bill_details.csv",
            #mime="text/csv"
        #)
