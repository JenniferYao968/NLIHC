import streamlit as st
import requests
import pandas as pd
import re
import base64
import json
import time
from io import BytesIO

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

st.set_page_config(layout="wide")

st.image("nlihc_logo.svg", width=220)
st.markdown("## Legislative Bill Screener")

API_KEY = "aa506fd9cd8b7234dc9e9a31ee4724a9"

JURISDICTION_OPTIONS = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "Washington, D.C.",
    "US": "U.S. Congress",
}

ALL_JURISDICTION_CODES = list(JURISDICTION_OPTIONS.keys())

JURISDICTION_GROUPS = {
    "Northeast": {
        "New England": ["CT", "ME", "MA", "NH", "RI", "VT"],
        "Middle Atlantic": ["NJ", "NY", "PA"],
    },
    "Midwest": {
        "East North Central": ["IL", "IN", "MI", "OH", "WI"],
        "West North Central": ["IA", "KS", "MN", "MO", "NE", "ND", "SD"],
    },
    "South": {
        "South Atlantic": ["DE", "FL", "GA", "MD", "NC", "SC", "VA", "WV"],
        "East South Central": ["AL", "KY", "MS", "TN"],
        "West South Central": ["AR", "LA", "OK", "TX"],
    },
    "West": {
        "Mountain": ["AZ", "CO", "ID", "MT", "NV", "NM", "UT", "WY"],
        "Pacific": ["AK", "CA", "HI", "OR", "WA"],
    },
    "Federal / D.C.": {
        "Federal / D.C.": ["US", "DC"],
    },
}

BILL_STATUS_OPTIONS = {
    1: "Introduced",
    2: "Engrossed",
    3: "Enrolled",
    4: "Passed",
    5: "Vetoed",
    6: "Failed",
}

STATUS_SORT_PRIORITY = {
    "Passed": 1,
    "Enrolled": 2,
    "Engrossed": 3,
    "Introduced": 4,
    "Failed": 5,
    "Vetoed": 6,
}

SORT_OPTIONS = [
    "Original order",
    "AI relevance score",
    "Status",
    "Bill number",
    "Title A–Z",
]

RESULTS_PER_PAGE_OPTIONS = [10, 25, 50]

LAYER_1_KEYWORD_CATEGORIES = {
    "Broad housing topics": [
        "housing",
        "tenant",
        "renter",
        "landlord",
        "residential",
        "eviction",
        "rent",
        "rental",
        "discrimination",
    ]
}

LAYER_2_KEYWORD_CATEGORIES = {
    "Eviction process": [
        "notice",
        "rental assistance",
        "mediation",
        "legal aid",
        "record sealing",
        "evict",
        "unlawful detainer",
    ],
    "Tenant rights and retaliation": [
        "retaliation",
        "tenant rights",
        "habitability",
        "code enforcement",
    ],
    "Fees, deposits, and screening": [
        "security deposit",
        "fees",
        "screening",
        "credit reporting",
    ],
    "Voucher and fair housing": [
        "source of income",
        "voucher",
        "fair housing",
    ],
    "Rent regulation": [
        "just cause",
        "rent control",
        "rent stabilization",
        "rent increase",
    ],
}

LAYER_3_KEYWORD_CATEGORIES = {
    "Eviction details": [
        "nonpayment",
        "notice to quit",
        "eviction record",
        "court eviction",
        "emergency rental assistance",
    ],
    "Tenant protections": [
        "tenant union",
        "code violation",
        "anti harassment",
        "unsafe housing",
        "habitable",
    ],
    "Fees and deposits details": [
        "application fee",
        "screening fee",
        "rent reporting",
        "deposit limit",
    ],
    "Voucher and discrimination details": [
        "housing choice voucher",
        "section 8",
        "lawful source of income",
    ],
    "Rent regulation details": [
        "no fault eviction",
        "rent cap",
        "just cause eviction",
    ],
}

defaults = {
    "bills": [],
    "base_results": [],
    "second_layer_results": [],
    "third_layer_results": [],
    "status_filtered_results": [],
    "first_filter_text": "",
    "second_filter_text": "",
    "third_filter_text": "",
    "jurisdiction_text": "",
    "all_jurisdictions_mode": False,
    "selected_status_labels": [],
    "open_layer1_category": None,
    "open_layer2_category": None,
    "open_layer3_category": None,
    "open_focus_outer": False,
    "open_precision_outer": False,
    "open_jurisdiction_expander": False,
    "general_search_ran": False,
    "focus_search_ran": False,
    "precision_search_ran": False,
    "status_filter_ran": False,
    "api_total_calls": 0,
    "api_calls_session_lookup": 0,
    "api_calls_bill_list_lookup": 0,
    "api_calls_bill_details_lookup": 0,
    "api_calls_bill_text_lookup": 0,
    "display_sort_option": "Original order",
    "display_results_per_page": 25,
    "display_current_page": 1,
    "cart_sort_option": "Original order",
    "cart_results_per_page": 10,
    "cart_current_page": 1,
    "prepared_export_data": None,
    "prepared_export_count": 0,
    "results_displayed_expanded": False,
    "results_cart_expanded": False,
    "tenant_relevance_definition": """Bills that are relevant to the Tenant Protections Database are bills that create, expand, reduce, clarify, or affect legal protections, procedures, rights, remedies, or obligations related to residential tenants, renters, landlords, rental housing, eviction, habitability, rent regulation, tenant screening, security deposits, fees, fair housing, source of income protections, lease termination, notice requirements, or other renter-facing housing protections. Include bills that are clearly housing-related and may materially affect tenant stability, access, affordability, or legal protections. Exclude bills that are purely about homeownership, construction, zoning, taxation, or administrative government operations unless they directly affect tenant protections or renter rights.""",
    "ai_provider": "Mock",
    "ollama_base_url": "http://localhost:11434",
    "ollama_model_name": "gemma3",
    "ai_scoring_results": {},
    "ai_scoring_ran": False,
    "ai_scoring_in_progress": False,
    "ai_last_scored_count": 0,
    "ai_score_threshold": 0,
    "ai_show_only_above_threshold": False,
    "ai_full_text_results": {},
    "ai_full_text_ran": False,
    "ai_full_text_in_progress": False,
    "ai_full_text_last_scored_count": 0,
    "ui_message_type": "",
    "ui_message_text": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def parse_keywords(text):
    return [k.strip().lower() for k in text.split(",") if k.strip()]


def normalize_keywords_for_display(keywords):
    seen = set()
    ordered = []
    for k in keywords:
        cleaned = k.strip()
        lowered = cleaned.lower()
        if cleaned and lowered not in seen:
            seen.add(lowered)
            ordered.append(cleaned)
    return ordered


def format_filter_value(value_list):
    if not value_list:
        return "Not applied"
    return ", ".join(value_list)


def increment_api_counter(counter_key):
    st.session_state.api_total_calls += 1
    st.session_state[counter_key] += 1


def clear_ai_scores():
    st.session_state["ai_scoring_results"] = {}
    st.session_state["ai_scoring_ran"] = False
    st.session_state["ai_scoring_in_progress"] = False
    st.session_state["ai_last_scored_count"] = 0
    st.session_state["ai_score_threshold"] = 0
    st.session_state["ai_show_only_above_threshold"] = False
    st.session_state["ai_full_text_results"] = {}
    st.session_state["ai_full_text_ran"] = False
    st.session_state["ai_full_text_in_progress"] = False
    st.session_state["ai_full_text_last_scored_count"] = 0


def reset_display_pagination():
    st.session_state["display_current_page"] = 1


def reset_cart_pagination():
    st.session_state["cart_current_page"] = 1


def reset_all_pagination():
    reset_display_pagination()
    reset_cart_pagination()


def parse_jurisdiction_input(text):
    if not text:
        return []

    raw_parts = [p.strip() for p in text.split(",") if p.strip()]
    name_to_code = {name.lower(): code for code, name in JURISDICTION_OPTIONS.items()}
    extra_aliases = {
        "washington dc": "DC",
        "washington, dc": "DC",
        "district of columbia": "DC",
        "u.s. congress": "US",
        "us congress": "US",
        "congress": "US",
        "united states": "US",
    }

    selected_codes = []
    seen = set()

    for part in raw_parts:
        normalized = part.strip().upper()
        lowered = part.strip().lower()

        code = None
        if normalized in JURISDICTION_OPTIONS:
            code = normalized
        elif lowered in name_to_code:
            code = name_to_code[lowered]
        elif lowered in extra_aliases:
            code = extra_aliases[lowered]

        if code and code not in seen:
            selected_codes.append(code)
            seen.add(code)

    return selected_codes


def get_active_jurisdictions():
    if st.session_state.get("all_jurisdictions_mode", False):
        return ALL_JURISDICTION_CODES
    return parse_jurisdiction_input(st.session_state.get("jurisdiction_text", ""))


def toggle_jurisdiction(code):
    st.session_state["all_jurisdictions_mode"] = False
    current_codes = parse_jurisdiction_input(st.session_state.get("jurisdiction_text", ""))

    if code in current_codes:
        updated_codes = [c for c in current_codes if c != code]
    else:
        updated_codes = current_codes + [code]

    st.session_state["jurisdiction_text"] = ", ".join(updated_codes)
    st.session_state["open_jurisdiction_expander"] = True


def add_jurisdiction_group(codes):
    st.session_state["all_jurisdictions_mode"] = False
    current_codes = parse_jurisdiction_input(st.session_state.get("jurisdiction_text", ""))
    updated_codes = list(current_codes)

    for code in codes:
        if code not in updated_codes:
            updated_codes.append(code)

    st.session_state["jurisdiction_text"] = ", ".join(updated_codes)
    st.session_state["open_jurisdiction_expander"] = True


def remove_jurisdiction_group(codes):
    st.session_state["all_jurisdictions_mode"] = False
    current_codes = parse_jurisdiction_input(st.session_state.get("jurisdiction_text", ""))
    updated_codes = [code for code in current_codes if code not in codes]
    st.session_state["jurisdiction_text"] = ", ".join(updated_codes)
    st.session_state["open_jurisdiction_expander"] = True


def clear_all_selected_jurisdictions():
    st.session_state["all_jurisdictions_mode"] = False
    st.session_state["jurisdiction_text"] = ""
    st.session_state["open_jurisdiction_expander"] = True


def activate_all_jurisdictions_mode():
    st.session_state["all_jurisdictions_mode"] = True
    st.session_state["jurisdiction_text"] = ""
    st.session_state["open_jurisdiction_expander"] = False


def clear_filters_and_results():
    st.session_state["first_filter_text"] = ""
    st.session_state["second_filter_text"] = ""
    st.session_state["third_filter_text"] = ""
    st.session_state["jurisdiction_text"] = ""
    st.session_state["all_jurisdictions_mode"] = False
    st.session_state["selected_status_labels"] = []

    st.session_state["display_sort_option"] = "Original order"
    st.session_state["display_results_per_page"] = 25
    st.session_state["display_current_page"] = 1

    st.session_state["cart_sort_option"] = "Original order"
    st.session_state["cart_results_per_page"] = 10
    st.session_state["cart_current_page"] = 1

    st.session_state["prepared_export_data"] = None
    st.session_state["prepared_export_count"] = 0
    clear_ai_scores()

    st.session_state["bills"] = []
    st.session_state["base_results"] = []
    st.session_state["second_layer_results"] = []
    st.session_state["third_layer_results"] = []
    st.session_state["status_filtered_results"] = []

    st.session_state["open_layer1_category"] = None
    st.session_state["open_layer2_category"] = None
    st.session_state["open_layer3_category"] = None
    st.session_state["open_focus_outer"] = False
    st.session_state["open_precision_outer"] = False
    st.session_state["open_jurisdiction_expander"] = False

    st.session_state["general_search_ran"] = False
    st.session_state["focus_search_ran"] = False
    st.session_state["precision_search_ran"] = False
    st.session_state["status_filter_ran"] = False

    st.session_state["results_displayed_expanded"] = False
    st.session_state["results_cart_expanded"] = False
    st.session_state["ui_message_type"] = ""
    st.session_state["ui_message_text"] = ""

    keys_to_remove = [
        key for key in list(st.session_state.keys())
        if key.startswith("select_bill_widget_")
        or key.startswith("selected_bill_")
        or key.startswith("show_bill_text_")
        or key.startswith("bill_text_viewer_")
    ]
    for key in keys_to_remove:
        del st.session_state[key]


def clear_selected_bills():
    keys_to_remove = [
        key for key in list(st.session_state.keys())
        if key.startswith("select_bill_widget_") or key.startswith("selected_bill_")
    ]
    for key in keys_to_remove:
        del st.session_state[key]

    st.session_state["prepared_export_data"] = None
    st.session_state["prepared_export_count"] = 0
    st.session_state["ai_full_text_results"] = {}
    st.session_state["ai_full_text_ran"] = False
    st.session_state["ai_full_text_in_progress"] = False
    st.session_state["ai_full_text_last_scored_count"] = 0
    st.session_state["results_cart_expanded"] = True


def go_previous_display_page():
    if st.session_state.display_current_page > 1:
        st.session_state.display_current_page -= 1
    st.session_state["results_displayed_expanded"] = True


def go_next_display_page(total_pages):
    if st.session_state.display_current_page < total_pages:
        st.session_state.display_current_page += 1
    st.session_state["results_displayed_expanded"] = True


def go_previous_cart_page():
    if st.session_state.cart_current_page > 1:
        st.session_state.cart_current_page -= 1
    st.session_state["results_cart_expanded"] = True


def go_next_cart_page(total_pages):
    if st.session_state.cart_current_page < total_pages:
        st.session_state.cart_current_page += 1
    st.session_state["results_cart_expanded"] = True


def toggle_first_filter_keyword(phrase, category):
    existing_display = normalize_keywords_for_display(
        [k.strip() for k in st.session_state.first_filter_text.split(",") if k.strip()]
    )
    existing_lower = [k.lower() for k in existing_display]

    if phrase.lower() in existing_lower:
        updated = [k for k in existing_display if k.lower() != phrase.lower()]
    else:
        updated = existing_display + [phrase]

    st.session_state.first_filter_text = ", ".join(updated)
    st.session_state.open_layer1_category = category


def toggle_second_filter_keyword(phrase, category):
    existing_display = normalize_keywords_for_display(
        [k.strip() for k in st.session_state.second_filter_text.split(",") if k.strip()]
    )
    existing_lower = [k.lower() for k in existing_display]

    if phrase.lower() in existing_lower:
        updated = [k for k in existing_display if k.lower() != phrase.lower()]
    else:
        updated = existing_display + [phrase]

    st.session_state.second_filter_text = ", ".join(updated)
    st.session_state.open_layer2_category = category
    st.session_state.open_focus_outer = True


def toggle_third_filter_keyword(phrase, category):
    existing_display = normalize_keywords_for_display(
        [k.strip() for k in st.session_state.third_filter_text.split(",") if k.strip()]
    )
    existing_lower = [k.lower() for k in existing_display]

    if phrase.lower() in existing_lower:
        updated = [k for k in existing_display if k.lower() != phrase.lower()]
    else:
        updated = existing_display + [phrase]

    st.session_state.third_filter_text = ", ".join(updated)
    st.session_state.open_layer3_category = category
    st.session_state.open_precision_outer = True


def get_category_selection_status(phrases, selected_text):
    selected_keywords = parse_keywords(selected_text)
    selected_count = sum(1 for phrase in phrases if phrase.lower() in selected_keywords)
    total_count = len(phrases)
    return selected_count, total_count


def apply_status_filter(bills, selected_status_labels):
    if not selected_status_labels:
        return bills

    allowed_status_codes = {
        code for code, label in BILL_STATUS_OPTIONS.items()
        if label in selected_status_labels
    }

    return [bill for bill in bills if bill.get("status") in allowed_status_codes]


def highlight_keywords(text, keywords):
    if not text:
        return "No text available."

    highlighted_text = text
    for keyword in keywords:
        if keyword:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            highlighted_text = pattern.sub(
                lambda match: (
                    f"<span style='background-color: #fff176; "
                    f"font-weight: 700; padding: 0 3px; border-radius: 3px;'>"
                    f"{match.group(0)}</span>"
                ),
                highlighted_text
            )
    return highlighted_text


def shorten_text(text, max_len=85):
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= max_len:
        return text
    shortened = text[:max_len].rsplit(" ", 1)[0]
    if not shortened:
        shortened = text[:max_len]
    return shortened + "..."


def get_priority_bucket(score):
    if score >= 85:
        return "High"
    if score >= 60:
        return "Medium"
    if score >= 35:
        return "Low"
    return "Not Relevant"


def build_bill_scoring_payload(bill):
    return {
        "bill_id": bill.get("bill_id"),
        "state": bill.get("search_state", ""),
        "bill_number": bill.get("bill_number") or bill.get("number") or "",
        "title": bill.get("title", ""),
        "description": bill.get("description", ""),
    }


OLLAMA_SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "relevance_score": {"type": "integer"},
        "priority_bucket": {"type": "string"},
        "confidence": {"type": "string"},
        "include_recommendation": {"type": "string"},
        "reasoning": {"type": "array", "items": {"type": "string"}},
        "ambiguity_flags": {"type": "array", "items": {"type": "string"}}
    },
    "required": [
        "relevance_score",
        "priority_bucket",
        "confidence",
        "include_recommendation",
        "reasoning",
        "ambiguity_flags"
    ]
}

FULL_TEXT_TOPIC_OPTIONS = [
    "ERA Related Protections",
    "Eviction Moratorium",
    "Allows Payment to Stop Eviction",
    "Right to Counsel",
    "Eviction Legal Defense Fund",
    "Landlord and Tenant Mediation",
    "Source of Income Protection",
    "Just Cause Standards",
    "Code Enforcement/Strengthening Habitability Standards",
    "Rent Stabilization Standards",
    "Anti-Retaliation",
    "Expunge/Seal Eviction Records",
    "Limits Fees",
    "Strengthens Written Notice or Summons Process",
    "Notice Period, Nonpayment of Rent",
    "Preemption",
    "None of the Above",
]

OLLAMA_FULL_TEXT_SCHEMA = {
    "type": "object",
    "properties": {
        "full_text_relevance_score": {"type": "integer"},
        "full_text_priority_bucket": {"type": "string"},
        "full_text_confidence": {"type": "string"},
        "full_text_include_recommendation": {"type": "string"},
        "full_text_reasoning": {"type": "array", "items": {"type": "string"}},
        "full_text_ambiguity_flags": {"type": "array", "items": {"type": "string"}},
        "key_provisions_summary": {"type": "array", "items": {"type": "string"}},
        "tenant_protection_topics": {"type": "array", "items": {"type": "string", "enum": FULL_TEXT_TOPIC_OPTIONS}},
        "manual_review_points": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "full_text_relevance_score",
        "full_text_priority_bucket",
        "full_text_confidence",
        "full_text_include_recommendation",
        "full_text_reasoning",
        "full_text_ambiguity_flags",
        "key_provisions_summary",
        "tenant_protection_topics",
        "manual_review_points",
    ]
}



def normalize_ai_score_result(result):
    score = result.get("relevance_score", 0)
    try:
        score = int(float(score))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    bucket = result.get("priority_bucket") or get_priority_bucket(score)
    if bucket not in {"High", "Medium", "Low", "Not Relevant"}:
        bucket = get_priority_bucket(score)

    confidence = str(result.get("confidence", "Low") or "Low").strip().title()
    if confidence not in {"High", "Medium", "Low"}:
        confidence = "Low"

    recommendation = str(result.get("include_recommendation", "No") or "No").strip().title()
    if recommendation not in {"Review", "Maybe", "No"}:
        recommendation = "No"

    reasoning = result.get("reasoning", [])
    if isinstance(reasoning, str):
        reasoning = [reasoning]
    reasoning = [str(item).strip() for item in reasoning if str(item).strip()]

    ambiguity_flags = result.get("ambiguity_flags", [])
    if isinstance(ambiguity_flags, str):
        ambiguity_flags = [ambiguity_flags]
    ambiguity_flags = [str(item).strip() for item in ambiguity_flags if str(item).strip()]

    return {
        "relevance_score": score,
        "priority_bucket": bucket,
        "confidence": confidence,
        "include_recommendation": recommendation,
        "reasoning": reasoning[:4],
        "ambiguity_flags": ambiguity_flags[:4],
    }


def normalize_full_text_ai_result(result):
    score = result.get("full_text_relevance_score", 0)
    try:
        score = int(float(score))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    bucket = result.get("full_text_priority_bucket") or get_priority_bucket(score)
    if bucket not in {"High", "Medium", "Low", "Not Relevant"}:
        bucket = get_priority_bucket(score)

    confidence = str(result.get("full_text_confidence", "Low") or "Low").strip().title()
    if confidence not in {"High", "Medium", "Low"}:
        confidence = "Low"

    recommendation = str(result.get("full_text_include_recommendation", "No") or "No").strip().title()
    if recommendation not in {"Review", "Maybe", "No"}:
        recommendation = "No"

    def clean_list(value, max_items):
        if isinstance(value, str):
            value = [value]
        value = [str(item).strip() for item in (value or []) if str(item).strip()]
        return value[:max_items]

    reasoning = clean_list(result.get("full_text_reasoning", []), 4)
    ambiguity_flags = clean_list(result.get("full_text_ambiguity_flags", []), 4)
    key_provisions_summary = clean_list(result.get("key_provisions_summary", []), 5)
    tenant_protection_topics = clean_list(result.get("tenant_protection_topics", []), 4)
    tenant_protection_topics = [topic for topic in tenant_protection_topics if topic in FULL_TEXT_TOPIC_OPTIONS]
    if not tenant_protection_topics:
        tenant_protection_topics = ["None of the Above"]
    manual_review_points = clean_list(result.get("manual_review_points", []), 4)

    if tenant_protection_topics == ["None of the Above"]:
        score = min(score, 35)
        bucket = get_priority_bucket(score)
        if recommendation == "Review":
            recommendation = "Maybe" if score >= 35 else "No"
        none_of_above_note = "The model selected 'None of the Above' for tenant-protection topics, which is a strong signal that the bill may be out of scope unless a clear residential landlord-tenant mechanism is identified."
        if none_of_above_note not in ambiguity_flags:
            ambiguity_flags = [none_of_above_note] + ambiguity_flags

    return {
        "full_text_relevance_score": score,
        "full_text_priority_bucket": bucket,
        "full_text_confidence": confidence,
        "full_text_include_recommendation": recommendation,
        "full_text_reasoning": reasoning,
        "full_text_ambiguity_flags": ambiguity_flags[:4],
        "key_provisions_summary": key_provisions_summary,
        "tenant_protection_topics": tenant_protection_topics,
        "manual_review_points": manual_review_points,
    }


def get_full_text_review_unavailable_result(reason):
    return {
        "full_text_relevance_score": 0,
        "full_text_priority_bucket": "Not Relevant",
        "full_text_confidence": "Low",
        "full_text_include_recommendation": "Maybe",
        "full_text_reasoning": [reason],
        "full_text_ambiguity_flags": ["Full-text AI review could not be completed for this bill."],
        "key_provisions_summary": [],
        "tenant_protection_topics": ["None of the Above"],
        "manual_review_points": ["Retrieve or verify the latest bill text manually before relying on the full-text assessment."],
        "review_status": "unavailable",
    }


def truncate_text_for_llm(text_value, max_chars=24000):
    text_value = str(text_value or "").strip()
    if len(text_value) <= max_chars:
        return text_value
    return text_value[:max_chars] + "\n\n[Truncated for model input due to length.]"

def detect_scope_guard_signals(text_value):
    text_value = str(text_value or "")
    lowered = f" {text_value.lower()} "

    residential_patterns = [
        r"\blandlord\b", r"\btenant\b", r"\btenants\b", r"\brenter\b", r"\brenters\b",
        r"\brental\b", r"\brent\b", r"\blease\b", r"\beviction\b", r"\bevict\b",
        r"security deposit", r"source of income", r"habitability", r"rent stabilization", r"rent control",
        r"nonpayment of rent", r"notice to quit", r"right to counsel", r"late fee", r"screening fee",
        r"just cause", r"retaliation", r"mobile home"
    ]
    residential_count = sum(1 for pattern in residential_patterns if re.search(pattern, lowered))

    out_of_scope_patterns = [
        r"lieutenant governor", r"governor and lieutenant governor", r"correctional facilit",
        r"\bincarcerated\b", r"\binmate\b", r"\bprison\b", r"\bjail\b", r"\bparole\b",
        r"work release", r"department of corrections", r"community supervision", r"police officer",
        r"attorney-general", r"firefighters", r"court of claims", r"trial and grand jurors",
        r"legislature", r"gun violence", r"body-worn cameras"
    ]
    out_of_scope_count = sum(1 for pattern in out_of_scope_patterns if re.search(pattern, lowered))

    strong_lieutenant_signal = bool(re.search(r"lieutenant governor", lowered)) and residential_count == 0
    strong_out_of_scope = strong_lieutenant_signal or (out_of_scope_count >= 3 and residential_count == 0) or (out_of_scope_count >= 5 and residential_count <= 1)

    return {
        "residential_count": residential_count,
        "out_of_scope_count": out_of_scope_count,
        "strong_out_of_scope": strong_out_of_scope,
        "strong_lieutenant_signal": strong_lieutenant_signal,
    }


def apply_scope_guard_to_first_pass_result(result, bill):
    combined = " ".join([
        str(bill.get("title", "") or ""),
        str(bill.get("description", "") or "")
    ])
    signals = detect_scope_guard_signals(combined)
    if not signals["strong_out_of_scope"]:
        return result

    updated = dict(result)
    updated["relevance_score"] = min(int(updated.get("relevance_score", 0) or 0), 25)
    updated["priority_bucket"] = get_priority_bucket(updated["relevance_score"])
    updated["confidence"] = "Medium" if updated["relevance_score"] > 0 else "Low"
    updated["include_recommendation"] = "No"

    reasoning = list(updated.get("reasoning", []))
    ambiguity_flags = list(updated.get("ambiguity_flags", []))
    guard_reason = "The bill appears primarily focused on correctional, governmental, or other non-residential contexts rather than residential landlord-tenant protections in the rental market."
    if signals["strong_lieutenant_signal"]:
        guard_reason = "The text appears to use phrases like 'lieutenant governor' rather than residential landlord-tenant terminology, so it should not be treated as a tenant-protection bill."
    if guard_reason not in reasoning:
        reasoning = [guard_reason] + reasoning
    ambiguity_note = "Strong scope guard applied because the text is dominated by non-residential landlord-tenant context signals."
    if ambiguity_note not in ambiguity_flags:
        ambiguity_flags = [ambiguity_note] + ambiguity_flags

    updated["reasoning"] = reasoning[:4]
    updated["ambiguity_flags"] = ambiguity_flags[:4]
    return updated


def apply_scope_guard_to_full_text_result(result, bill, full_text):
    combined = " ".join([
        str(bill.get("title", "") or ""),
        str(bill.get("description", "") or ""),
        str(full_text or "")
    ])
    signals = detect_scope_guard_signals(combined)
    if not signals["strong_out_of_scope"]:
        return result

    updated = dict(result)
    updated["full_text_relevance_score"] = min(int(updated.get("full_text_relevance_score", 0) or 0), 20)
    updated["full_text_priority_bucket"] = get_priority_bucket(updated["full_text_relevance_score"])
    updated["full_text_confidence"] = "Medium" if updated["full_text_relevance_score"] > 0 else "Low"
    updated["full_text_include_recommendation"] = "No"

    reasoning = list(updated.get("full_text_reasoning", []))
    ambiguity_flags = list(updated.get("full_text_ambiguity_flags", []))
    key_provisions = list(updated.get("key_provisions_summary", []))
    manual_review = list(updated.get("manual_review_points", []))

    guard_reason = "The bill text is primarily about correctional, governmental, or other non-residential contexts rather than residential landlord-tenant protections in the rental market."
    if signals["strong_lieutenant_signal"]:
        guard_reason = "The bill text includes 'lieutenant governor' in a governmental-office context, which is not evidence of tenant-protection relevance."
    if guard_reason not in reasoning:
        reasoning = [guard_reason] + reasoning
    guard_flag = "Strong scope guard applied because the primary context is not the residential landlord-tenant rental market."
    if guard_flag not in ambiguity_flags:
        ambiguity_flags = [guard_flag] + ambiguity_flags

    if not key_provisions:
        key_provisions = ["No clear residential landlord-tenant protection mechanism was identified in the retrieved bill text."]
    else:
        key_provisions = ["No clear residential landlord-tenant protection mechanism was identified in the retrieved bill text."] + key_provisions

    manual_point = "Confirm manually only if a specific residential rental landlord-tenant provision is suspected despite the bill's broader non-residential context."
    if manual_point not in manual_review:
        manual_review = [manual_point] + manual_review

    updated["tenant_protection_topics"] = ["None of the Above"]
    updated["full_text_reasoning"] = reasoning[:4]
    updated["full_text_ambiguity_flags"] = ambiguity_flags[:4]
    updated["key_provisions_summary"] = key_provisions[:5]
    updated["manual_review_points"] = manual_review[:4]
    return updated


def map_full_text_topics_from_text(combined_text):
    topic_keywords = {
        "ERA Related Protections": ["emergency rental assistance", "era", "rental assistance"],
        "Eviction Moratorium": ["moratorium", "temporary halt on evictions"],
        "Allows Payment to Stop Eviction": ["pay to stay", "cure", "payment to stop eviction", "tender rent"],
        "Right to Counsel": ["right to counsel", "appointed counsel", "civil legal counsel"],
        "Eviction Legal Defense Fund": ["legal defense fund", "eviction defense fund"],
        "Landlord and Tenant Mediation": ["mediation", "landlord and tenant mediation"],
        "Source of Income Protection": ["source of income", "lawful source of income", "voucher discrimination"],
        "Just Cause Standards": ["just cause", "good cause", "no fault eviction"],
        "Code Enforcement/Strengthening Habitability Standards": ["habitability", "code enforcement", "health and safety", "repair and deduct", "substandard housing"],
        "Rent Stabilization Standards": ["rent stabilization", "rent control", "rent cap"],
        "Anti-Retaliation": ["retaliation", "retaliatory"],
        "Expunge/Seal Eviction Records": ["seal eviction", "expunge eviction", "eviction records", "record sealing"],
        "Limits Fees": ["late fee", "application fee", "screening fee", "fee cap", "limits fees"],
        "Strengthens Written Notice or Summons Process": ["written notice", "summons", "service of process", "notice requirements"],
        "Notice Period, Nonpayment of Rent": ["nonpayment", "notice period", "notice to quit", "days notice"],
        "Preemption": ["preempt", "preemption"],
    }
    topics = []
    for topic, keywords in topic_keywords.items():
        if any(keyword in combined_text for keyword in keywords):
            topics.append(topic)
    return topics[:4] if topics else ["None of the Above"]


def build_full_text_review_payload(bill, full_text):
    payload = build_bill_scoring_payload(bill)
    payload["full_text"] = full_text
    return payload


def score_bill_with_ollama(bill, relevance_definition, base_url, model_name):
    payload = build_bill_scoring_payload(bill)
    base_url = (base_url or "http://localhost:11434").strip().rstrip("/")
    model_name = (model_name or "gemma3").strip()

    prompt = f"""
You are assisting a housing policy research team reviewing legislation for potential inclusion in a Tenant Protections Database.

Tenant protections relevance definition:
{relevance_definition}

Instructions:
- Use only the bill title and description.
- Score relevance for inclusion, tracking, or review in the NLIHC Tenant Protections Database, not for housing or protections policy generally.
- Focus on the residential landlord-tenant rental market.
- Do not treat the substring "tenant" inside unrelated phrases like "lieutenant governor" as evidence of tenant-protection relevance.
- Bills are not in scope merely because they mention housing, residents, protections, law enforcement, prior incarceration, or public institutions; those are relevant only if the bill materially changes protections, rights, procedures, or obligations in the residential landlord-tenant context.
- If the primary context is governmental offices, corrections, prisons, jails, policing, courts, pensions, or other non-residential systems, score low unless the title/description clearly indicates a residential rental landlord-tenant mechanism.
- Return only valid JSON that matches the requested schema.
- Keep reasoning concise and specific.
- Use score ranges consistently: 85-100 High, 60-84 Medium, 35-59 Low, 0-34 Not Relevant.
- Confidence must be High, Medium, or Low.
- Include recommendation must be Review, Maybe, or No.

Bill:
State: {payload['state']}
Bill number: {payload['bill_number']}
Title: {payload['title']}
Description: {payload['description']}

Return only valid JSON matching this schema:
{json.dumps(OLLAMA_SCORE_SCHEMA)}
""".strip()

    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "format": OLLAMA_SCORE_SCHEMA,
                "stream": False,
            },
            timeout=180,
        )
        response.raise_for_status()
        data = response.json()
        raw_content = data.get("response", "{}")
        parsed = json.loads(raw_content)
        normalized = normalize_ai_score_result(parsed)
        return apply_scope_guard_to_first_pass_result(normalized, bill)
    except requests.exceptions.RequestException as exc:
        return {
            "relevance_score": 0,
            "priority_bucket": "Not Relevant",
            "confidence": "Low",
            "include_recommendation": "No",
            "reasoning": [f"Ollama request failed: {exc}"],
            "ambiguity_flags": ["Local model response could not be retrieved."],
        }
    except json.JSONDecodeError:
        return {
            "relevance_score": 0,
            "priority_bucket": "Not Relevant",
            "confidence": "Low",
            "include_recommendation": "No",
            "reasoning": ["Ollama returned a response that could not be parsed into structured fields."],
            "ambiguity_flags": ["Local model response was not valid JSON."],
        }


def score_bill_full_text_with_ollama(bill, full_text, relevance_definition, base_url, model_name):
    payload = build_full_text_review_payload(bill, full_text)
    base_url = (base_url or "http://localhost:11434").strip().rstrip("/")
    model_name = (model_name or "gemma3").strip()
    allowed_topics = ", ".join(FULL_TEXT_TOPIC_OPTIONS)

    prompt = f"""
You are assisting a housing policy research team reviewing legislation for potential inclusion in a Tenant Protections Database.

Tenant protections relevance definition:
{relevance_definition}

Instructions:
- Use the bill title, description, and full bill text.
- Score relevance for inclusion, tracking, or review in the NLIHC Tenant Protections Database, not for housing or protections policy generally.
- Focus on whether the bill's primary regulated context is the residential landlord-tenant rental market.
- Do not treat the substring "tenant" inside unrelated phrases like "lieutenant governor" as evidence of tenant-protection relevance.
- Law enforcement, prior incarceration, criminal-record, or public-safety language does not make a bill out of scope by itself; it matters only if the bill materially changes protections, rights, procedures, or obligations in the residential landlord-tenant context.
- If the bill's primary context is governmental offices, corrections, prisons, jails, policing, courts, pensions, or other non-residential systems, score low unless the full text clearly establishes a residential rental landlord-tenant mechanism.
- Choosing "None of the Above" for tenant_protection_topics should be a strong signal that the bill is likely out of scope unless the reasoning clearly identifies a residential landlord-tenant protection mechanism.
- Return only valid JSON matching the schema.
- Keep reasoning concise and specific.
- Keep key_provisions_summary as a bullet-list style array with 2 to 5 concise bullets when possible.
- tenant_protection_topics must use only these labels: {allowed_topics}
- manual_review_points must always be present and may be an empty list.
- Use score ranges consistently: 85-100 High, 60-84 Medium, 35-59 Low, 0-34 Not Relevant.
- Confidence must be High, Medium, or Low.
- Include recommendation must be Review, Maybe, or No.

Bill:
State: {payload['state']}
Bill number: {payload['bill_number']}
Title: {payload['title']}
Description: {payload['description']}

Full bill text:
{truncate_text_for_llm(payload['full_text'])}

Return only valid JSON matching this schema:
{json.dumps(OLLAMA_FULL_TEXT_SCHEMA)}
""".strip()

    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "format": OLLAMA_FULL_TEXT_SCHEMA,
                "stream": False,
            },
            timeout=240,
        )
        response.raise_for_status()
        data = response.json()
        raw_content = data.get("response", "{}")
        parsed = json.loads(raw_content)
        normalized = normalize_full_text_ai_result(parsed)
        normalized["review_status"] = "completed"
        return normalized
    except requests.exceptions.RequestException as exc:
        result = get_full_text_review_unavailable_result(f"Ollama full-text request failed: {exc}")
        result["manual_review_points"] = ["Retry the full-text review after confirming Ollama is running locally and the model is loaded."]
        return result
    except json.JSONDecodeError:
        result = get_full_text_review_unavailable_result("Ollama returned a full-text response that could not be parsed into structured fields.")
        result["manual_review_points"] = ["Retry the full-text review or inspect the bill manually because the model output could not be parsed."]
        return result


def mock_score_bill_full_text(bill, full_text, relevance_definition):
    payload = build_full_text_review_payload(bill, full_text)
    combined = f"{payload.get('title', '')} {payload.get('description', '')} {payload.get('full_text', '')}".lower()

    positive_terms = [
        "tenant", "renter", "landlord", "eviction", "rent", "rental",
        "habitability", "security deposit", "notice", "lease",
        "source of income", "fair housing", "voucher", "retaliation",
        "discrimination", "housing", "unlawful detainer", "just cause",
        "mediation", "counsel", "fee", "nonpayment", "preemption"
    ]
    strong_terms = [
        "eviction", "just cause", "source of income", "habitability",
        "retaliation", "rent stabilization", "right to counsel", "nonpayment"
    ]

    matches = sum(1 for term in positive_terms if term in combined)
    strong_matches = sum(1 for term in strong_terms if term in combined)
    score = min(100, 18 + matches * 4 + strong_matches * 9)
    bucket = get_priority_bucket(score)

    reasoning = []
    if any(term in combined for term in ["eviction", "unlawful detainer", "nonpayment"]):
        reasoning.append("The full bill text appears to regulate eviction procedures, nonpayment issues, or related tenant defenses.")
    if any(term in combined for term in ["notice", "summons", "service of process"]):
        reasoning.append("The bill text appears to affect notice requirements or the process for serving summonses or eviction notices.")
    if any(term in combined for term in ["habitability", "code enforcement", "repair"]):
        reasoning.append("The bill text appears to address habitability standards, repairs, or code enforcement that affect tenants.")
    if any(term in combined for term in ["fee", "security deposit", "screening"]):
        reasoning.append("The bill text appears to regulate fees, deposits, or tenant screening practices.")
    if not reasoning:
        reasoning.append("The full bill text does not show strong obvious tenant-protection language, although some housing-related content may still be present.")

    ambiguity_flags = []
    if len(full_text or "") < 200:
        ambiguity_flags.append("The retrieved bill text is short or incomplete, so the full-text assessment may be less reliable.")
    if score < 60:
        ambiguity_flags.append("The bill may still require manual review because the full text is not clearly focused on tenant protections.")

    key_provisions = []
    if "nonpayment" in combined or "notice to quit" in combined:
        key_provisions.append("Addresses notice timing, nonpayment procedures, or conditions tied to eviction for unpaid rent.")
    if "retaliation" in combined:
        key_provisions.append("Includes language related to retaliation protections for tenants asserting rights or reporting conditions.")
    if "security deposit" in combined or "late fee" in combined or "application fee" in combined:
        key_provisions.append("Regulates deposits or tenant-facing fees such as late fees, application fees, or similar charges.")
    if "source of income" in combined or "voucher" in combined:
        key_provisions.append("Includes language affecting voucher holders or source-of-income protections in rental housing.")
    if "rent stabilization" in combined or "rent control" in combined or "rent cap" in combined:
        key_provisions.append("Contains rent regulation language such as stabilization, control, or caps on rent increases.")
    if not key_provisions:
        key_provisions.append("No clearly targeted tenant-protection provision was identified from the retrieved full text in this mock review.")

    manual_review_points = []
    if any(term in combined for term in ["shall", "may", "except", "unless"]):
        manual_review_points.append("Verify the scope, exceptions, and effective applicability in the bill text before deciding whether to include it in the database.")
    if "preempt" in combined or "preemption" in combined:
        manual_review_points.append("Confirm whether the bill limits local tenant-protection ordinances through preemption language.")

    topics = map_full_text_topics_from_text(combined)

    return {
        "full_text_relevance_score": score,
        "full_text_priority_bucket": bucket,
        "full_text_confidence": "High" if score >= 85 else "Medium" if score >= 45 else "Low",
        "full_text_include_recommendation": "Review" if score >= 60 else "Maybe" if score >= 35 else "No",
        "full_text_reasoning": reasoning[:4],
        "full_text_ambiguity_flags": ambiguity_flags[:4],
        "key_provisions_summary": key_provisions[:5],
        "tenant_protection_topics": topics[:4],
        "manual_review_points": manual_review_points[:4],
        "review_status": "completed",
    }


def get_bill_details_and_full_text_for_review(bill):
    details = get_bill_details(bill.get("bill_id"), API_KEY)
    if not details:
        return {}, {}, ""
    latest_text_record = get_latest_text_record(details, API_KEY)
    full_text = extract_full_bill_text(latest_text_record)
    return details, latest_text_record, full_text


def run_full_text_ai_review_on_cart(cart_bills):
    relevance_definition = st.session_state.get("tenant_relevance_definition", "").strip()
    provider = st.session_state.get("ai_provider", "Mock")
    base_url = st.session_state.get("ollama_base_url", "http://localhost:11434")
    model_name = st.session_state.get("ollama_model_name", "gemma3")

    results = {}
    st.session_state["ai_full_text_in_progress"] = True

    for bill in cart_bills:
        bill_id = bill.get("bill_id")
        if not bill_id:
            continue

        _, latest_text_record, full_text = get_bill_details_and_full_text_for_review(bill)

        unavailable_markers = [
            "[No bill text available]",
            "[No bill text document returned]",
            "[Unable to decode base64 bill document]",
            "[Unable to extract text from PDF bill document]",
        ]
        if (not full_text) or any(full_text.startswith(marker) for marker in unavailable_markers) or full_text.startswith("[Unsupported bill text format") or full_text.startswith("[PDF text extraction unavailable"):
            results[bill_id] = get_full_text_review_unavailable_result(f"Full bill text was unavailable for {bill.get('search_state', '')} {bill.get('bill_number') or bill.get('number') or bill_id}.")
            continue

        if provider == "Ollama":
            results[bill_id] = score_bill_full_text_with_ollama(bill, full_text, relevance_definition, base_url, model_name)
        else:
            results[bill_id] = mock_score_bill_full_text(bill, full_text, relevance_definition)

    st.session_state["ai_full_text_results"] = results
    st.session_state["ai_full_text_ran"] = True
    st.session_state["ai_full_text_in_progress"] = False
    st.session_state["ai_full_text_last_scored_count"] = len(results)


def mock_score_bill_for_tenant_relevance(bill, relevance_definition):
    payload = build_bill_scoring_payload(bill)
    title = (payload.get("title") or "").lower()
    description = (payload.get("description") or "").lower()
    combined = f"{title} {description}".strip()

    positive_terms = [
        "tenant", "renter", "landlord", "eviction", "rent", "rental",
        "habitability", "security deposit", "notice", "lease",
        "source of income", "fair housing", "voucher", "retaliation",
        "discrimination", "housing", "unlawful detainer", "just cause"
    ]

    strong_terms = [
        "eviction", "tenant", "renter", "habitability", "security deposit",
        "just cause", "source of income", "unlawful detainer"
    ]

    matches = sum(1 for term in positive_terms if term in combined)
    strong_matches = sum(1 for term in strong_terms if term in combined)
    score = min(100, 10 + matches * 8 + strong_matches * 10)
    bucket = get_priority_bucket(score)

    reasoning = []
    ambiguity_flags = []

    if "eviction" in combined or "unlawful detainer" in combined:
        reasoning.append("The bill appears related to eviction processes or procedural tenant protections.")
    if "rent" in combined or "rental" in combined or "lease" in combined:
        reasoning.append("The bill appears to affect rental housing, rent-related issues, or lease terms.")
    if "tenant" in combined or "renter" in combined:
        reasoning.append("The title or description explicitly references tenants or renters.")
    if "security deposit" in combined or "fee" in combined or "screening" in combined:
        reasoning.append("The bill may affect deposits, fees, or tenant screening practices.")
    if "fair housing" in combined or "source of income" in combined or "discrimination" in combined:
        reasoning.append("The bill may affect anti-discrimination or housing access protections.")

    if not reasoning:
        reasoning.append("The title and description show limited direct tenant-protection language.")

    if len(combined) < 40:
        ambiguity_flags.append("Title/description is brief, so the relevance estimate may be less reliable.")
    if score < 60:
        ambiguity_flags.append("The bill may be housing-adjacent but not clearly tenant-protection specific from the available summary.")

    return {
        "relevance_score": score,
        "priority_bucket": bucket,
        "confidence": "High" if score >= 85 else "Medium" if score >= 45 else "Low",
        "include_recommendation": "Review" if score >= 60 else "Maybe" if score >= 35 else "No",
        "reasoning": reasoning[:3],
        "ambiguity_flags": ambiguity_flags[:2],
    }


def run_ai_scoring_on_displayed_bills(display_bills):
    relevance_definition = st.session_state.get("tenant_relevance_definition", "").strip()
    provider = st.session_state.get("ai_provider", "Mock")
    base_url = st.session_state.get("ollama_base_url", "http://localhost:11434")
    model_name = st.session_state.get("ollama_model_name", "gemma3")
    results = {}

    st.session_state["ai_scoring_in_progress"] = True

    for bill in display_bills:
        bill_id = bill.get("bill_id")
        if not bill_id:
            continue
        if provider == "Ollama":
            results[bill_id] = score_bill_with_ollama(bill, relevance_definition, base_url, model_name)
        else:
            results[bill_id] = mock_score_bill_for_tenant_relevance(bill, relevance_definition)

    st.session_state["ai_scoring_results"] = results
    st.session_state["ai_scoring_ran"] = True
    st.session_state["ai_scoring_in_progress"] = False
    st.session_state["ai_last_scored_count"] = len(results)



def filter_bills_by_ai_score(bills):
    if not st.session_state.get("ai_show_only_above_threshold", False):
        return bills

    threshold = st.session_state.get("ai_score_threshold", 0)
    ai_results = st.session_state.get("ai_scoring_results", {})

    filtered = []
    for bill in bills:
        bill_id = bill.get("bill_id")
        result = ai_results.get(bill_id)
        if result and result.get("relevance_score", 0) >= threshold:
            filtered.append(bill)

    return filtered


def make_unique_sheet_name(base_name, used_names):
    invalid_chars = ['\\', '/', '*', '?', ':', '[', ']']
    for ch in invalid_chars:
        base_name = base_name.replace(ch, "_")
    base_name = base_name.strip() or "Bill"
    base_name = base_name[:31]

    candidate = base_name
    counter = 2
    while candidate in used_names:
        suffix = f"_{counter}"
        max_base_len = 31 - len(suffix)
        candidate = f"{base_name[:max_base_len]}{suffix}"
        counter += 1

    used_names.add(candidate)
    return candidate


def split_text_for_excel(text, max_chunk_size=5000):
    if not text:
        return [""]
    text = str(text)
    return [text[start:start + max_chunk_size] for start in range(0, len(text), max_chunk_size)]


def build_bill_text_sheet(details, latest_text_record, full_text):
    text_chunks = split_text_for_excel(full_text, max_chunk_size=5000)
    rows = []
    for i, chunk in enumerate(text_chunks, start=1):
        rows.append({
            "bill_id": details.get("bill_id") if i == 1 else "",
            "state": details.get("search_state") if i == 1 else "",
            "bill_number": details.get("bill_number") if i == 1 else "",
            "title": details.get("title") if i == 1 else "",
            "bill_text_date": latest_text_record.get("date") if i == 1 else "",
            "bill_text_type": latest_text_record.get("type") if i == 1 else "",
            "bill_text_mime": latest_text_record.get("mime") if i == 1 else "",
            "text_part": i,
            "full_bill_text": chunk
        })

    return pd.DataFrame(rows, columns=[
        "bill_id", "state", "bill_number", "title", "bill_text_date",
        "bill_text_type", "bill_text_mime", "text_part", "full_bill_text"
    ])


def apply_filter(bills, phrases):
    if not phrases:
        return bills

    filtered = []
    for bill in bills:
        title = bill.get("title", "").lower()
        desc = bill.get("description", "").lower()
        if any(phrase.lower() in title or phrase.lower() in desc for phrase in phrases):
            filtered.append(bill)
    return filtered


def bill_number_sort_key(bill):
    bill_number = str(bill.get("bill_number") or bill.get("number") or "").strip().upper()
    match = re.match(r"([A-Z]+)\s*0*([0-9]+)", bill_number)
    if match:
        prefix = match.group(1)
        number = int(match.group(2))
        return (prefix, number, bill_number)
    return (bill_number, float("inf"), bill_number)


def get_ai_priority_icon(priority_bucket):
    bucket = str(priority_bucket or "").strip().lower()
    if bucket == "high":
        return "🟢"
    if bucket == "medium":
        return "🟡"
    if bucket == "low":
        return "🟠"
    if bucket == "not relevant":
        return "🔴"
    return "⚪"


def build_bill_expander_label(bill, is_selected=False, context_suffix=""):
    bill_state = bill.get("search_state", "")
    bill_number = bill.get("bill_number") or bill.get("number") or "No Bill Number"
    bill_title = bill.get("title", "No Title")
    bill_status_code = bill.get("status")
    bill_status_label = BILL_STATUS_OPTIONS.get(bill_status_code, f"Status {bill_status_code}")
    short_title = shorten_text(bill_title, 85)

    score_prefix = ""
    if context_suffix == "display":
        ai_result = st.session_state.get("ai_scoring_results", {}).get(bill.get("bill_id"))
        if ai_result:
            score = ai_result.get("relevance_score", 0)
            bucket = ai_result.get("priority_bucket", "Not Relevant")
            score_prefix = f"{get_ai_priority_icon(bucket)} {bucket} {score}% | "
        else:
            score_prefix = "⚪ Not scored | "
    elif context_suffix == "cart":
        full_text_result = st.session_state.get("ai_full_text_results", {}).get(bill.get("bill_id"))
        if full_text_result:
            score = full_text_result.get("full_text_relevance_score", 0)
            bucket = full_text_result.get("full_text_priority_bucket", "Not Relevant")
            score_prefix = f"{get_ai_priority_icon(bucket)} {bucket} {score}% | "

    base_label = f"{score_prefix}{bill_state} | {bill_number} | {bill_status_label} | {short_title}"
    return f"✅ {base_label}" if is_selected else base_label


def sort_bills(bills, sort_option):
    if sort_option == "Original order":
        return list(bills)

    bills_copy = list(bills)

    if sort_option == "AI relevance score":
        ai_results = st.session_state.get("ai_scoring_results", {})

        def ai_sort_key(bill):
            result = ai_results.get(bill.get("bill_id"), {})
            score = result.get("relevance_score", -1)
            return (
                -score,
                str(bill.get("search_state", "")),
                bill_number_sort_key(bill)
            )

        return sorted(bills_copy, key=ai_sort_key)

    if sort_option == "Status":
        return sorted(
            bills_copy,
            key=lambda bill: (
                STATUS_SORT_PRIORITY.get(BILL_STATUS_OPTIONS.get(bill.get("status"), ""), 999),
                str(bill.get("search_state", "")),
                bill_number_sort_key(bill)
            )
        )

    if sort_option == "Bill number":
        return sorted(
            bills_copy,
            key=lambda bill: (str(bill.get("search_state", "")), bill_number_sort_key(bill))
        )

    if sort_option == "Title A–Z":
        return sorted(
            bills_copy,
            key=lambda bill: (str(bill.get("search_state", "")), str(bill.get("title") or "").lower())
        )

    return bills_copy


def get_status_filter_source():
    if st.session_state.precision_search_ran and st.session_state.third_layer_results:
        return st.session_state.third_layer_results
    if st.session_state.focus_search_ran and st.session_state.second_layer_results:
        return st.session_state.second_layer_results
    if st.session_state.general_search_ran and st.session_state.base_results:
        return st.session_state.base_results
    return []


def get_selected_bill_ids_in_current_results(bills):
    selected_ids = []
    for bill in bills:
        bill_id = bill.get("bill_id")
        if st.session_state.get(f"selected_bill_{bill_id}", False):
            selected_ids.append(bill_id)
    return selected_ids


def get_selected_bill_ids_global():
    selected_ids = []
    for key, value in st.session_state.items():
        if key.startswith("selected_bill_") and value is True:
            try:
                selected_ids.append(int(key.replace("selected_bill_", "")))
            except ValueError:
                pass
    return selected_ids


def paginate_bills(bills, per_page, current_page):
    total_results = len(bills)
    total_pages = max(1, (total_results + per_page - 1) // per_page) if total_results > 0 else 1
    current_page = min(current_page, total_pages)
    current_page = max(1, current_page)
    start_idx = (current_page - 1) * per_page
    end_idx = min(start_idx + per_page, total_results)
    page_bills = bills[start_idx:end_idx]
    return {
        "page_bills": page_bills,
        "total_results": total_results,
        "total_pages": total_pages,
        "current_page": current_page,
        "start_idx": start_idx,
        "end_idx": end_idx,
    }


@st.cache_data(ttl=86400)
def get_active_session(state, api_key):
    increment_api_counter("api_calls_session_lookup")
    url = f"https://api.legiscan.com/?key={api_key}&op=getSessionList&state={state}"
    response = requests.get(url)
    data = response.json()

    if data.get("status") != "OK":
        return None, None

    for session in data.get("sessions", []):
        if session.get("sine_die") == 0 and session.get("special") == 0:
            return session.get("session_id"), session.get("session_name")

    return None, None


@st.cache_data(ttl=86400)
def get_master_list(session_id, api_key):
    increment_api_counter("api_calls_bill_list_lookup")
    url = f"https://api.legiscan.com/?key={api_key}&op=getMasterList&id={session_id}"
    response = requests.get(url)
    data = response.json()

    if data.get("status") != "OK":
        return []

    masterlist = data.get("masterlist", {})
    bills = []
    for key, value in masterlist.items():
        if key != "session":
            bills.append(value)
    return bills


@st.cache_data(ttl=86400)
def get_bill_details(bill_id, api_key):
    increment_api_counter("api_calls_bill_details_lookup")
    url = f"https://api.legiscan.com/?key={api_key}&op=getBill&id={bill_id}"
    response = requests.get(url)
    data = response.json()

    if data.get("status") != "OK":
        return {}
    return data.get("bill", {})


@st.cache_data(ttl=86400)
def get_bill_text(doc_id, api_key):
    increment_api_counter("api_calls_bill_text_lookup")
    url = f"https://api.legiscan.com/?key={api_key}&op=getBillText&id={doc_id}"
    response = requests.get(url)
    data = response.json()

    if data.get("status") != "OK":
        return {}
    return data.get("text", {})


def get_latest_text_record(details, api_key):
    texts = details.get("texts") or []
    if not texts:
        return {}

    sorted_texts = sorted(texts, key=lambda x: (x.get("date") or "", x.get("doc_id") or 0))
    latest_text_meta = sorted_texts[-1]
    doc_id = latest_text_meta.get("doc_id")

    if not doc_id:
        return {}

    return get_bill_text(doc_id, api_key)


def extract_full_bill_text(text_record):
    if not text_record:
        return "[No bill text available]"

    encoded_doc = text_record.get("doc")
    mime_type = (text_record.get("mime") or "").lower()

    if not encoded_doc:
        return "[No bill text document returned]"

    try:
        decoded_bytes = base64.b64decode(encoded_doc)
    except Exception:
        return "[Unable to decode base64 bill document]"

    if "pdf" in mime_type:
        if PdfReader is None:
            return "[PDF text extraction unavailable: install pypdf with 'python3 -m pip install pypdf']"
        try:
            reader = PdfReader(BytesIO(decoded_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            extracted = "\n\n".join(pages).strip()
            return extracted if extracted else "[PDF returned but no readable text could be extracted]"
        except Exception:
            return "[Unable to extract text from PDF bill document]"

    if "html" in mime_type or "text" in mime_type or "xml" in mime_type:
        try:
            decoded_text = decoded_bytes.decode("utf-8", errors="ignore").strip()
            return decoded_text if decoded_text else "[Text document returned but empty after decoding]"
        except Exception:
            return "[Unable to decode text bill document]"

    return f"[Unsupported bill text format: {mime_type}]"


def build_export_package(export_sorted, include_full_text):
    output_data = []
    bill_text_sheets = {}
    used_sheet_names = set()

    for bill in export_sorted:
        details = get_bill_details(bill["bill_id"], API_KEY)
        details["search_state"] = bill.get("search_state", "")

        output_data.append({
            "bill_id": details.get("bill_id"),
            "state": bill.get("search_state", ""),
            "session_id": details.get("session_id"),
            "bill_number": details.get("bill_number"),
            "status": details.get("status"),
            "status_date": details.get("status_date"),
            "title": details.get("title"),
            "description": details.get("description"),
            "url": details.get("url"),
            "state_link": details.get("state_link")
        })

        if include_full_text:
            latest_text_record = get_latest_text_record(details, API_KEY)
            full_text = extract_full_bill_text(latest_text_record)

            bill_number_for_sheet = details.get("bill_number", f"bill_{details.get('bill_id')}")
            sheet_bill_number = f"{bill.get('search_state', '')}_{bill_number_for_sheet}"
            sheet_name = make_unique_sheet_name(str(sheet_bill_number), used_sheet_names)

            bill_text_sheets[sheet_name] = build_bill_text_sheet(
                details, latest_text_record, full_text
            )

    summary_df = pd.DataFrame(output_data, columns=[
        "bill_id", "state", "session_id", "bill_number", "status",
        "status_date", "title", "description", "url", "state_link"
    ])

    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        if include_full_text:
            for sheet_name, text_df in bill_text_sheets.items():
                text_df.to_excel(writer, sheet_name=sheet_name, index=False)

    excel_buffer.seek(0)
    return excel_buffer.getvalue(), len(export_sorted)


def update_bill_selection_from_widget(bill_id, context_suffix):
    widget_key = f"select_bill_widget_{bill_id}_{context_suffix}"
    selected_value = st.session_state.get(widget_key, False)
    st.session_state[f"selected_bill_{bill_id}"] = selected_value

    if context_suffix == "display":
        st.session_state["results_displayed_expanded"] = True
    elif context_suffix == "cart":
        st.session_state["results_cart_expanded"] = True


def render_bill_expander(bill, highlight_terms, context_suffix=""):
    bill_state = bill.get("search_state", "")
    bill_number = bill.get("bill_number") or bill.get("number") or "No Bill Number"
    bill_title = bill.get("title", "No Title")
    bill_desc = bill.get("description", "No Description")
    bill_id = bill.get("bill_id")
    bill_status_code = bill.get("status")
    bill_status_label = BILL_STATUS_OPTIONS.get(bill_status_code, f"Status {bill_status_code}")

    short_title = shorten_text(bill_title, 85)

    selected_key = f"selected_bill_{bill_id}"
    widget_key = f"select_bill_widget_{bill_id}_{context_suffix}"
    st.session_state[widget_key] = st.session_state.get(selected_key, False)

    text_checkbox_key = f"show_bill_text_{bill_id}_{context_suffix}" if context_suffix else f"show_bill_text_{bill_id}"

    is_selected = st.session_state.get(selected_key, False)
    expander_label = build_bill_expander_label(bill, is_selected=is_selected, context_suffix=context_suffix)

    with st.expander(expander_label, expanded=False):
        st.checkbox(
            f"Select {bill_state} {bill_number} for download",
            key=widget_key,
            on_change=update_bill_selection_from_widget,
            args=(bill_id, context_suffix),
        )
        st.caption("Expected API cost: 0 calls")

        st.markdown(f"**Jurisdiction:** {bill_state}")
        st.markdown(f"**Bill Status:** {bill_status_label}")

        st.markdown("**Title Preview**", unsafe_allow_html=True)
        st.markdown(
            highlight_keywords(bill_title, highlight_terms),
            unsafe_allow_html=True
        )

        st.markdown("**Description Preview**", unsafe_allow_html=True)
        st.markdown(
            highlight_keywords(bill_desc, highlight_terms),
            unsafe_allow_html=True
        )

        ai_result = st.session_state.get("ai_scoring_results", {}).get(bill_id)
        if context_suffix == "display" and ai_result:
            st.markdown("**Title/Description AI Assessment**")
            st.caption(f"Provider used: {st.session_state.get('ai_provider', 'Mock')}")
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric("Relevance", f"{ai_result.get('relevance_score', 0)}%")
            with metric_col2:
                st.metric("Priority", ai_result.get("priority_bucket", "N/A"))
            with metric_col3:
                st.metric("Confidence", ai_result.get("confidence", "N/A"))

            st.markdown(f"**Recommendation:** {ai_result.get('include_recommendation', 'N/A')}")

            reasoning = ai_result.get("reasoning", [])
            if reasoning:
                st.markdown("**Why AI flagged this**")
                for reason in reasoning:
                    st.markdown(f"- {reason}")

            ambiguity_flags = ai_result.get("ambiguity_flags", [])
            if ambiguity_flags:
                st.markdown("**Ambiguity flags**")
                for flag in ambiguity_flags:
                    st.markdown(f"- {flag}")

        if context_suffix == "cart":
            full_text_result = st.session_state.get("ai_full_text_results", {}).get(bill_id)
            if full_text_result:
                st.markdown("**Full-Text AI Assessment**")
                ft_col1, ft_col2, ft_col3 = st.columns(3)
                with ft_col1:
                    st.metric("Full-Text Relevance", f"{full_text_result.get('full_text_relevance_score', 0)}%")
                with ft_col2:
                    st.metric("Priority", full_text_result.get("full_text_priority_bucket", "N/A"))
                with ft_col3:
                    st.metric("Confidence", full_text_result.get("full_text_confidence", "N/A"))

                st.markdown(f"**Recommendation:** {full_text_result.get('full_text_include_recommendation', 'N/A')}")

                key_provisions = full_text_result.get("key_provisions_summary", [])
                if key_provisions:
                    st.markdown("**Key Provisions Summary**")
                    for item in key_provisions:
                        st.markdown(f"- {item}")

                topics = full_text_result.get("tenant_protection_topics", [])
                if topics:
                    st.markdown("**Tenant Protection Topics**")
                    st.markdown(", ".join(topics))

                full_text_reasoning = full_text_result.get("full_text_reasoning", [])
                if full_text_reasoning:
                    st.markdown("**Why AI flagged this**")
                    for reason in full_text_reasoning:
                        st.markdown(f"- {reason}")

                full_text_ambiguity = full_text_result.get("full_text_ambiguity_flags", [])
                if full_text_ambiguity:
                    st.markdown("**Ambiguity flags**")
                    for flag in full_text_ambiguity:
                        st.markdown(f"- {flag}")

                manual_review_points = full_text_result.get("manual_review_points", [])
                if manual_review_points:
                    st.markdown("**Manual review points**")
                    for item in manual_review_points:
                        st.markdown(f"- {item}")
                else:
                    st.markdown("**Manual review points:** None")

        show_text = st.checkbox(
            f"Show bill text for {bill_state} {bill_number}",
            key=text_checkbox_key
        )
        st.caption("Expected API cost: up to 2 calls (1 bill details lookup + 1 bill text lookup)")

        if show_text:
            details = get_bill_details(bill_id, API_KEY)
            latest_text_record = get_latest_text_record(details, API_KEY)
            full_text = extract_full_bill_text(latest_text_record)
            bill_text_date = latest_text_record.get("date", "Unknown date")

            st.markdown("**Bill Text Metadata**")
            st.markdown(f"- Bill text date: {bill_text_date}")
            st.markdown(f"- Bill text type: {latest_text_record.get('type', 'Unknown')}")
            st.markdown(f"- Bill text mime: {latest_text_record.get('mime', 'Unknown')}")

            st.text_area(
                label=f"Bill text for {bill_state} {bill_number}",
                value=full_text,
                height=500,
                key=f"bill_text_viewer_{bill_id}_{context_suffix}" if context_suffix else f"bill_text_viewer_{bill_id}"
            )


def run_general_search():
    reset_all_pagination()
    st.session_state.general_search_ran = True
    st.session_state.focus_search_ran = False
    st.session_state.precision_search_ran = False
    st.session_state.status_filter_ran = False

    st.session_state.bills = []
    st.session_state.base_results = []
    st.session_state.second_layer_results = []
    st.session_state.third_layer_results = []
    st.session_state.status_filtered_results = []
    st.session_state.prepared_export_data = None
    st.session_state.prepared_export_count = 0
    clear_ai_scores()
    st.session_state.results_displayed_expanded = False
    st.session_state.results_cart_expanded = False

    selected_jurisdictions = get_active_jurisdictions()
    first_keywords = parse_keywords(st.session_state.get("first_filter_text", ""))

    if not selected_jurisdictions:
        st.session_state["ui_message_type"] = "warning"
        st.session_state["ui_message_text"] = "Please enter at least one valid jurisdiction, or use the nationwide option."
        return

    combined_bills = []
    jurisdictions_with_active_sessions = []
    jurisdictions_without_active_sessions = []

    for jurisdiction in selected_jurisdictions:
        session_id, session_name = get_active_session(jurisdiction, API_KEY)

        if not session_id:
            jurisdictions_without_active_sessions.append(jurisdiction)
            continue

        display_name = JURISDICTION_OPTIONS.get(jurisdiction, jurisdiction)
        jurisdictions_with_active_sessions.append(f"{jurisdiction} ({display_name} — {session_name})")
        jurisdiction_bills = get_master_list(session_id, API_KEY)

        for bill in jurisdiction_bills:
            bill["search_state"] = jurisdiction

        combined_bills.extend(jurisdiction_bills)

    deduped_bills = []
    seen_bill_ids = set()
    for bill in combined_bills:
        bill_id = bill.get("bill_id")
        if bill_id not in seen_bill_ids:
            deduped_bills.append(bill)
            seen_bill_ids.add(bill_id)

    filtered = apply_filter(deduped_bills, first_keywords)

    st.session_state.base_results = filtered
    st.session_state.bills = filtered

    if jurisdictions_with_active_sessions and jurisdictions_without_active_sessions:
        st.session_state["ui_message_type"] = "info"
        st.session_state["ui_message_text"] = (
            f"Using active sessions for: {', '.join(jurisdictions_with_active_sessions)}. "
            f"No active regular session found for: {', '.join(jurisdictions_without_active_sessions)}."
        )
    elif jurisdictions_with_active_sessions:
        st.session_state["ui_message_type"] = "success"
        st.session_state["ui_message_text"] = (
            f"Using active sessions for: {', '.join(jurisdictions_with_active_sessions)}"
        )
    else:
        st.session_state["ui_message_type"] = "error"
        st.session_state["ui_message_text"] = "No active regular sessions found for the selected jurisdictions."


def run_focus_search():
    if not st.session_state.base_results:
        st.session_state["ui_message_type"] = "warning"
        st.session_state["ui_message_text"] = "Run the General Search first."
        return

    reset_all_pagination()
    st.session_state.focus_search_ran = True
    st.session_state.precision_search_ran = False
    st.session_state.status_filter_ran = False
    st.session_state.prepared_export_data = None
    st.session_state.prepared_export_count = 0
    clear_ai_scores()
    st.session_state.results_displayed_expanded = False
    st.session_state.results_cart_expanded = False

    second_keywords = parse_keywords(st.session_state.get("second_filter_text", ""))
    second_filtered = apply_filter(st.session_state.base_results, second_keywords)

    st.session_state.second_layer_results = second_filtered
    st.session_state.third_layer_results = []
    st.session_state.status_filtered_results = []
    st.session_state.bills = second_filtered
    st.session_state["ui_message_type"] = "info"
    st.session_state["ui_message_text"] = "Focus Search applied."


def run_precision_search():
    if not st.session_state.second_layer_results:
        st.session_state["ui_message_type"] = "warning"
        st.session_state["ui_message_text"] = "Run the Focus Search first."
        return

    reset_all_pagination()
    st.session_state.precision_search_ran = True
    st.session_state.status_filter_ran = False
    st.session_state.prepared_export_data = None
    st.session_state.prepared_export_count = 0
    clear_ai_scores()
    st.session_state.results_displayed_expanded = False
    st.session_state.results_cart_expanded = False

    third_keywords = parse_keywords(st.session_state.get("third_filter_text", ""))
    third_filtered = apply_filter(st.session_state.second_layer_results, third_keywords)

    st.session_state.third_layer_results = third_filtered
    st.session_state.status_filtered_results = []
    st.session_state.bills = third_filtered
    st.session_state["ui_message_type"] = "info"
    st.session_state["ui_message_text"] = "Precision Search applied."


def run_status_search():
    source_bills = get_status_filter_source()
    if not source_bills:
        st.session_state["ui_message_type"] = "warning"
        st.session_state["ui_message_text"] = "Run the General Search first."
        return

    reset_all_pagination()
    st.session_state.status_filter_ran = True
    st.session_state.prepared_export_data = None
    st.session_state.prepared_export_count = 0
    clear_ai_scores()
    st.session_state.results_displayed_expanded = False
    st.session_state.results_cart_expanded = False

    selected_status_labels = st.session_state.get("selected_status_labels", [])
    status_filtered = apply_status_filter(source_bills, selected_status_labels)
    st.session_state.status_filtered_results = status_filtered
    st.session_state.bills = status_filtered
    st.session_state["ui_message_type"] = "info"
    st.session_state["ui_message_text"] = "Bill Status filter applied."


left_col, right_col = st.columns([4, 1], gap="large")

with left_col:
    all_mode_active = st.session_state.get("all_jurisdictions_mode", False)

    st.text_input(
        "Select jurisdiction(s) (comma separated codes or names)",
        key="jurisdiction_text",
        placeholder="Example: NY, CA, US",
        disabled=all_mode_active
    )

    current_jurisdictions = get_active_jurisdictions()

    with st.expander("Jurisdiction Options", expanded=st.session_state.open_jurisdiction_expander):
        st.caption("Click a jurisdiction to add or remove it from the field above, or use subgroup actions.")

        for region_name, subgroups in JURISDICTION_GROUPS.items():
            region_codes = [code for subgroup_codes in subgroups.values() for code in subgroup_codes]
            region_selected_count = sum(1 for code in region_codes if code in current_jurisdictions)
            region_total_count = len(region_codes)
            region_prefix = "✅ " if region_selected_count > 0 else ""

            with st.expander(f"{region_prefix}{region_name} ({region_selected_count}/{region_total_count})", expanded=False):
                for subgroup_name, codes in subgroups.items():
                    subgroup_selected_count = sum(1 for code in codes if code in current_jurisdictions)
                    subgroup_total_count = len(codes)
                    subgroup_prefix = "✅ " if subgroup_selected_count > 0 else ""

                    with st.expander(f"{subgroup_prefix}{subgroup_name} ({subgroup_selected_count}/{subgroup_total_count})", expanded=False):
                        action_col1, action_col2, action_col3 = st.columns([1.1, 1.1, 2.3])
                        with action_col1:
                            st.button(
                                "Select All",
                                key=f"select_all_{region_name}_{subgroup_name}",
                                on_click=add_jurisdiction_group,
                                args=(codes,),
                                use_container_width=True
                            )
                        with action_col2:
                            st.button(
                                "Deselect All",
                                key=f"deselect_all_{region_name}_{subgroup_name}",
                                on_click=remove_jurisdiction_group,
                                args=(codes,),
                                use_container_width=True
                            )
                        with action_col3:
                            st.caption(f"Manage all jurisdictions in {subgroup_name}")

                        cols = st.columns(2)
                        for idx, code in enumerate(codes):
                            with cols[idx % 2]:
                                name = JURISDICTION_OPTIONS[code]
                                is_selected = code in current_jurisdictions
                                button_label = f"✅ {code} — {name}" if is_selected else f"{code} — {name}"
                                st.button(
                                    button_label,
                                    key=f"jurisdiction_option_{region_name}_{subgroup_name}_{code}",
                                    on_click=toggle_jurisdiction,
                                    args=(code,),
                                    use_container_width=True,
                                    disabled=all_mode_active
                                )

        clear_jur_col1, clear_jur_col2 = st.columns([1.4, 3])
        with clear_jur_col1:
            st.button(
                "Clear All Selected Jurisdictions",
                on_click=clear_all_selected_jurisdictions,
                use_container_width=True,
                key="clear_all_selected_jurisdictions_button"
            )
        with clear_jur_col2:
            st.caption("Remove every manually selected jurisdiction and re-enable custom selection.")

    top_jur_col1, top_jur_col2 = st.columns([2.2, 3])
    with top_jur_col1:
        st.button(
            "Search All 50 States, Washington, D.C., and U.S. Congress",
            on_click=activate_all_jurisdictions_mode,
            use_container_width=True,
            key="activate_all_jurisdictions_mode_button"
        )
        st.caption("Expected API cost: up to 104 calls")
    with top_jur_col2:
        if all_mode_active:
            st.success("Nationwide jurisdiction mode is active.")
        else:
            st.caption("Use this to search across every state plus D.C. and Congress.")

    SELECTED_JURISDICTIONS = current_jurisdictions

    st.markdown("### General Search")
    first_filter_input = st.text_input(
        "Enter general search keywords (comma separated)",
        key="first_filter_text",
        on_change=run_general_search
    )
    FIRST_FILTER_KEYWORDS = parse_keywords(first_filter_input)
    st.caption("Click a suggested keyword to add or remove it from the General Search box.")

    selected_layer1_keywords = parse_keywords(st.session_state.first_filter_text)

    for category, phrases in LAYER_1_KEYWORD_CATEGORIES.items():
        selected_count, total_count = get_category_selection_status(phrases, st.session_state.first_filter_text)
        prefix = "✅ " if selected_count > 0 else ""
        expander_label = f"{prefix}{category} ({selected_count}/{total_count})"
        keep_open = st.session_state.open_layer1_category == category

        with st.expander(expander_label, expanded=keep_open):
            cols = st.columns(2)
            for idx, phrase in enumerate(phrases):
                with cols[idx % 2]:
                    is_selected = phrase.lower() in selected_layer1_keywords
                    button_label = f"✅ {phrase}" if is_selected else phrase
                    st.button(
                        button_label,
                        key=f"layer1_filter_{category}_{phrase}",
                        on_click=toggle_first_filter_keyword,
                        args=(phrase, category)
                    )

    st.button("Run General Search", on_click=run_general_search)
    st.caption("Expected API cost: 2 calls per selected jurisdiction (1 session lookup + 1 bill list lookup)")

    st.markdown("### Focus Search")
    second_filter_input = st.text_input(
        "Enter focus search keywords to narrow the results (comma separated)",
        key="second_filter_text",
        on_change=run_focus_search
    )
    SECOND_FILTER_KEYWORDS = parse_keywords(second_filter_input)

    with st.expander("Focus Search Suggested Keywords", expanded=st.session_state.open_focus_outer):
        st.caption("Click a suggested keyword to add or remove it from the Focus Search box.")
        selected_layer2_keywords = parse_keywords(st.session_state.second_filter_text)

        for category, phrases in LAYER_2_KEYWORD_CATEGORIES.items():
            selected_count, total_count = get_category_selection_status(phrases, st.session_state.second_filter_text)
            prefix = "✅ " if selected_count > 0 else ""
            expander_label = f"{prefix}{category} ({selected_count}/{total_count})"
            keep_open = st.session_state.open_layer2_category == category

            with st.expander(expander_label, expanded=keep_open):
                cols = st.columns(2)
                for idx, phrase in enumerate(phrases):
                    with cols[idx % 2]:
                        is_selected = phrase.lower() in selected_layer2_keywords
                        button_label = f"✅ {phrase}" if is_selected else phrase
                        st.button(
                            button_label,
                            key=f"layer2_filter_{category}_{phrase}",
                            on_click=toggle_second_filter_keyword,
                            args=(phrase, category)
                        )

    st.button("Run Focus Search", on_click=run_focus_search)
    st.caption("Expected API cost: 0 calls (local filtering only)")

    st.markdown("### Precision Search")
    third_filter_input = st.text_input(
        "Enter precision search keywords to refine the results further (comma separated)",
        key="third_filter_text",
        on_change=run_precision_search
    )
    THIRD_FILTER_KEYWORDS = parse_keywords(third_filter_input)

    with st.expander("Precision Search Suggested Keywords", expanded=st.session_state.open_precision_outer):
        st.caption("Click a suggested keyword to add or remove it from the Precision Search box.")
        selected_layer3_keywords = parse_keywords(st.session_state.third_filter_text)

        for category, phrases in LAYER_3_KEYWORD_CATEGORIES.items():
            selected_count, total_count = get_category_selection_status(phrases, st.session_state.third_filter_text)
            prefix = "✅ " if selected_count > 0 else ""
            expander_label = f"{prefix}{category} ({selected_count}/{total_count})"
            keep_open = st.session_state.open_layer3_category == category

            with st.expander(expander_label, expanded=keep_open):
                cols = st.columns(2)
                for idx, phrase in enumerate(phrases):
                    with cols[idx % 2]:
                        is_selected = phrase.lower() in selected_layer3_keywords
                        button_label = f"✅ {phrase}" if is_selected else phrase
                        st.button(
                            button_label,
                            key=f"layer3_filter_{category}_{phrase}",
                            on_click=toggle_third_filter_keyword,
                            args=(phrase, category)
                        )

    st.button("Run Precision Search", on_click=run_precision_search)
    st.caption("Expected API cost: 0 calls (local filtering only)")

    st.markdown("### Bill Status")
    st.pills(
        "Select bill statuses to filter results",
        options=list(BILL_STATUS_OPTIONS.values()),
        default=st.session_state.selected_status_labels,
        selection_mode="multi",
        key="selected_status_labels",
    )

    st.button("Run Bill Status Filter", on_click=run_status_search)
    st.caption("Expected API cost: 0 calls (local filtering only)")

    st.button("Clear Filters and Results", on_click=clear_filters_and_results)

    if st.session_state["ui_message_text"]:
        message_type = st.session_state.get("ui_message_type", "info")
        message_text = st.session_state.get("ui_message_text", "")

        if message_type == "success":
            st.success(message_text)
        elif message_type == "warning":
            st.warning(message_text)
        elif message_type == "error":
            st.error(message_text)
        else:
            st.info(message_text)

    highlight_terms = FIRST_FILTER_KEYWORDS + SECOND_FILTER_KEYWORDS + THIRD_FILTER_KEYWORDS

    selected_bill_ids = set(get_selected_bill_ids_in_current_results(st.session_state.bills))
    selected_bill_ids_global = set(get_selected_bill_ids_global())

    display_pool = [bill for bill in st.session_state.bills if bill.get("bill_id") not in selected_bill_ids]
    cart_pool = [bill for bill in st.session_state.bills if bill.get("bill_id") in selected_bill_ids]

    display_pool_filtered = filter_bills_by_ai_score(display_pool)
    display_sorted = sort_bills(display_pool_filtered, st.session_state.display_sort_option)
    cart_sorted = sort_bills(cart_pool, st.session_state.cart_sort_option)

    display_page = paginate_bills(
        display_sorted,
        int(st.session_state.display_results_per_page),
        st.session_state.display_current_page
    )
    st.session_state.display_current_page = display_page["current_page"]

    cart_page = paginate_bills(
        cart_sorted,
        int(st.session_state.cart_results_per_page),
        st.session_state.cart_current_page
    )
    st.session_state.cart_current_page = cart_page["current_page"]

    st.markdown("### Selection Summary")
    summary_col1, summary_col2 = st.columns([1, 1])
    with summary_col1:
        st.metric("Selected bills", len(selected_bill_ids_global))
    with summary_col2:
        st.metric("Current displayed results", len(display_pool_filtered))

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        st.markdown("**General Search**")
        st.caption(format_filter_value(FIRST_FILTER_KEYWORDS))
    with filter_col2:
        st.markdown("**Focus Search**")
        st.caption(format_filter_value(SECOND_FILTER_KEYWORDS))
    with filter_col3:
        st.markdown("**Precision Search**")
        st.caption(format_filter_value(THIRD_FILTER_KEYWORDS))
    with filter_col4:
        st.markdown("**Bill Status**")
        st.caption(format_filter_value(st.session_state.selected_status_labels))

    st.markdown("### AI Scoring Summary")
    if st.session_state.get("ai_scoring_ran", False):
        ai_summary_col1, ai_summary_col2 = st.columns([1, 1])
        with ai_summary_col1:
            st.metric("Bills scored", st.session_state.get("ai_last_scored_count", 0))
        with ai_summary_col2:
            st.metric("Minimum score filter", st.session_state.get("ai_score_threshold", 0))
    else:
        st.caption("AI relevance scoring has not been run yet.")

    st.markdown("### Results")

    with st.expander(
        f"Displayed Bills ({len(display_pool_filtered)})",
        expanded=st.session_state.results_displayed_expanded
    ):
        controls_col1, controls_col2 = st.columns([6, 3], gap="small")
        with controls_col1:
            st.pills(
                "Sort results by",
                options=SORT_OPTIONS,
                default=st.session_state.display_sort_option,
                selection_mode="single",
                key="display_sort_option",
            )
        with controls_col2:
            st.markdown(
                """
                <style>
                .results-per-page-center-display label {
                    text-align: center !important;
                    width: 100%;
                    display: block;
                }
                </style>
                <div class="results-per-page-center-display">
                """,
                unsafe_allow_html=True,
            )
            st.pills(
                "Results per page",
                options=RESULTS_PER_PAGE_OPTIONS,
                default=st.session_state.display_results_per_page,
                selection_mode="single",
                key="display_results_per_page",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("#### AI Relevance Scoring")
        st.text_area(
            "Tenant protections relevance definition",
            key="tenant_relevance_definition",
            height=180,
            help="This definition is pre-filled but can be edited before running AI scoring."
        )

        provider_col1, provider_col2, provider_col3 = st.columns([1, 1.4, 1.2])
        with provider_col1:
            st.selectbox(
                "Scoring provider",
                options=["Mock", "Ollama"],
                key="ai_provider"
            )
        with provider_col2:
            if st.session_state.ai_provider == "Ollama":
                st.text_input(
                    "Ollama base URL",
                    key="ollama_base_url",
                    help="Default local Ollama API URL."
                )
            else:
                st.text_input(
                    "Ollama base URL",
                    key="ollama_base_url",
                    disabled=True
                )
        with provider_col3:
            if st.session_state.ai_provider == "Ollama":
                st.text_input(
                    "Ollama model name",
                    key="ollama_model_name",
                    help="Example: gemma3"
                )
            else:
                st.text_input(
                    "Ollama model name",
                    key="ollama_model_name",
                    disabled=True
                )

        ai_col1, ai_col2, ai_col3 = st.columns([1.4, 1, 1.2])
        with ai_col1:
            score_displayed_clicked = st.button(
                "Score All Displayed Bills",
                use_container_width=True,
                key="score_all_displayed_bills_button"
            )
        with ai_col2:
            st.number_input(
                "Minimum score",
                min_value=0,
                max_value=100,
                step=5,
                key="ai_score_threshold"
            )
        with ai_col3:
            st.checkbox(
                "Show only bills above minimum score",
                key="ai_show_only_above_threshold"
            )

        if st.session_state.ai_provider == "Ollama":
            st.caption("Ollama runs locally on your machine. Scoring speed depends on your local model and hardware.")
        else:
            st.caption("Mock scoring uses keyword-based rules so you can compare non-LLM scoring against Ollama results.")

        if score_displayed_clicked:
            if not display_pool:
                st.session_state["ui_message_type"] = "warning"
                st.session_state["ui_message_text"] = "No displayed bills available to score."
            elif st.session_state.ai_provider == "Ollama" and (not st.session_state.ollama_base_url.strip() or not st.session_state.ollama_model_name.strip()):
                st.session_state["ui_message_type"] = "warning"
                st.session_state["ui_message_text"] = "Enter both an Ollama base URL and model name before scoring with Ollama."
            else:
                start_time = time.perf_counter()
                if st.session_state.ai_provider == "Ollama":
                    with st.spinner("Scoring displayed bills with Ollama...", show_time=True):
                        run_ai_scoring_on_displayed_bills(display_pool)
                else:
                    run_ai_scoring_on_displayed_bills(display_pool)
                st.session_state["ollama_display_last_run_seconds"] = round(time.perf_counter() - start_time, 2) if st.session_state.ai_provider == "Ollama" else st.session_state.get("ollama_display_last_run_seconds")
                st.session_state["results_displayed_expanded"] = True

        st.subheader(f"Displayed bills: {len(display_pool_filtered)}")
        if display_page["total_results"] > 0:
            st.write("Preview the matching bills below:")
            for bill in display_page["page_bills"]:
                render_bill_expander(bill, highlight_terms, context_suffix="display")
        else:
            st.caption("No displayed bills yet.")

        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            st.button(
                "Previous",
                on_click=go_previous_display_page,
                disabled=display_page["current_page"] == 1,
                use_container_width=True,
                key="display_prev"
            )
        with nav_col2:
            if display_page["total_results"] > 0:
                show_text = f"Showing {display_page['start_idx'] + 1}-{display_page['end_idx']} of {display_page['total_results']} bills"
            else:
                show_text = "No bills to display"
            st.markdown(
                f"<div style='text-align:center; padding-top:0.4rem;'>"
                f"{show_text}<br>"
                f"Page {display_page['current_page']} of {display_page['total_pages']}"
                f"</div>",
                unsafe_allow_html=True,
            )
        with nav_col3:
            st.button(
                "Next",
                on_click=go_next_display_page,
                args=(display_page["total_pages"],),
                disabled=display_page["current_page"] == display_page["total_pages"],
                use_container_width=True,
                key="display_next"
            )

    with st.expander(
        f"Download Cart ({len(cart_pool)})",
        expanded=st.session_state.results_cart_expanded
    ):
        cart_controls_col1, cart_controls_col2 = st.columns([6, 3], gap="small")
        with cart_controls_col1:
            st.pills(
                "Sort results by",
                options=SORT_OPTIONS,
                default=st.session_state.cart_sort_option,
                selection_mode="single",
                key="cart_sort_option",
            )
        with cart_controls_col2:
            st.markdown(
                """
                <style>
                .results-per-page-center-cart label {
                    text-align: center !important;
                    width: 100%;
                    display: block;
                }
                </style>
                <div class="results-per-page-center-cart">
                """,
                unsafe_allow_html=True,
            )
            st.pills(
                "Results per page",
                options=RESULTS_PER_PAGE_OPTIONS,
                default=st.session_state.cart_results_per_page,
                selection_mode="single",
                key="cart_results_per_page",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        clear_col1, clear_col2 = st.columns([1.5, 3])
        with clear_col1:
            st.button(
                "Clear Selected Bills",
                on_click=clear_selected_bills,
                use_container_width=True,
                key="clear_selected_bills_button"
            )
        with clear_col2:
            st.markdown(f"**{len(selected_bill_ids_global)} bill(s) currently selected**")

        full_text_col1, full_text_col2 = st.columns([1.8, 3], gap="small")
        with full_text_col1:
            run_full_text_clicked = st.button(
                "Run Full-Text AI Review for Download Cart",
                use_container_width=True,
                key="run_full_text_ai_review_button"
            )
        with full_text_col2:
            st.markdown(f"**{len(cart_pool)} bill(s) currently in the full-text review queue**")

        st.caption("Expected LegiScan API cost: up to 2 calls per selected bill for full-text retrieval.")
        if st.session_state.ai_provider == "Ollama":
            st.caption("Expected AI cost: local Ollama runtime only. Full-text review may take noticeably longer than title/description scoring.")
        else:
            st.caption("Mock full-text review uses keyword-based rules so you can compare non-LLM review against Ollama results.")

        if run_full_text_clicked:
            if not cart_pool:
                st.session_state["ui_message_type"] = "warning"
                st.session_state["ui_message_text"] = "No bills are currently in the Download Cart for full-text AI review."
            elif st.session_state.ai_provider == "Ollama" and (not st.session_state.ollama_base_url.strip() or not st.session_state.ollama_model_name.strip()):
                st.session_state["ui_message_type"] = "warning"
                st.session_state["ui_message_text"] = "Enter both an Ollama base URL and model name before running full-text AI review."
            else:
                start_time = time.perf_counter()
                if st.session_state.ai_provider == "Ollama":
                    with st.spinner("Running full-text AI review for download cart with Ollama...", show_time=True):
                        run_full_text_ai_review_on_cart(cart_pool)
                else:
                    run_full_text_ai_review_on_cart(cart_pool)
                st.session_state["ollama_full_text_last_run_seconds"] = round(time.perf_counter() - start_time, 2) if st.session_state.ai_provider == "Ollama" else st.session_state.get("ollama_full_text_last_run_seconds")
                st.session_state["results_cart_expanded"] = True

        st.subheader(f"Bills in cart: {len(cart_pool)}")

        if cart_page["total_results"] > 0:
            st.write("Review the selected bills below:")

            for bill in cart_page["page_bills"]:
                render_bill_expander(bill, highlight_terms, context_suffix="cart")

            cart_nav_col1, cart_nav_col2, cart_nav_col3 = st.columns([1, 2, 1])
            with cart_nav_col1:
                st.button(
                    "Previous",
                    on_click=go_previous_cart_page,
                    disabled=cart_page["current_page"] == 1,
                    use_container_width=True,
                    key="cart_prev"
                )
            with cart_nav_col2:
                cart_show_text = f"Showing {cart_page['start_idx'] + 1}-{cart_page['end_idx']} of {cart_page['total_results']} bills"
                st.markdown(
                    f"<div style='text-align:center; padding-top:0.4rem;'>"
                    f"{cart_show_text}<br>"
                    f"Page {cart_page['current_page']} of {cart_page['total_pages']}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with cart_nav_col3:
                st.button(
                    "Next",
                    on_click=go_next_cart_page,
                    args=(cart_page["total_pages"],),
                    disabled=cart_page["current_page"] == cart_page["total_pages"],
                    use_container_width=True,
                    key="cart_next"
                )
        else:
            st.caption("No bills in the cart yet.")

    st.markdown("### Export")

    include_full_text = st.checkbox("Include full bill text as separate Excel tabs for selected bills")

    if include_full_text:
        st.caption("Expected API cost for export: up to 2 calls per selected bill")
    else:
        st.caption("Expected API cost for export: up to 1 call per selected bill")

    export_selected_ids = get_selected_bill_ids_in_current_results(st.session_state.bills)
    export_selected_set = set(export_selected_ids)
    export_sorted = sort_bills(
        [bill for bill in st.session_state.bills if bill.get("bill_id") in export_selected_set],
        st.session_state.cart_sort_option
    )

    prepare_col1, prepare_col2 = st.columns([1.3, 2], gap="small")
    with prepare_col1:
        prepare_clicked = st.button("Prepare Selected Bill Information", use_container_width=True)
    with prepare_col2:
        st.markdown(f"**{len(export_sorted)} bill(s) queued for export**")

    if prepare_clicked:
        if export_sorted:
            prepared_bytes, prepared_count = build_export_package(export_sorted, include_full_text)
            st.session_state.prepared_export_data = prepared_bytes
            st.session_state.prepared_export_count = prepared_count
        else:
            st.session_state.prepared_export_data = None
            st.session_state.prepared_export_count = 0

    download_col1, download_col2 = st.columns([1.3, 2], gap="small")
    with download_col1:
        st.download_button(
            label="Download Excel File",
            data=st.session_state.prepared_export_data or b"",
            file_name="selected_bill_details.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            disabled=st.session_state.prepared_export_data is None,
            use_container_width=True,
        )
    with download_col2:
        st.markdown(f"**{st.session_state.prepared_export_count} bill(s) in current export file**")

with right_col:
    st.markdown("### Search Status")

    if st.session_state.general_search_ran:
        st.metric("General Search", len(st.session_state.base_results))
    else:
        st.caption("General Search has not been run yet.")

    if st.session_state.focus_search_ran:
        st.metric("Focus Search", len(st.session_state.second_layer_results))
    else:
        st.caption("Run Focus Search to narrow the results.")

    if st.session_state.precision_search_ran:
        st.metric("Precision Search", len(st.session_state.third_layer_results))
    else:
        st.caption("Run Precision Search to refine the results.")

    if st.session_state.status_filter_ran:
        st.metric("Bill Status", len(st.session_state.status_filtered_results))
    else:
        st.caption("Run Bill Status to filter by legislative status.")

    st.markdown("---")
    st.markdown("### Current Filters")
    if st.session_state.get("all_jurisdictions_mode", False):
        st.markdown("**Jurisdictions:** All 50 states, Washington, D.C., and U.S. Congress")
    else:
        st.markdown(f"**Jurisdictions:** {format_filter_value(SELECTED_JURISDICTIONS)}")
    st.markdown(f"**General Search:** {format_filter_value(FIRST_FILTER_KEYWORDS)}")
    st.markdown(f"**Focus Search:** {format_filter_value(SECOND_FILTER_KEYWORDS)}")
    st.markdown(f"**Precision Search:** {format_filter_value(THIRD_FILTER_KEYWORDS)}")
    st.markdown(f"**Bill Status:** {format_filter_value(st.session_state.selected_status_labels)}")

    st.markdown("---")
    st.markdown("### API Calls")
    st.metric("Total API calls", st.session_state.api_total_calls)
    st.metric("Session lookup", st.session_state.api_calls_session_lookup)
    st.metric("Bill list lookup", st.session_state.api_calls_bill_list_lookup)
    st.metric("Bill details lookup", st.session_state.api_calls_bill_details_lookup)
    st.metric("Bill text lookup", st.session_state.api_calls_bill_text_lookup)

    st.markdown("#### Ollama Timers")
    display_time = st.session_state.get("ollama_display_last_run_seconds")
    full_text_time = st.session_state.get("ollama_full_text_last_run_seconds")
    timer_col1, timer_col2 = st.columns(2)
    with timer_col1:
        st.markdown("**Pass 1 Review**")
        if display_time is None:
            st.caption("Not run yet")
        else:
            st.markdown(f"<div style='font-size:1.4rem; font-weight:600; line-height:1.1;'>{display_time:.2f} sec</div>", unsafe_allow_html=True)
    with timer_col2:
        st.markdown("**Pass 2 Review**")
        if full_text_time is None:
            st.caption("Not run yet")
        else:
            st.markdown(f"<div style='font-size:1.4rem; font-weight:600; line-height:1.1;'>{full_text_time:.2f} sec</div>", unsafe_allow_html=True)
