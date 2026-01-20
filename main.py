# MIT License
# Copyright (c) 2025 Yami
# See LICENSE file for details.

import streamlit as st

ADMIN_ID = 1

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


pg_dict = {
    "": [dashboard_page, income_page, transaction_page],
    "Tools": [advisor_page, target_page],
    "User": [login_page],
}

try:
    if st.session_state.logged_in:
        if st.session_state.user_id == ADMIN_ID:
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
