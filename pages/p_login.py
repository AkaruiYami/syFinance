import streamlit as st

st.set_page_config(page_title="Login", layout="wide")

st.title("Login")
st.markdown("A simple Login page.")
st.divider()


def login_page():
    st.title("🔐 Login to syFinance")

    USERNAME = "admin"
    PASSWORD = "satua"

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
        if username == USERNAME and password == PASSWORD:
            st.session_state.logged_in = True
            st.success("✅ Login successful!")
            st.switch_page("pages/p_summary.py")
        else:
            st.error("❌ Invalid username or password.")


login_page()
