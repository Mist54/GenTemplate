# app.py

import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime
from pathlib import Path
from gemini_api import generate_response
import time

# --------------------------
# Page configuration
# --------------------------
st.set_page_config(page_title="Gemini Report Generator", layout="wide")
st.title("🤖 Gemini Streamlit App")
st.caption("Section-wise report generation — AI does all calculations")
st.divider()

# --------------------------
# Optional Chat Interface
# --------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.expander("💬 Chat with Gemini (optional)", expanded=False):
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    if prompt := st.chat_input("Ask Gemini a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Gemini is thinking..."):
                reply = generate_response(prompt)
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

st.divider()

# --------------------------
# Section-by-section Report Generator UI
# --------------------------
st.subheader("📊 Section-by-section Report Generator (AI handles all calculations)")

# File uploaders
csv_file = st.file_uploader("Upload CSV Data (optional)", type=["csv"])
template_file = st.file_uploader("Upload Template TXT (optional)", type=["txt"])

# Default paths (fallback if no upload)
csv_path = Path("src/Monthly_Operations_Data.csv")
template_path = Path("src/ReportTemplate.txt")
outputs_dir = Path("outputs")
outputs_dir.mkdir(parents=True, exist_ok=True)

# --------------------------
# Helper functions
# --------------------------
def load_dataframe():
    """Load CSV data either from uploaded file or default local path."""
    if csv_file:
        try:
            return pd.read_csv(csv_file)
        except Exception as e:
            st.error(f"Failed to read uploaded CSV: {e}")
            return None
    if csv_path.exists():
        try:
            return pd.read_csv(csv_path)
        except Exception as e:
            st.error(f"Failed to read CSV at {csv_path}: {e}")
            return None
    st.error("CSV data not found. Upload a CSV or place one at src/Monthly_Operations_Data.csv")
    return None

def load_template_text():
    """Load template text either from uploaded file or default local path."""
    if template_file:
        try:
            return template_file.read().decode("utf-8")
        except Exception as e:
            st.error(f"Failed to read uploaded template: {e}")
            return None
    if template_path.exists():
        try:
            return template_path.read_text(encoding="utf-8")
        except Exception as e:
            st.error(f"Failed to read template at {template_path}: {e}")
            return None
    st.error("Template not found. Upload a .txt template or place one at src/ReportTemplate.txt")
    return None

# --------------------------
# Generate Report button
# --------------------------
if st.button("Generate Report"):
    df = load_dataframe()
    if df is None:
        st.stop()

    template_text = load_template_text()
    if not template_text:
        st.stop()

    # Convert full dataset to list-of-dicts (full CSV sent to AI)
    full_rows = df.fillna("").to_dict(orient="records")
    rows_json = json.dumps(full_rows, ensure_ascii=False, indent=2)

    # Split template into sections (SECTION1, SECTION2, etc.)
    sections = re.split(r'(?=\bSECTION\b)', template_text)
    sections = [s.strip() for s in sections if s.strip()]
    total_sections = len(sections)
    if total_sections == 0:
        st.error("No sections found in template. Ensure your template uses 'SECTION' headers.")
        st.stop()

    report_sections = {}
    section_progress = st.empty()

    # Generate each section one by one
    with st.spinner("Generating report section by section (AI will compute all metrics)..."):
        for i, section in enumerate(sections, start=1):
            prompt = (
f"You are an expert report-generation assistant. Fill ONLY the placeholders marked with {{}} in the CURRENT SECTION below using the FULL RAW DATA provided.\n\n"
f"Rules (follow exactly):\n"
f"1) DO NOT hallucinate. Use only the RAW DATA provided.\n"
f"2) Do NOT change, reword, move, or delete any text outside the placeholders {{}}.\n"
f"3) Perform ALL calculations (sums, averages, percentages, rankings, defect rates, margins, etc.) as needed.\n"
f"4) Round numbers sensibly: integers or 2 decimals.\n"
f"5) For Top-N lists, compute from raw data.\n"
f"6) If any data is missing, fill with '[MISSING DATA]'.\n"
f"7) Return ONLY the filled SECTION TEXT.\n\n"
f"CURRENT SECTION TO FILL:\n{section}\n\n"
f"Full Data (raw rows, unchanged):\n{rows_json}\n"
            )

            section_progress.text(f"Processing section {i}/{total_sections}...")
            try:
                ai_response = generate_response(prompt)
                ai_text = ai_response if isinstance(ai_response, str) else str(ai_response)
            except Exception as e:
                ai_text = f"[ERROR: Gemini API failed for this section: {e}]"

            # Strip extra newlines to avoid messy concatenation
            report_sections[f"section_{i}"] = ai_text.strip("\n")
            time.sleep(0.25)

    # Persist sections and full report in session
    st.session_state.report_sections = report_sections
    st.session_state.total_sections = total_sections
    st.session_state.full_report = "\n\n".join(report_sections[f"section_{i}"] for i in range(1, total_sections + 1))

    # Save to disk
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_file = outputs_dir / f"report_{ts}.txt"
    out_file.write_text(st.session_state.full_report, encoding="utf-8")

    # Display full report preserving formatting
    st.success("Report generated successfully! (AI handled all calculations)")
    st.subheader("Generated Report")
    st.markdown(f"```\n{st.session_state.full_report}\n```")

    # Download button
    with open(out_file, "rb") as f:
        st.download_button(
            label="Download report (TXT)",
            data=f,
            file_name=out_file.name,
            mime="text/plain"
        )

# --------------------------
# Section-specific refinement
# --------------------------
if "report_sections" in st.session_state:
    st.divider()
    st.subheader("✏️ Refine a Specific Section")

    report_sections = st.session_state.report_sections
    total_sections = st.session_state.total_sections
    full_report = st.session_state.full_report  # persistent full report

    # Select section to modify
    section_names = [f"Section {i}" for i in range(1, total_sections + 1)]
    selected_section = st.selectbox("Select section to modify:", section_names)
    section_index = int(selected_section.split()[-1])
    current_text = report_sections[f"section_{section_index}"]

    # Preview current section using markdown to preserve formatting
    st.markdown("**🔍 Current Section Preview:**")
    st.markdown(f"```\n{current_text}\n```")

    # User instruction for modification
    custom_prompt = st.text_area(
        "Enter your refinement instruction (e.g., 'Make summary concise', 'Add Q3 comparison'):",
        placeholder="Describe what you want Gemini to change in this section..."
    )

    if st.button("Regenerate Selected Section"):
        edit_prompt = (
f"You are an expert editor. Modify ONLY the section below based on the user's instruction.\n\n"
f"Rules:\n"
f"1) Keep the structure, formatting, and tone intact unless relevant to the instruction.\n"
f"2) Apply the user's instruction precisely — do not alter unrelated parts.\n"
f"3) Return ONLY the modified section text.\n\n"
f"--- USER INSTRUCTION ---\n{custom_prompt}\n"
f"--- CURRENT SECTION ---\n{current_text}\n"
        )

        with st.spinner(f"Regenerating {selected_section}..."):
            try:
                revised_section = generate_response(edit_prompt)
            except Exception as e:
                st.error(f"Gemini API failed to refine this section: {e}")
                st.stop()

        # Update section in session
        report_sections[f"section_{section_index}"] = revised_section.strip("\n")

        # Rebuild full report
        updated_report = "\n\n".join(report_sections[f"section_{i}"] for i in range(1, total_sections + 1))
        st.session_state.report_sections = report_sections
        st.session_state.full_report = updated_report

        # Save updated report to disk
        updated_ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        updated_file = outputs_dir / f"report_updated_{updated_ts}.txt"
        updated_file.write_text(updated_report, encoding="utf-8")

        st.success(f"{selected_section} updated successfully!")
        st.markdown(f"**📄 Updated Full Report:**\n```\n{updated_report}\n```")

        with open(updated_file, "rb") as f:
            st.download_button(
                label="Download updated report (TXT)",
                data=f,
                file_name=updated_file.name,
                mime="text/plain"
            )
