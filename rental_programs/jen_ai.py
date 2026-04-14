import os
import json
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from openai import OpenAI

# =========================
# 🔑 Setup
# =========================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="NLIHC Rental Program Agent", layout="wide")
st.title("🏠 Rental Programs AI Agent")
st.caption("Find and structure rental program data for NLIHC dataset")

# =========================
# 🧠 Session State
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "logs" not in st.session_state:
    st.session_state.logs = []

# =========================
# 🧾 Logging
# =========================
def log(msg, data=None):
    st.session_state.logs.append({"msg": msg, "data": data})

# =========================
# 🌐 Scraper
# =========================
def scrape(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            log(f"Skipped (bad status): {url}")
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        for t in soup(["script", "style"]):
            t.decompose()

        text = soup.get_text(" ", strip=True)

        if len(text) < 200:
            log(f"Skipped (too little content): {url}")
            return None

        return text[:6000]

    except:
        log(f"Skipped (error scraping): {url}")
        return None

# =========================
# 🔍 Query Generator
# =========================
def generate_search_queries(user_query):
    prompt = f"""
Generate 3 search queries to find rental housing programs.

User query:
{user_query}

Focus on:
- government websites
- housing programs
"""
    res = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    queries = res.choices[0].message.content.split("\n")
    return [q.strip("- ").strip() for q in queries if q.strip()]

# =========================
# 🧩 Extraction + Relevance
# =========================
def extract_and_score(text, url, user_query):
    prompt = f"""
Extract rental program info and score relevance.

Return JSON:

{{
"Program Name": "",
"Location": "",
"Program Type": "",
"Income Eligibility Threshold": "",
"Duration": "",
"Website": "{url}",
"Relevance Score": 0-1,
"Relevance Explanation": ""
}}

User query:
{user_query}

Rules:
- Only extract explicit info
- If missing → "Unknown"
- Relevance based on location, type, income match
"""

    res = client.chat.completions.create(
        model="gpt-4.1",
        temperature=0,
        messages=[{"role": "user", "content": prompt + text}]
    )

    return json.loads(res.choices[0].message.content)

# =========================
# 🤖 Agent
# =========================
def run_agent(user_query):
    st.session_state.logs = []

    log("Parsing user query")

    queries = generate_search_queries(user_query)
    log("Generated search queries", queries)

    # 🔥 Replace later with real search API
    urls = [
        "https://www.hud.gov/topics/rental_assistance",
        "https://www.nyc.gov/site/hra/help/rental-assistance.page",
        "https://www.mass.gov/service-details/rental-assistance-programs",
        "https://www.la.gov/housing",
        "https://www.chicago.gov/city/en/depts/doh/provdrs/renters.html"
    ]

    log("Using candidate URLs", urls)

    results = []

    for url in urls:
        log(f"Checking: {url}")

        text = scrape(url)

        if not text:
            continue  # 🚫 skip bad pages

        try:
            data = extract_and_score(text, url, user_query)

            # 🚫 skip invalid extraction
            if not data.get("Program Name") or data.get("Program Name") == "Unknown":
                log(f"Skipped (no valid program): {url}")
                continue

            results.append(data)
            log("Added valid result", data)

        except:
            log(f"Skipped (extraction error): {url}")
            continue

    df = pd.DataFrame(results)

    if not df.empty:
        df = df.sort_values(by="Relevance Score", ascending=False)

        # 🔢 LIMIT TO TOP 8
        df = df.head(8)

    log(f"Final results count: {len(df)}")

    return df

# =========================
# 💬 Render Chat History
# =========================
# =========================
# 💬 Render Chat History (FULL)
# =========================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):

        # User message
        if msg["role"] == "user":
            st.markdown(msg["content"])

        # Assistant message
        else:
            st.markdown(msg["content"])

            # 🔥 Show table if exists
            if "data" in msg and msg["data"]:
                df = pd.DataFrame(msg["data"])
                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False)
                st.download_button(
                    "⬇️ Export",
                    csv,
                    "rental_programs.csv",
                    "text/csv",
                    key=f"download_{id(msg)}"
                )

            # 🔍 Relevance explanation
            if "data" in msg and msg["data"]:
                st.markdown("### 🔍 Why These Results")
                for row in msg["data"]:
                    st.markdown(f"""
**{row['Program Name']}**
- Score: {row['Relevance Score']}
- Why: {row['Relevance Explanation']}
- Source: {row['Website']}
""")

            # 📚 Workflow
            if "logs" in msg:
                with st.expander("Workflow"):
                    for step in msg["logs"]:
                        st.write(step["msg"])

# =========================
# 💬 Input
# =========================
query = st.chat_input("Search by state, program type, income...")

if query:
    # Save user message
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        status = st.status("Running agent...", expanded=True)

        df = run_agent(query)

        # =========================
        # 🧭 Workflow
        # =========================
        for step in st.session_state.logs:
            status.write(f"• {step['msg']}")

        status.update(label="Done", state="complete")

        # =========================
        # 📊 Results
        # =========================
        st.subheader("📊 Top 8 Relevant Programs")

        if not df.empty:
            st.dataframe(df, use_container_width=True)

            # =========================
            # ⬇️ Export
            # =========================
            csv = df.to_csv(index=False)

            st.download_button(
                "⬇️ Export to CSV (Google Sheets Ready)",
                csv,
                "rental_programs.csv",
                "text/csv"
            )

            # =========================
            # 🔍 Relevance Explanation
            # =========================
            st.subheader("🔍 Why These Results")

            for _, row in df.iterrows():
                st.markdown(f"""
**{row['Program Name']}**
- Score: {row['Relevance Score']}
- Why: {row['Relevance Explanation']}
- Source: {row['Website']}
""")

        else:
            st.warning("No valid programs found.")

        # =========================
        # 📚 Workflow Details
        # =========================
        with st.expander("Workflow Details"):
            for step in st.session_state.logs:
                st.write(step["msg"])
                if step["data"]:
                    st.json(step["data"])

    # Save assistant summary to chat history
    summary = f"Returned top {len(df)} relevant programs."
    st.session_state.messages.append({
        "role": "assistant",
        "content": summary,
        "data": df.to_dict(orient="records"),
        "logs": st.session_state.logs.copy()
    })
