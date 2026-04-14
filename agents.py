import ollama
import json
import re


def clean_llm_output(text):
    """
    Extract JSON even if wrapped in markdown or extra text
    """

    if not text:
        return None

    text = text.replace("```json", "").replace("```", "")

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group())
        except:
            return None

    return None


def extract_agent(text, source_url):
    prompt = f"""
You are a strict JSON extraction system.

Return ONLY valid JSON.
- No markdown
- No explanation
- No backticks
- No extra text

If extraction fails, return empty JSON: {{}}

Schema:
{{
  "program_name": "",
  "agency": "",
  "location": "",
  "target_population": "",
  "eligibility": "",
  "benefits": "",
  "funding_type": "",
  "summary": ""
}}

TEXT:
{text}
"""

    response = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0}
    )

    content = response["message"]["content"]

    data = clean_llm_output(content)

    if not data:
        data = {
            "program_name": "Unknown Program",
            "agency": "",
            "location": "",
            "target_population": "",
            "eligibility": "",
            "benefits": "",
            "funding_type": "unknown",
            "summary": content[:300]
        }

    data["source_url"] = source_url

    return data

def validate_agent(data):
    if isinstance(data, dict):
        if not data.get("program_name"):
            data["program_name"] = "Unknown Program"

        if not data.get("funding_type"):
            data["funding_type"] = "unknown"

    return data
