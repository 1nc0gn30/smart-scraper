"""
StreamlitNetlifyCollab — Streamlit Dashboard (companion)

This demonstrates how the exact same Python logic that powers the Netlify + FastAPI flow
can be consumed directly inside a beautiful Streamlit interface.

Great for:
- Internal data teams
- Analysts who prefer notebooks / Streamlit
- Rapid prototyping new analysis tasks

Run locally:
    cd streamlit-app
    pip install -r requirements.txt
    streamlit run app.py

You can point it at the same deployed FastAPI, or run everything locally.
"""

import os
import sys
import json
from pathlib import Path

import streamlit as st
import pandas as pd
import requests

# Robust import for the shared scraper.py
# Priority:
# 1. scraper.py next to this app.py (best for standalone deploys + docker)
# 2. python-backend sibling (monorepo local dev)
# 3. Common container paths
here = Path(__file__).resolve().parent

candidates = [
    here,                              # scraper.py next to app.py (standalone / copied)
    here.parent / "python-backend",    # ../python-backend/ (repo checkout)
    Path("/app"),                      # container root
    Path("/app/python-backend"),
]

scraper_path = None
for cand in candidates:
    if (cand / "scraper.py").is_file():
        if str(cand) not in sys.path:
            sys.path.insert(0, str(cand))
        scraper_path = cand / "scraper.py"
        break

try:
    from scraper import (
        scrape_and_analyze,
        SUPPORTED_TASKS,
        SUPPORTED_MODES,
        result_to_dataframe,
    )
except Exception as import_err:
    st.error(
        "❌ Could not import the shared scraper module.\n\n"
        "Make sure `scraper.py` is present next to app.py or in ../python-backend/.\n"
        "For Docker/standalone builds, the scraper must be copied into the image."
    )
    st.exception(import_err)
    st.stop()

st.set_page_config(
    page_title="StreamlitNetlifyCollab • Smart Scraper",
    page_icon="🧠",
    layout="wide",
)

st.title("Smart Scraper — Streamlit Edition")
st.caption("Same core logic as the Netlify + FastAPI demo. 100% Python.")

# Sidebar config
with st.sidebar:
    st.header("Configuration")

    backend_mode = st.radio(
        "Data source",
        ["Use local scraper (Python)", "Call remote FastAPI"],
        index=0,
        help="Local = runs scraper.py directly (fastest). Remote = hits the same backend the Netlify app uses."
    )

    if backend_mode == "Call remote FastAPI":
        api_url = st.text_input(
            "FastAPI base URL",
            value=os.getenv("PYTHON_API_URL", "http://localhost:8000"),
            help="Example: https://your-backend.up.railway.app or https://xxx.onrender.com"
        )
        api_key = st.text_input("API Key (if required)", value=os.getenv("API_KEY", ""), type="password")
    else:
        api_url = None
        api_key = None

    st.divider()
    st.markdown("**Supported Tasks**")
    for task, desc in SUPPORTED_TASKS.items():
        st.markdown(f"- **{task}**: {desc}")

    st.divider()
    st.caption("Made for the Streamlit + Netlify hybrid demo.")

# Main UI
col1, col2 = st.columns([1.35, 1])

with col1:
    mode = st.radio("Input type", SUPPORTED_MODES, horizontal=True, index=0)

    if mode == "url":
        url = st.text_input("Public URL", value="https://news.ycombinator.com")
        query = None
    else:
        url = None
        query = st.text_input("Search keyword / topic", value="AI agents 2025")

    task = st.selectbox(
        "Analysis task",
        list(SUPPORTED_TASKS.keys()),
        format_func=lambda x: f"{x} — {SUPPORTED_TASKS[x]}",
    )

    max_results = st.slider("Max results", 5, 120, 40, step=5)

    run_col1, run_col2 = st.columns(2)
    with run_col1:
        run_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)
    with run_col2:
        demo_btn = st.button("Load Demo Data", use_container_width=True)

with col2:
    st.markdown("#### How it works")
    st.markdown(
        "When using **local scraper**, we execute `scraper.scrape_and_analyze` directly.\n\n"
        "When using **remote FastAPI**, we call the `/analyze` endpoint (the same one the Netlify Function uses)."
    )
    if api_url:
        st.code(f"POST {api_url}/analyze", language="http")

results_placeholder = st.empty()

# --- Action Handlers ---

def run_local():
    with st.spinner("Scraping and analyzing with Python..."):
        try:
            result = scrape_and_analyze(
                url=url,
                query=query,
                mode=mode,
                task=task,
                max_results=max_results,
            )
            return result
        except Exception as e:
            st.error(f"Local scraper error: {e}")
            return None

def call_remote():
    if not api_url:
        st.error("Please provide a FastAPI base URL.")
        return None

    payload = {
        "mode": mode,
        "task": task,
        "max_results": max_results,
    }
    if mode == "url":
        payload["url"] = url
    else:
        payload["query"] = query

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    url_endpoint = api_url.rstrip("/") + "/analyze"

    with st.spinner("Calling remote Python backend via FastAPI..."):
        try:
            resp = requests.post(url_endpoint, json=payload, headers=headers, timeout=35)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            st.error(f"API error {resp.status_code}: {resp.text[:300]}")
            return None
        except Exception as e:
            st.error(f"Request failed: {e}")
            return None

def display_results(result: dict):
    if not result:
        return

    st.success(f"Task **{result.get('task')}** completed")

    # Meta info
    meta_left, meta_right = st.columns(2)
    with meta_left:
        source = result.get("url") or result.get("query") or result.get("source", "—")
        st.markdown(f"**Source:** `{source}`")
    with meta_right:
        st.markdown(f"**Items returned:** `{result.get('count', '—')}`")

    # Show raw
    with st.expander("Raw JSON response", expanded=False):
        st.json(result)

    # Task specific pretty views
    st.subheader("Results")

    # Try to turn into DataFrame
    df = result_to_dataframe(result)

    if df is not None and not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Download - create columns here so they are scoped to results area
        dcol1, dcol2, dcol3 = st.columns(3)
        csv = df.to_csv(index=False).encode("utf-8")
        json_str = json.dumps(result, indent=2).encode("utf-8")

        with dcol1:
            st.download_button("⬇️ Download CSV", data=csv, file_name=f"{result.get('task', 'result')}.csv", mime="text/csv", use_container_width=True)
        with dcol2:
            st.download_button("⬇️ Download JSON", data=json_str, file_name=f"{result.get('task', 'result')}.json", mime="application/json", use_container_width=True)
        with dcol3:
            st.caption("DataFrame + exports above")
    else:
        # Fallback pretty rendering
        if result.get("headlines"):
            for h in result["headlines"]:
                st.markdown(f"**{h['tag']}** — {h['text']}")
        elif result.get("prices"):
            for p in result["prices"]:
                st.markdown(f"`{p['price']}` — {p.get('context', '')}")
        elif result.get("meta"):
            st.json(result["meta"])
        else:
            st.write(result)

# Button actions
if run_btn:
    result = run_local() if backend_mode.startswith("Use local") else call_remote()
    if result:
        with results_placeholder.container():
            display_results(result)
        # Store for re-render
        st.session_state["last_result"] = result

if demo_btn:
    # Demo data now respects current selection
    demo = {
        "mode": mode,
        "task": task,
        "count": 4,
    }
    if mode == "url":
        demo["url"] = "https://news.ycombinator.com"
        demo["page_title"] = "Hacker News"
        demo["headlines"] = [
            {"tag": "H1", "text": "Hacker News"},
            {"tag": "H2", "text": "Show HN: Streamlit + Netlify collaboration demo"},
            {"tag": "H2", "text": "Ask HN: What are you working on this month?"},
            {"tag": "H3", "text": "Python backend powering authenticated scraping"},
        ]
    else:
        demo["query"] = query or "demo topic"
        demo["search_results"] = [
            {"title": "Example result 1", "url": "https://example.com/1", "snippet": "Demo search result for the chosen keyword."},
            {"title": "Example result 2", "url": "https://example.com/2", "snippet": "Another illustrative search hit."},
        ]
    with results_placeholder.container():
        display_results(demo)
    st.session_state["last_result"] = demo

# Reload last result if present (avoid double-wrapping)
if "last_result" in st.session_state and not (run_btn or demo_btn):
    with results_placeholder.container():
        display_results(st.session_state["last_result"])

# Footer note
st.divider()
st.markdown("**[GitHub / 1nc0gn30/smart-scraper](https://github.com/1nc0gn30/smart-scraper)**")
st.caption("Open source. Use it, fork it, open issues/PRs.")
st.caption(
    "Uses the shared `scraper.py` (local copy or sibling python-backend/). "
    "Same logic powers the Netlify + FastAPI version."
)
