import streamlit as st

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
loan_page = st.Page("./pages/p_loan.py", title="Loan", icon=":material/credit_score:")

pg = st.navigation(
    {
        "": [dashboard_page, income_page, transaction_page, loan_page],
        "Tools": [advisor_page, target_page],
        "User": [login_page],
    }
)

if st.session_state.get("logged_in"):
    with st.sidebar:
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.success("Logged out successfully.")
            st.switch_page("pages/p_login.py")

pg.run()
