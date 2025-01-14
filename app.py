# app.py
import streamlit as st
from comparison import comparison_page
from results import results_page

# Set up wide mode and page title
st.set_page_config(layout="wide", page_title="Bullet Rating App v2")

# Check URL parameter
query_params = st.query_params
view = query_params.get("view", "main")  # Default to "main" if no "view" parameter

# Load the appropriate page based on the URL parameter
if view == "main":
    comparison_page()
elif view == "results":
    results_page()
