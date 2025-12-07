import streamlit as st
from argon2 import PasswordHasher
from models.user import User

st.set_page_config(page_title="Login", layout="wide")

st.title("Login")
st.markdown("A simple Login page.")
st.divider()


def login_page():
    ph = PasswordHasher()
    st.title("🔐 Login to syFinance")

    if st.session_state.get("logged_in", False):
        st.success("✅ Already logged in.")
        if st.button("Go to Dashboard"):
            st.switch_page("pages/p_summary.py")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        st.stop()

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = User.objects().filter(name=username).first()
        if user is None:
            st.error("Invalid username.")
            return

        user = user.to_dict()
        hashed_pw = user["password"]

        if ph.verify(hashed_pw.strip(), password):
            st.session_state.logged_in = True
            st.session_state.user_id = user["id"]
            st.success("✅ Login successful!")
            st.switch_page("pages/p_summary.py")
        else:
            st.error("❌ Invalid username or password.")


login_page()
