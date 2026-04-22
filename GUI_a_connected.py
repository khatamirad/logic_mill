# -*- coding: utf-8 -*-
"""
Streamlit GUI for LogicMill similarity search.

Place this file in the same folder as similarity_search_json.py
and run with:

    streamlit run GUI_a_connected.py
"""

import json
import os
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import similarity_search_json as sim


st.set_page_config(page_title="LogicMill Similarity Search", layout="centered")

st.title("LogicMill Similarity Search")
st.caption("Enter your API token, title, and abstract, then click Generate results.")

with st.form("similarity_form"):
    token = st.text_input("API Token", type="password")
    title = st.text_input("Title")
    abstract = st.text_area("Abstract", height=220)

    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("Number of results", min_value=1, max_value=100, value=25, step=1)
    with col2:
        search_type = st.selectbox("Search type", ["both", "patents", "publications"], index=0)

    submitted = st.form_submit_button("Generate results")


def save_gui_results(results, title_text: str):
    results_dir = Path(__file__).parent / "results"
    results_json_dir = results_dir / "json"
    results_dir.mkdir(exist_ok=True)
    results_json_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = "streamlit_query"

    json_path = results_json_dir / f"{base_name}_{timestamp}.json"
    txt_path = results_dir / f"{base_name}_{timestamp}.txt"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    patent_count = sum(1 for r in results if r.get("index") == "patents")
    publication_count = sum(1 for r in results if r.get("index") == "publications")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Query title: {title_text}\n\n")
        f.write(f"Found {len(results)} similar documents:\n\n")
        for i, result in enumerate(results, 1):
            doc = result.get("document", {})
            index_type = result.get("index", "unknown")
            f.write(f"{i}. {doc.get('title', 'No title')}\n")
            f.write(f"   Type: {index_type}\n")
            f.write(f"   Score: {result.get('score', 0):.4f}\n")
            f.write(f"   ID: {result.get('id', 'N/A')}\n")
            if doc.get("url"):
                f.write(f"   URL: {doc['url']}\n")
            f.write("\n")
        f.write("=" * 60 + "\n")
        f.write(f"Summary: {patent_count} patents, {publication_count} publications\n")

    return json_path, txt_path


def build_download_text(results, title_text: str) -> str:
    patent_count = sum(1 for r in results if r.get("index") == "patents")
    publication_count = sum(1 for r in results if r.get("index") == "publications")

    lines = [f"Query title: {title_text}", "", f"Found {len(results)} similar documents:", ""]
    for i, result in enumerate(results, 1):
        doc = result.get("document", {})
        index_type = result.get("index", "unknown")
        lines.append(f"{i}. {doc.get('title', 'No title')}")
        lines.append(f"   Type: {index_type}")
        lines.append(f"   Score: {result.get('score', 0):.4f}")
        lines.append(f"   ID: {result.get('id', 'N/A')}")
        if doc.get("url"):
            lines.append(f"   URL: {doc['url']}")
        lines.append("")
    lines.append("=" * 60)
    lines.append(f"Summary: {patent_count} patents, {publication_count} publications")
    return "\n".join(lines)


if submitted:
    if not token or not title or not abstract:
        st.error("Please fill in all fields.")
    else:
        try:
            os.environ["LOGICMILL_API_TOKEN"] = token

            input_data = {
                "title": title,
                "abstract": abstract,
            }

            with st.spinner("Generating results..."):
                session, active_token = sim.create_session()
                results = sim.fetch_results(
                    session=session,
                    token=active_token,
                    input_data=input_data,
                    amount=int(amount),
                    search_type=search_type,
                )

            if not results:
                st.warning("No results were returned.")
            else:
                st.success(f"Results generated: {len(results)} documents found.")

                patent_count = sum(1 for r in results if r.get("index") == "patents")
                publication_count = sum(1 for r in results if r.get("index") == "publications")

                c1, c2, c3 = st.columns(3)
                c1.metric("Total results", len(results))
                c2.metric("Patents", patent_count)
                c3.metric("Publications", publication_count)

                rows = []
                for i, result in enumerate(results, 1):
                    doc = result.get("document", {})
                    rows.append({
                        "Rank": i,
                        "Title": doc.get("title", "No title"),
                        "Type": result.get("index", "unknown"),
                        "Score": round(float(result.get("score", 0)), 4),
                        "ID": result.get("id", "N/A"),
                        "URL": doc.get("url", ""),
                    })

                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)

                with st.expander("Show first 3 detailed results", expanded=True):
                    for i, result in enumerate(results[:3], 1):
                        doc = result.get("document", {})
                        st.markdown(f"**{i}. {doc.get('title', 'No title')}**")
                        st.write(f"Type: {result.get('index', 'unknown')}")
                        st.write(f"Score: {result.get('score', 0):.4f}")
                        st.write(f"ID: {result.get('id', 'N/A')}")
                        if doc.get("url"):
                            st.write(f"URL: {doc['url']}")
                        st.divider()

                json_path, txt_path = save_gui_results(results, title)

                json_bytes = json.dumps(results, indent=2, ensure_ascii=False).encode("utf-8")
                txt_bytes = build_download_text(results, title).encode("utf-8")

                d1, d2 = st.columns(2)
                with d1:
                    st.download_button(
                        label="Download JSON",
                        data=json_bytes,
                        file_name=json_path.name,
                        mime="application/json",
                    )
                with d2:
                    st.download_button(
                        label="Download TXT",
                        data=txt_bytes,
                        file_name=txt_path.name,
                        mime="text/plain",
                    )

                st.caption(f"Also saved locally to: {txt_path}")
                st.caption(f"JSON archive saved locally to: {json_path}")

        except SystemExit:
            st.error(
                "The backend script stopped because of an API or configuration issue. "
                "This usually means the GraphQL query or endpoint still needs adjustment."
            )
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            st.code(traceback.format_exc())
