# utils/auth.py
import streamlit as st


def is_logged_in():
    """Return True if user is logged in."""
    return st.session_state.get("logged_in", False)


def require_login():
    """If not logged in, redirect to login page."""
    if not is_logged_in():
        st.switch_page("pages/p_login.py")
