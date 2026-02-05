# MIT License
# Copyright (c) 2025 Yami
# See LICENSE file for details.

import streamlit as st
from utils.auth import is_admin
from models.user import User

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
