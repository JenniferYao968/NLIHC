import requests
import pandas as pd
import os

# Pulls all bills from a state's active legislative session using the LegiScan API and exports to CSV. 
# Does not filter by keywords

# ==========================
# CONFIG
# ==========================

# Make this a separate config file or environment variable in production for security
API_KEY = "aa506fd9cd8b7234dc9e9a31ee4724a9"
STATE = "TX"  # Change to any state (CA, NY, FL, etc.)

if not API_KEY:
    print("Error: LEGI_API_KEY not set.")
    exit()

# ==========================
# STEP 1: Get Active Session
# ==========================

print("Fetching session list...")

session_url = f"https://api.legiscan.com/?key={API_KEY}&op=getSessionList&state={STATE}"
session_response = requests.get(session_url)
session_data = session_response.json()

if session_data.get("status") != "OK":
    print("Error fetching session list:", session_data)
    exit()

active_session_id = None

for session in session_data["sessions"]:
    if session["sine_die"] == 0 and session["special"] == 0:
        active_session_id = session["session_id"]
        print("Active regular session found:", session["session_name"])
        break

if not active_session_id:
    print("No active regular session found.")
    exit()

# ==========================
# STEP 2: Get Bills
# ==========================

print("Fetching bills...")

master_url = f"https://api.legiscan.com/?key={API_KEY}&op=getMasterList&id={active_session_id}"
master_response = requests.get(master_url)
master_data = master_response.json()

if master_data.get("status") != "OK":
    print("Error fetching bills:", master_data)
    exit()

bills = []

for key, bill in master_data["masterlist"].items():
    if key != "session":
        bills.append(bill)

print(f"Total bills retrieved: {len(bills)}")

# ==========================
# STEP 3: Export CSV
# ==========================

df = pd.DataFrame(bills)

filename = f"{STATE}_bills.csv"
df.to_csv(filename, index=False)

print(f"Export complete! File saved as {filename}")
