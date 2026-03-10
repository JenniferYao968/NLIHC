import requests
import pandas as pd
import os
import time

# ==========================
# CONFIG
# ==========================

API_KEY = "aa506fd9cd8b7234dc9e9a31ee4724a9"

if not API_KEY:
    print("Error: LEGI_API_KEY not set.")
    exit()

STATE = input("Enter state abbreviation (TX, CA, NY, etc.): ").upper()

keyword_input = input("Enter keywords to filter bills (comma separated): ")
KEYWORDS = [k.strip().lower() for k in keyword_input.split(",") if k.strip()]

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
# STEP 2: Scan Master List (TITLE filter)
# ==========================

print("Scanning master bill list...")

master_url = f"https://api.legiscan.com/?key={API_KEY}&op=getMasterList&id={active_session_id}"
master_response = requests.get(master_url)
master_data = master_response.json()

if master_data.get("status") != "OK":
    print("Error fetching bills:", master_data)
    exit()

matching_bill_ids = []

for key, bill in master_data["masterlist"].items():

    if key == "session":
        continue

    title = str(bill.get("title", "")).lower()

    if not KEYWORDS or any(keyword in title for keyword in KEYWORDS):
        matching_bill_ids.append(bill["bill_id"])

print(f"Bills with matching titles: {len(matching_bill_ids)}")

# ==========================
# STEP 3: Deep Check Using getBill
# ==========================

print("Checking bill descriptions with getBill...")

filtered_bills = []

for bill_id in matching_bill_ids:

    bill_url = f"https://api.legiscan.com/?key={API_KEY}&op=getBill&id={bill_id}"
    bill_response = requests.get(bill_url)
    bill_data = bill_response.json()

    if bill_data.get("status") != "OK":
        continue

    bill_info = bill_data["bill"]

    bill_number = bill_info.get("bill_number", "")
    title = bill_info.get("title", "")
    description = str(bill_info.get("description", "")).lower()

    matched_keyword = None

    for keyword in KEYWORDS:
        if keyword in description:
            matched_keyword = keyword
            break

    if matched_keyword:
        record = {
            "state": STATE,
            "bill_number": bill_number,
            "title": title,
            "description": bill_info.get("description", ""),
            "matched_keyword": matched_keyword
        }

        filtered_bills.append(record)

    time.sleep(0.2)  # avoid hitting API rate limits

print(f"Total bills after description filtering: {len(filtered_bills)}")

# ==========================
# STEP 4: Export CSV
# ==========================

df = pd.DataFrame(filtered_bills)

filename = f"{STATE}_filtered_bills.csv"
df.to_csv(filename, index=False)

print(f"Export complete! File saved as {filename}")
