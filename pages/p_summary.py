from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from components.budget_view import select_period, show_metrics
from models.income import Income
from models.transaction import Transactions
from utils import config
from utils.auth import require_login
from utils.budget import comparison_period, records_in, summarize

require_login()

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title(config.APP_NAME)
st.markdown("Overview of your income, expenses, and savings.")
st.divider()

# Get all transactions and incomes
transactions = (
    Transactions.objects().filter(user_id=int(st.session_state.user_id)).all()
)
incomes = Income.objects().filter(user_id=int(st.session_state.user_id)).all()

transactions = [trans.to_dict() for trans in transactions]
incomes = [income.to_dict() for income in incomes]
mode, period, policies, _ = select_period(
    int(st.session_state.user_id), transactions + incomes, "dashboard"
)
values = show_metrics(incomes, transactions, period)
today = date.today()
total_income = sum(
    float(record["amount"])
    for record in incomes
    if date.fromisoformat(str(record["date"])[:10]) <= today
)
total_spending = sum(
    float(record["amount"])
    for record in transactions
    if date.fromisoformat(str(record["date"])[:10]) <= today
)
st.metric("Total savings (all time)", config.fmt(total_income - total_spending))
previous = comparison_period(period, mode, policies)
previous_values = summarize(incomes, transactions, previous)
st.caption(
    f"Previous {'cycle' if mode == 'Payday cycle' else 'month'} comparison: "
    f"{previous.label}"
)
st.metric(
    "Spending versus previous period",
    config.fmt(values["spending"]),
    delta=config.fmt(values["spending"] - previous_values["spending"]),
    delta_color="inverse",
)
df_expenses = pd.DataFrame(records_in(transactions, period, date.today()))
total_expenses = values["spending"]
monthly_income = values["income"]

st.divider()
st.subheader("Expenses by Category")

if not df_expenses.empty:
    show_subcats = st.checkbox(
        "Show subcategory breakdown", key="summary_subcat_toggle"
    )

    if show_subcats:
        df_plot = df_expenses.copy()
        df_plot["subcategory"] = df_plot["subcategory"].fillna("(Uncategorized)")
        df_plot["label"] = df_plot["category"] + " > " + df_plot["subcategory"]
        category_summary = (
            df_plot.groupby("label")["amount"]
            .sum()
            .reset_index()
            .sort_values("amount", ascending=False)
        )
        color_field = "label"
        tooltip_fields = ["label", "amount"]
    else:
        category_summary = (
            df_expenses.groupby("category")["amount"]
            .sum()
            .reset_index()
            .sort_values("amount", ascending=False)
        )
        color_field = "category"
        tooltip_fields = ["category", "amount"]

    # Pie chart for expenses
    pie_chart = (
        alt.Chart(category_summary)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta(field="amount", type="quantitative"),
            color=alt.Color(field=color_field, type="nominal"),
            tooltip=tooltip_fields,
        )
    )
    st.altair_chart(pie_chart, width="stretch")

    # Display table
    table_display = category_summary.copy()
    table_display["amount"] = table_display["amount"].map(config.fmt)
    st.table(table_display)
else:
    st.info("No transactions recorded in this period.")

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
