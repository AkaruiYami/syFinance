from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt

from utils import config
from models.income import Income
from models.transaction import Transactions


from utils.auth import require_login

require_login()

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title(config.APP_NAME)
st.markdown("Overview of your income, expenses, and savings.")
st.divider()

# Get all transactions and incomes
transactions = Transactions.objects().all()
incomes = Income.objects().all()

transactions = [trans.to_dict() for trans in transactions]
incomes = [income.to_dict() for income in incomes]
# Convert to DataFrames with default columns if empty
df_expenses = (
    pd.DataFrame(transactions)
    if transactions
    else pd.DataFrame(columns=["amount", "category", "date"])  # pyright: ignore
)
df_income = (
    pd.DataFrame(incomes) if incomes else pd.DataFrame(columns=["amount", "date"])  # pyright: ignore
)

# Ensure numeric safely
if "amount" in df_expenses.columns:
    df_expenses["amount"] = pd.to_numeric(
        df_expenses["amount"], errors="coerce"
    ).fillna(0.0)  # pyright: ignore
else:
    df_expenses["amount"] = pd.Series(dtype=float)

if "amount" in df_income.columns:
    df_income["amount"] = pd.to_numeric(df_income["amount"], errors="coerce").fillna(  # pyright: ignore
        0.0
    )
else:
    df_income["amount"] = pd.Series(dtype=float)

# Ensure date is datetime safely
if "date" in df_expenses.columns and not df_expenses.empty:
    df_expenses["date"] = pd.to_datetime(df_expenses["date"], errors="coerce")
if "date" in df_income.columns and not df_income.empty:
    df_income["date"] = pd.to_datetime(df_income["date"], errors="coerce")

total_expenses = df_expenses["amount"].sum() if not df_expenses.empty else 0.0
monthly_income = df_income["amount"].sum() if not df_income.empty else 0.0
net_savings = monthly_income - total_expenses

# Filter only current month
now = datetime.now()
if not df_expenses.empty and "date" in df_expenses.columns:
    df_expenses = df_expenses[
        (df_expenses["date"].dt.year == now.year)
        & (df_expenses["date"].dt.month == now.month)
    ]
if not df_income.empty and "date" in df_income.columns:
    df_income = df_income[
        (df_income["date"].dt.year == now.year)
        & (df_income["date"].dt.month == now.month)
    ]

# Totals
total_expenses = df_expenses["amount"].sum() if not df_expenses.empty else 0.0
monthly_income = df_income["amount"].sum() if not df_income.empty else 0.0

# Format metrics
total_expenses_str = f"{config.CURRENCY} {total_expenses:.2f}"
monthly_income_str = f"{config.CURRENCY} {monthly_income:.2f}"
net_savings_str = f"{config.CURRENCY} {net_savings:.2f}"

# Display metrics
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Monthly Income", monthly_income_str)
with col2:
    st.metric("Total Expenses", total_expenses_str)
with col3:
    st.metric("Net Savings", net_savings_str)

st.divider()
st.subheader("Expenses by Category")

if not df_expenses.empty:
    # Group by category
    category_summary = (
        df_expenses.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )

    # Pie chart for expenses
    pie_chart = (
        alt.Chart(category_summary)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta(field="amount", type="quantitative"),
            color=alt.Color(field="category", type="nominal"),
            tooltip=["category", "amount"],
        )
    )
    st.altair_chart(pie_chart, width="stretch")

    # Display table
    table_display = category_summary.copy()
    table_display["amount"] = table_display["amount"].map(
        lambda x: f"{config.CURRENCY} {x:.2f}"
    )
    st.table(table_display)
else:
    st.info("No transactions recorded this month.")

st.divider()
st.subheader("Income vs Expenses Overview")

# Combine totals for chart
summary_df = pd.DataFrame(
    {"Type": ["Income", "Expenses"], "Amount": [monthly_income, total_expenses]}
)

# Bar chart comparing income and expenses
income_expense_chart = (
    alt.Chart(summary_df)
    .mark_bar()
    .encode(
        x=alt.X("Type:N", title="Type"),
        y=alt.Y("Amount:Q", title=f"Amount ({config.CURRENCY})"),
        color=alt.Color(
            "Type:N",
            scale=alt.Scale(
                domain=["Income", "Expenses"], range=["#4CAF50", "#F44336"]
            ),
        ),
        tooltip=["Type", "Amount"],
    )
)
st.altair_chart(income_expense_chart, width="stretch")
