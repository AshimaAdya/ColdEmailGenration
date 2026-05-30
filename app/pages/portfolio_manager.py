import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from portfolio import Portfolio

load_dotenv()

st.set_page_config(layout="wide", page_title="Portfolio Manager", page_icon="📁")
st.title("Portfolio Manager")

portfolio = Portfolio()


def _reload_data():
    portfolio.data = pd.read_csv(portfolio.file_path)
    portfolio.data = portfolio.data[portfolio.data["Techstack"] != "Techstack"].reset_index(drop=True)


# --- View current portfolio ---
st.subheader("Current Portfolio Entries")
_reload_data()
st.dataframe(portfolio.data, use_container_width=True)
st.caption(f"{len(portfolio.data)} entries | Vector store: {portfolio.collection.count()} docs")

st.divider()

# --- Add entry ---
st.subheader("Add Entry")
with st.form("add_entry", clear_on_submit=True):
    techstack = st.text_input("Tech Stack (comma-separated skills)", placeholder="Python, FastAPI, PostgreSQL")
    link = st.text_input("Portfolio Link", placeholder="https://github.com/you/project")
    submitted = st.form_submit_button("Add Entry")
    if submitted:
        if not techstack.strip() or not link.strip():
            st.error("Both Tech Stack and Link are required.")
        else:
            new_row = pd.DataFrame([{"Techstack": techstack.strip(), "Links": link.strip()}])
            new_row.to_csv(portfolio.file_path, mode="a", header=False, index=False)
            portfolio.force_reload()
            st.success(f"Entry added. Vector store now has {portfolio.collection.count()} docs.")
            st.rerun()

st.divider()

# --- Delete entry ---
st.subheader("Delete Entry")
_reload_data()
if portfolio.data.empty:
    st.info("No entries to delete.")
else:
    options = {f"[{i}] {row['Techstack'][:60]}": i for i, row in portfolio.data.iterrows()}
    selected_label = st.selectbox("Select entry to delete", list(options.keys()))
    if st.button("Delete Selected Entry", type="secondary"):
        idx = options[selected_label]
        updated = portfolio.data.drop(idx).reset_index(drop=True)
        updated.to_csv(portfolio.file_path, index=False)
        portfolio.force_reload()
        st.success("Entry deleted and vector store updated.")
        st.rerun()

st.divider()

# --- Force reload ---
st.subheader("Force Reload Vector Store")
st.caption("Use this if you edited the CSV file directly outside the app.")
if st.button("Force Reload", type="primary"):
    portfolio.force_reload()
    st.success(f"Vector store rebuilt with {portfolio.collection.count()} entries.")
