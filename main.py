import streamlit as st

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

pg = st.navigation(
    {
        "": [dashboard_page, income_page, transaction_page],
        "Tools": [advisor_page],
    }
)

pg.run()
