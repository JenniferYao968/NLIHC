import requests
import pandas as pd
import os

# Builds upon the original jen_pull_bills.py by adding keyword filtering functionality.

# ==========================
# CONFIG
# ==========================

API_KEY = "aa506fd9cd8b7234dc9e9a31ee4724a9"  # Add your LegiScan API key here

if not API_KEY:
    print("Error: LEGI_API_KEY not set.")
    exit()

# Ask user for state
STATE = input("Enter state abbreviation (TX, CA, NY, etc.): ").upper()

# Ask user for keywords
keyword_input = input("Enter keywords to filter bills (comma separated): ")

# Convert keywords into a list and make lowercase
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

    if key == "session":
        continue

    # Combine searchable fields
    title = str(bill.get("title", "")).lower()
    description = str(bill.get("description", "")).lower()

    searchable_text = title + " " + description

    # If no keywords were provided, include all bills
    if not KEYWORDS:
        bills.append(bill)

    # Otherwise filter by keywords
    elif any(keyword in searchable_text for keyword in KEYWORDS):
        bills.append(bill)

print(f"Total bills retrieved after filtering: {len(bills)}")

# ==========================
# STEP 3: Export CSV
# ==========================

df = pd.DataFrame(bills)

filename = f"{STATE}_filtered_bills.csv"
df.to_csv(filename, index=False)

print(f"Export complete! File saved as {filename}")
