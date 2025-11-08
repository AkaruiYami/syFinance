import streamlit as st
from datetime import date
import pandas as pd

from utils import config
from models.income import Income

st.set_page_config(page_title="Income", page_icon="💵", layout="wide")

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
    st.table(df_display[["date", "amount", "description"]])

else:
    st.info("No income recorded yet.")

