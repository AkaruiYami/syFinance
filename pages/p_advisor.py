# advisor.py
import calendar
from decimal import Decimal
from math import ceil, trunc
import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt
import numpy as np

from utils import config
from models.income import Income
from models.transaction import Transactions
from models.wishlist import Wishlist


from utils.auth import require_login

require_login()

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title("Financial Advisor")
st.markdown("Plan and view what the best for your savings.")
st.divider()


def fmt(amount):
    try:
        return f"{config.CURRENCY} {float(amount):.2f}"
    except NameError:
        return f"{config.CURRENCY} 0.00"


# --- Load Data ---
transactions = (
    Transactions.objects().filter(user_id=int(st.session_state.user_id)).all()
)
incomes = Income.objects().filter(user_id=int(st.session_state.user_id)).all()

transactions = [trans.to_dict() for trans in transactions]
incomes = [income.to_dict() for income in incomes]

df_expenses = (
    pd.DataFrame(transactions)
    if transactions
    else pd.DataFrame(columns=["amount", "category", "date"])  # pyright: ignore
)
df_income = (
    pd.DataFrame(incomes) if incomes else pd.DataFrame(columns=["amount", "date"])  # pyright: ignore
)

# --- Prepare Data ---
for df in [df_expenses, df_income]:
    if not df.empty:
        df["amount"] = df["amount"].astype(float)
        df["date"] = pd.to_datetime(df["date"])

# --- Monthly summaries (grouped by year and month) ---
if not df_income.empty:
    df_income["month"] = df_income["date"].dt.to_period("M")
    income_monthly = df_income.groupby("month")["amount"].sum().reset_index()
else:
    income_monthly = pd.DataFrame(columns=["month", "amount"])  # pyright: ignore

if not df_expenses.empty:
    df_expenses["month"] = df_expenses["date"].dt.to_period("M")
    expense_monthly = df_expenses.groupby("month")["amount"].sum().reset_index()
else:
    expense_monthly = pd.DataFrame(columns=["month", "amount"])  # pyright: ignore

# --- Merge monthly summaries ---
monthly_summary = pd.merge(
    income_monthly,
    expense_monthly,
    on="month",
    how="outer",
    suffixes=("_income", "_expense"),
).fillna(0)

if not monthly_summary.empty:
    monthly_summary["month_str"] = monthly_summary["month"].astype(str)

# --- Plot Line Chart (Monthly Income vs Spending) ---
st.subheader("📈 Monthly Income vs Spending Trend")

if not monthly_summary.empty:
    chart_data = monthly_summary.melt(
        id_vars="month_str",
        value_vars=["amount_income", "amount_expense"],
        var_name="Type",
        value_name="Amount",
    )

    chart_data["Type"] = chart_data["Type"].map(
        {"amount_income": "Income", "amount_expense": "Spending"}  # pyright: ignore
    )

    line_chart = (
        alt.Chart(chart_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("month_str:N", title="Month"),
            y=alt.Y("Amount:Q", title=f"Amount ({config.CURRENCY})"),
            color=alt.Color(
                "Type:N",
                scale=alt.Scale(
                    domain=["Income", "Spending"], range=["#2196F3", "#F44336"]
                ),
            ),
            tooltip=["month_str", "Type", "Amount"],
        )
        .properties(height=300)
    )

    st.altair_chart(line_chart, width="stretch")
else:
    st.info("Not enough data to show monthly trend.")

st.divider()

# --- Calculate Current Month and Averages ---
now = datetime.now()
this_month = now.strftime("%Y-%m")

if not monthly_summary.empty:
    # Convert Period to string for filtering
    monthly_summary["month_str"] = monthly_summary["month"].astype(str)
    current_row = monthly_summary[monthly_summary["month_str"] == this_month]

    # Current month values
    if not current_row.empty:
        monthly_income = current_row["amount_income"].values[0]  # pyright: ignore
        total_expenses = current_row["amount_expense"].values[0]  # pyright: ignore
        net_savings = monthly_income - total_expenses
    else:
        monthly_income = total_expenses = net_savings = 0

    # Previous months average
    previous_months = monthly_summary[monthly_summary["month_str"] < this_month]
    if not previous_months.empty:
        avg_income = previous_months["amount_income"].mean()
        avg_expense = previous_months["amount_expense"].mean()
        avg_savings = (
            previous_months["amount_income"] - previous_months["amount_expense"]
        ).mean()

        avg_income_str = f"{config.CURRENCY} {avg_income:.2f}"
        avg_expense_str = f"{config.CURRENCY} {avg_expense:.2f}"
        avg_savings_str = f"{config.CURRENCY} {avg_savings:.2f}"
    else:
        avg_income_str = avg_expense_str = avg_savings_str = "No previous data"
else:
    monthly_income = total_expenses = net_savings = 0
    avg_income_str = avg_expense_str = avg_savings_str = "No previous data"

st.subheader("📊 Averages from Previous Months")
col1, col2, col3 = st.columns(3)
col1.metric("Average Income", avg_income_str)
col2.metric("Average Spending", avg_expense_str)
col3.metric("Average Savings", avg_savings_str)

st.divider()

st.subheader("🧠 Personalized Insights")

if monthly_income == 0:
    st.warning(
        "No income recorded this month. Add your income to get accurate insights."
    )
else:
    savings_rate = (net_savings / monthly_income) * 100 if monthly_income > 0 else 0
    spending_rate = (total_expenses / monthly_income) * 100 if monthly_income > 0 else 0

    # Insight 1: Savings rate
    if savings_rate >= 20:
        st.success(
            f"✅ Great! You're saving {savings_rate:.1f}% of your income. Keep it up!"
        )
    elif 10 <= savings_rate < 20:
        st.info(
            f"🙂 You're saving {savings_rate:.1f}% of your income. Aim for 20% or more."
        )
    else:
        st.warning(
            f"⚠️ You're saving only {savings_rate:.1f}%. Try reducing unnecessary expenses."
        )

    percent_top = 0
    top_category = "None"
    # Insight 2: Top spending category
    if not df_expenses.empty:
        top_category = df_expenses.groupby("category")["amount"].sum().idxmax()
        top_spent = df_expenses.groupby("category")["amount"].sum().max()
        percent_top = (top_spent / total_expenses) * 100 if total_expenses > 0 else 0

        st.info(
            f"💸 Your top spending category is **{top_category}**, making up {percent_top:.1f}% of total expenses."
        )

        if percent_top > 40:
            st.warning(
                f"Consider reviewing your **{top_category}** expenses — they represent a large portion of your spending."
            )

    # Insight 3: Recommendations
    st.divider()
    st.subheader("📋 Recommendations")

    recs = []
    if savings_rate < 10:
        recs.append("💡 Try setting an automatic savings transfer right after payday.")
    if total_expenses > monthly_income:
        recs.append(
            "⚠️ Your expenses exceed your income — consider reviewing subscriptions or large purchases."
        )
    if not df_expenses.empty and percent_top > 40:
        recs.append(
            f"💡 Reduce {top_category} spending by 10% to save an extra {config.CURRENCY} {total_expenses * 0.1:.2f} next month."
        )
    if savings_rate > 20:
        recs.append(
            "✅ You can consider investing part of your savings for better long-term growth."
        )

    if recs:
        for r in recs:
            st.markdown(f"- {r}")
    else:
        st.success("Everything looks balanced! Keep up your good financial habits. 💪")

st.divider()
# --- Analyze the feasibility of buying the item based on your average monthly income ---
st.subheader("🎯 Goals")

wishlist = (
    Wishlist.objects()
    .filter(user_id=int(st.session_state.user_id))
    .filter(status=Wishlist.Status.NOT_COMPLETE)
    .all()
)
wishlist = [wish.to_dict() for wish in wishlist]

if wishlist:
    df = pd.DataFrame(wishlist)
    df["amount"] = df["amount"].astype(float)

    # --- Use average monthly savings instead of income ---
    WMA_N = len(config.WMA_WEIGHTS)
    latest_incomes = monthly_summary["amount_income"].tail(WMA_N)
    latest_expenses = monthly_summary["amount_expense"].tail(WMA_N)
    latest_savings = latest_incomes - latest_expenses
    n_savings = len(latest_savings)
    if n_savings < WMA_N:
        latest_savings = [0] * (WMA_N - n_savings) + latest_savings
    avg_monthly_savings = sum(
        round(saving * w, 2) for saving, w in zip(latest_savings, config.WMA_WEIGHTS)
    )

    # compute trend adjustment
    monthly_summary["savings"] = (
        monthly_summary["amount_income"] - monthly_summary["amount_expense"]
    )
    monthly_summary = monthly_summary.sort_values("month").reset_index(drop=True)
    monthly_summary["month_index"] = np.arange(1, len(monthly_summary) + 1)
    _x = monthly_summary["month_index"]
    _y = monthly_summary["savings"]
    slope, intercept = np.polyfit(_x, _y, 1)
    # forecast savings for next month
    next_month_index = monthly_summary["month_index"].iloc[-1] + 1
    trend_adjusted_savings = intercept + slope * next_month_index

    try:
        cusion = avg_expense * config.CUSION_FACTOR  # pyright: ignore[reportPossiblyUnboundVariable]
    except NameError:
        cusion = 0

    affordable_savings = avg_monthly_savings + slope - cusion

    if avg_monthly_savings <= 0:
        st.warning(
            "Not enough savings data to calculate affordability. Add income and expense records first."
        )
    else:
        # --- Calculate affordability ---
        df["months_needed"] = (df["amount"] / max(affordable_savings, 0.01)).round(2)

        def cal_estimate_time(months):
            decimals = Decimal(str(months)) % 1
            today = datetime.now()
            num_days = calendar.monthrange(today.year, today.month)[1]
            num_days = ceil(decimals * int(num_days))
            str_fmt = f"{num_days} day{'s' if num_days > 1 else ''}"
            months = trunc(months)
            if months > 0:
                str_fmt = f"{months} month{'s' if months > 1 else ''} {str_fmt}"
            return str_fmt

        def safe_est_purchase_date(months):
            if months < 1:
                return "This Month"
            if months > 1200:  # cap at 100 years
                return "Far Future"
            now = pd.Timestamp.now()
            return (now + pd.DateOffset(months=int(months))).strftime("%Y-%m")

        now = datetime.now()
        df["est_purchase_date"] = df["months_needed"].apply(safe_est_purchase_date)

        # Display with formatted currency
        df["amount_fmt"] = df["amount"].apply(fmt)

        st.markdown(
            "### Wishlist Affordability Based on Your **Average Monthly Savings**"
        )
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.caption(
                f"Weighted Moving Average Monthly Savings: {fmt(avg_monthly_savings)}"
            )
        with col2:
            st.caption(f"Saving Trend per Month: {fmt(slope)}")
        with col3:
            st.caption(f"Cusion: {fmt(cusion)}")
        with col4:
            st.caption(f"Affordable Savings: {fmt(affordable_savings)}")

        if affordable_savings <= 0:
            st.error("Not enough savings. Consider improve your monthly savings first.")
        display = df[["name", "amount_fmt", "months_needed", "est_purchase_date"]]
        display = display.rename(
            columns={
                "name": "Name",
                "amount_fmt": "Amount",
                "months_needed": "Estimated Time",
                "est_purchase_date": "Estimated Purchase Date",
            }
        )  # pyright: ignore [reportCallIssue]
        display["Estimated Time"] = display["Estimated Time"].apply(cal_estimate_time)
        st.table(display)

        st.markdown("### Advisor Notes")

        for _, row in df.iterrows():
            n = row["name"]
            amt = row["amount"]
            m = row["months_needed"]

            if m <= 1:
                st.success(
                    f"You can afford **{n}** this month. Estimated cost: {fmt(amt)}."
                )
            elif m <= 3:
                st.info(
                    f"You're close to affording **{n}** — about **{m} months** needed."
                )
            else:
                st.warning(
                    f"**{n}** will require about **{m} months** of savings. Consider prioritizing smaller goals first."
                )

else:
    st.info("Looks like you don't have anything you wanted to buy yet.")
