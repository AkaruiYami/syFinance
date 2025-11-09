import streamlit as st
from datetime import date, datetime
import pandas as pd

from utils import config
from models.income import Income

st.set_page_config(page_title="Income", layout="wide")

st.title("Income")
st.markdown("Record the money you receive here.")
st.divider()

# Income entry form
with st.form("add_income", clear_on_submit=True):
    income_date = st.date_input("Date", value=date.today())
    amount = st.number_input(f"Amount ({config.CURRENCY})", min_value=0.0, step=0.10)
    description = st.text_input("Description")
    submitted = st.form_submit_button("Add Income")

if submitted:
    Income.insert(
        {
            "date": str(income_date),
            "amount": float(amount),
            "description": str(description),
        }
    )
    st.success("Income recorded successfully!")

st.divider()
st.subheader("Income History")

incomes = Income.all()

if incomes:
    # Convert to DataFrame
    df = pd.DataFrame(incomes)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # --- Monthly Summary ---
    df["month"] = df["date"].dt.to_period("M")
    monthly_income = df.groupby("month")["amount"].sum().reset_index()
    monthly_income["month"] = monthly_income["month"].astype(str)

    # --- Chart ---
    st.subheader("Monthly Income Trend")
    st.line_chart(
        data=monthly_income,
        x="month",
        y="amount",
        width="stretch",
    )

    st.divider()
    st.subheader("All Income Records")

    # Format for display
    df_display = df.copy()
    df_display["amount"] = df_display["amount"].apply(
        lambda x: f"{config.CURRENCY} {x:.2f}"
    )

    # --- Pagination Setup ---
    page_size = 25
    total_records = len(df_display)
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
    paginated_df = df_display.iloc[start_idx:end_idx]

    # --- Display Table ---
    st.table(paginated_df[["date", "amount", "description"]])

    st.divider()
    st.subheader("Monthly Summary")

    now = datetime.now()
    df_current_month = df[
        (df["date"].dt.year == now.year) & (df["date"].dt.month == now.month)
    ]

    total_income = df_current_month["amount"].sum()
    total_income_str = f"{config.CURRENCY} {total_income:.2f}"

    st.metric("Total Income (This Month)", total_income_str)

else:
    st.info("No income recorded yet.")
