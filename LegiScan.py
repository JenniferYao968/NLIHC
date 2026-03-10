import os
import requests
import json

# Get API key from environment variable
API_KEY = "aa506fd9cd8b7234dc9e9a31ee4724a9"

if not API_KEY:
    raise ValueError("API key not found. Set LEGISCAN_API_KEY environment variable.")

# Base URL for LegiScan API
BASE_URL = "https://api.legiscan.com/"

# Example: Get session list for a state (e.g., Texas = TX)
params = {
    "key": API_KEY,
    "op": "getDataSetList",
    "state": "TX"
}

response = requests.get(BASE_URL, params=params)

if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=2))
else:
    print("Error:", response.status_code)
