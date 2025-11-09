import pandas as pd
import streamlit as st
from datetime import date

from components import paginated_table
from utils import config
from models.transaction import Transaction

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title("Transactions")
st.markdown("View, add, and manage your financial transactions here.")
st.divider()

# Add transaction form
with st.form("add_transaction", clear_on_submit=True):
    trans_date = st.date_input("Date", value=date.today())
    category = st.selectbox(
        "Category",
        ["Food", "Transport", "Bills", "Shopping", "Entertainment", "Other"],
    )
    amount = st.number_input(f"Amount ({config.CURRENCY})", min_value=0.0, step=0.10)
    description = st.text_input("Description")
    submitted = st.form_submit_button("Add Transaction")

if submitted:
    Transaction.insert(
        {
            "date": str(trans_date),
            "category": category,
            "amount": float(amount),
            "description": description,
        }
    )
    st.success("Transaction added! (Will be saved later)")

st.divider()
st.subheader("Transaction History")

records = Transaction.all()

if records:
    df = pd.DataFrame(records)
    df["amount"] = (
        df["amount"].astype(float).map(lambda x: f"{config.CURRENCY} {x:.2f}")
    )

    paginated_table(df)

else:
    st.info("Table will display recorded transactions once persistence is added.")


st.divider()
st.subheader("Monthly Summary")
if records:
    df = pd.DataFrame(records)
    df["amount"] = df["amount"].astype(float)
    df_expenses = df[df["amount"] > 0]  # adjust if using negatives for expenses

    # Total Expenses
    total_expenses = df_expenses["amount"].sum()
    total_expenses_str = f"{config.CURRENCY} {total_expenses:.2f}"

    # Expenses per category
    category_summary = (
        df_expenses.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )
    category_summary["amount"] = category_summary["amount"].map(
        lambda x: f"{config.CURRENCY} {x:.2f}"
    )

    st.metric("Total Expenses", total_expenses_str)
    st.text("Expenses by Category")
    st.table(category_summary)

else:
    st.info("No transactions yet to summarize.")
