import streamlit as st

dashboard_page = st.Page("./pages/p_summary.py", title="Dashboard", default=True)
income_page = st.Page("./pages/p_income.py", title="Income")
transaction_page = st.Page("./pages/p_transaction.py", title="Transaction")

pg = st.navigation([dashboard_page, income_page, transaction_page])

pg.run()
