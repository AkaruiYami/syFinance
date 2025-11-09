import pandas as pd
import streamlit as st
from datetime import date

from utils import config
from models.transaction import Transaction

st.set_page_config(page_title="Transaction", layout="wide")

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

    # --- Pagination Setup ---
    page_size = 25
    total_records = len(df)
    total_pages = (total_records - 1) // page_size + 1

    # Store current page in session_state so it persists between reruns
    if "page_number" not in st.session_state:
        st.session_state.page_number = 1

    # Pagination controls (centered)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write(f"Page {st.session_state.page_number} of {total_pages}")

    col_prev, col_next = st.columns(2)
    with col_prev:
        if (
            st.button("⬅️ Previous", width="stretch")
            and st.session_state.page_number > 1
        ):
            st.session_state.page_number -= 1
    with col_next:
        if (
            st.button("Next ➡️", width="stretch")
            and st.session_state.page_number < total_pages
        ):
            st.session_state.page_number += 1

    # --- Paginate Data ---
    start_idx = (st.session_state.page_number - 1) * page_size
    end_idx = start_idx + page_size
    paginated_df = df.iloc[start_idx:end_idx]

    # --- Display Table ---
    st.table(paginated_df)

else:
    st.info("Table will display recorded transactions once persistence is added.")

st.divider()
st.subheader("Monthly Summary")

# Get all transactions again for summary
transactions = Transaction.all()

if transactions:
    df = pd.DataFrame(transactions)
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
