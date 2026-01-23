# utils/auth.py
import streamlit as st
from models.user import User


def is_logged_in():
    """Return True if user is logged in."""
    return st.session_state.get("logged_in", False)


def require_login():
    """If not logged in, redirect to login page."""
    if not is_logged_in():
        st.switch_page("pages/p_login.py")


def is_admin():
    """Return True if current user has admin role."""
    return st.session_state.get("user_role") == "admin"


def require_admin():
    """If not admin, redirect to dashboard with error."""
    if not is_admin():
        st.error("Admin access required.")
        st.switch_page("pages/p_summary.py")


def get_current_user_role():
    """Get the current user's role."""
    return st.session_state.get("user_role", "user")


def get_current_user():
    """Get the current user object."""
    if not is_logged_in():
        return None
    user_id = st.session_state.get("user_id")
    if user_id:
        return User.objects().filter(id=user_id).first()
    return None
