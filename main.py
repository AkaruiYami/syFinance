# MIT License
# Copyright (c) 2025 Yami
# See LICENSE file for details.

import pathlib

import streamlit as st
from argon2 import PasswordHasher
from utils import config
from utils.auth import is_admin
from utils.db import init_db
from admin import api
from models.user import User

# Bootstrap: ensure DB directory exists and tables are created on every startup
try:
    db_path = pathlib.Path(config.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    init_db(verbose=False)
except Exception as e:
    st.error(f"Failed to initialize the database: {e}")
    st.stop()

login_page = st.Page("./pages/p_login.py", title="Login", icon=":material/login:")
dashboard_page = st.Page(
    "./pages/p_summary.py", title="Dashboard", icon=":material/dashboard:", default=True
)
income_page = st.Page(
    "./pages/p_income.py", title="Income", icon=":material/account_balance:"
)
transaction_page = st.Page(
    "./pages/p_transaction.py", title="Transaction", icon=":material/payments:"
)
advisor_page = st.Page(
    "./pages/p_advisor.py", title="Advisor", icon=":material/candlestick_chart:"
)
target_page = st.Page("./pages/p_target.py", title="Target", icon=":material/target:")
# loan_page = st.Pretricted=Noneage("./pages/p_loan.py", title="Loan", icon=":material/credit_score:")

admin_page = st.Page("./admin/pages/p_home.py", title="Admin")


def first_run_setup():
    """Show signup screen when no users exist yet."""
    if User.objects().all():
        return  # Users exist, skip

    st.title("Welcome to syFinance")
    st.markdown("Create your admin account to get started.")

    with st.form("first_run_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create Account")

        if submitted:
            username = username.strip()
            if not username:
                st.error("Username is required.")
            elif not api.is_username_valid(username):
                st.error(
                    f"Cannot use '{username}' as a username. Choose something else."
                )
            elif not password:
                st.error("Password is required.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    ph = PasswordHasher()
                    user = User.new(
                        name=username,
                        password=ph.hash(password),
                        role="admin",
                    )
                    user.save()
                    st.session_state.logged_in = True
                    st.session_state.user_id = user.id
                    st.session_state.user_role = "admin"
                    st.success("Account created! Redirecting...")
                    st.switch_page("pages/p_summary.py")
                except Exception as e:
                    st.error(f"Failed to create account: {e}")

    st.stop()  # Block navigation until signup is complete


def admin_setup():
    """One-time setup to designate the first admin user."""
    # Check if any admin users exist
    admin_users = User.objects().filter(role="admin").all()
    if admin_users:
        return  # Admin already exists, no setup needed

    # If no admin exists and user is logged in, show setup
    if st.session_state.get("logged_in"):
        with st.sidebar:
            st.warning("⚠️ No admin user found. Please designate an admin.")

        st.title("🔧 Admin Setup")
        st.markdown(
            "Since this is the first time the system is running, you need to designate an admin user."
        )

        # Get all users
        all_users = User.objects().all()

        if not all_users:
            st.error("No users found. Please contact system administrator.")
            return

        # Let user choose which user should be admin
        user_options = [f"{user.name} (ID: {user.id})" for user in all_users]
        selected_user_idx = st.selectbox(
            "Select which user should be the admin:",
            range(len(user_options)),
            format_func=lambda i: user_options[i],
        )

        if st.button("Make Admin", type="primary"):
            selected_user = all_users[selected_user_idx]
            selected_user.role = "admin"
            selected_user.save()

            # Update current session if this user is the one logged in
            if st.session_state.get("user_id") == selected_user.id:
                st.session_state.user_role = "admin"

            st.success(f"✅ {selected_user.name} is now an admin!")
            st.rerun()


pg_dict = {
    "": [dashboard_page, income_page, transaction_page],
    "Tools": [advisor_page, target_page],
    "User": [login_page],
}

# First-run: show signup if no users exist (blocks until complete)
first_run_setup()

# Check for admin setup if needed
admin_setup()

try:
    if st.session_state.logged_in and is_admin():
        pg_dict["Admin"] = [admin_page]
except AttributeError:
    pass
finally:
    pg = st.navigation(pg_dict)

if st.session_state.get("logged_in"):
    with st.sidebar:
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.success("Logged out successfully.")
            st.switch_page("pages/p_login.py")

pg.run()
