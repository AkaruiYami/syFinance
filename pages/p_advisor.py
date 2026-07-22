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
days_in_month = calendar.monthrange(now.year, now.month)[1]
days_elapsed = now.day  # 1-indexed: today counts as a full day

if not monthly_summary.empty:
    # Convert Period to string for filtering
    monthly_summary["month_str"] = monthly_summary["month"].astype(str)
    current_row = monthly_summary[monthly_summary["month_str"] == this_month]

    # Current month raw values (month to date)
    if not current_row.empty:
        monthly_income = current_row["amount_income"].values[0]  # pyright: ignore
        total_expenses = current_row["amount_expense"].values[0]  # pyright: ignore
        net_savings = monthly_income - total_expenses
    else:
        monthly_income = total_expenses = net_savings = 0

    # Prorated projection: extrapolate MTD spending to full month
    if days_elapsed > 0:
        prorated_expenses = (total_expenses / days_elapsed) * days_in_month
        prorated_income = (monthly_income / days_elapsed) * days_in_month
    else:
        prorated_expenses = total_expenses
        prorated_income = monthly_income

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
    prorated_expenses = prorated_income = 0
    avg_income_str = avg_expense_str = avg_savings_str = "No previous data"

st.subheader("📊 Month-to-Date Progress")
st.caption(f"Day {days_elapsed} of {days_in_month} — {days_elapsed / days_in_month:.0%} through the month")

col1, col2, col3 = st.columns(3)
col1.metric(
    "Income (MTD)",
    fmt(monthly_income),
    delta=f"Projected: {fmt(prorated_income)}" if days_elapsed > 0 and prorated_income != monthly_income else None,
)
col2.metric(
    "Spending (MTD)",
    fmt(total_expenses),
    delta=f"Projected: {fmt(prorated_expenses)}" if days_elapsed > 0 and prorated_expenses != total_expenses else None,
    delta_color="inverse",
)
col3.metric(
    "Savings (MTD)",
    fmt(net_savings),
    delta=f"Projected: {fmt(prorated_income - prorated_expenses)}" if days_elapsed > 0 else None,
)

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

    # Default values outside conditional to avoid NameError on empty data
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

# --- Category Trends (Month-over-Month) ---
st.subheader("📊 Category Trends")

if not df_expenses.empty and "month" in df_expenses.columns:
    cat_monthly = (
        df_expenses.groupby(["month", "category"])["amount"]
        .sum()
        .reset_index()
        .sort_values("month")
    )

    # Determine which month to analyze (current if available, else most recent)
    available_months = sorted(cat_monthly["month"].unique())
    latest_month = max(available_months)

    current_cat = cat_monthly[cat_monthly["month"] == latest_month].set_index("category")["amount"]
    prev_month = available_months[-2] if len(available_months) >= 2 else None
    prev_cat = (
        cat_monthly[cat_monthly["month"] == prev_month]["amount"].values[0]
        if prev_month is not None
        else None
    )

    # Trailing 3-month average per category (excluding latest month)
    trailing_3m = cat_monthly[cat_monthly["month"].isin(available_months[-4:-1])]
    avg_3m = trailing_3m.groupby("category")["amount"].mean() if not trailing_3m.empty else pd.Series(dtype=float)

    trend_rows = []
    for cat, amount in current_cat.items():
        # vs previous month
        if prev_cat is not None and prev_month is not None:
            prev_val = cat_monthly[
                (cat_monthly["month"] == prev_month) & (cat_monthly["category"] == cat)
            ]["amount"]
            prev_amount = prev_val.values[0] if not prev_val.empty else 0
            pct_prev = ((amount - prev_amount) / prev_amount * 100) if prev_amount > 0 else None
        else:
            pct_prev = None

        # vs 3-month average
        avg_3m_val = avg_3m.get(cat, 0)
        pct_3m = ((amount - avg_3m_val) / avg_3m_val * 100) if avg_3m_val > 0 else None

        trend_rows.append({
            "Category": cat,
            "Latest": amount,
            "Prev Month": prev_amount if prev_cat is not None else None,
            "Δ% (MoM)": pct_prev,
            "3M Avg": avg_3m_val if avg_3m_val > 0 else None,
            "Δ% (3M)": pct_3m,
        })

    if trend_rows:
        df_trends = pd.DataFrame(trend_rows)

        # Display formatted table
        display_trends = df_trends.copy()
        display_trends["Latest"] = display_trends["Latest"].apply(fmt)
        if "Prev Month" in display_trends.columns:
            display_trends["Prev Month"] = display_trends["Prev Month"].apply(
                lambda x: fmt(x) if pd.notna(x) and x is not None else "—"
            )
        display_trends["Δ% (MoM)"] = display_trends["Δ% (MoM)"].apply(
            lambda x: f"{x:+.1f}%" if pd.notna(x) and x is not None else "—"
        )
        display_trends["3M Avg"] = display_trends["3M Avg"].apply(
            lambda x: fmt(x) if pd.notna(x) and x is not None else "—"
        )
        display_trends["Δ% (3M)"] = display_trends["Δ% (3M)"].apply(
            lambda x: f"{x:+.1f}%" if pd.notna(x) and x is not None else "—"
        )

        st.dataframe(display_trends, use_container_width=True, hide_index=True)

        # Flag large spikes
        spikes = df_trends[
            ((df_trends["Δ% (MoM)"].fillna(0).abs() > config.CATEGORY_SPIKE_THRESHOLD))
            | ((df_trends["Δ% (3M)"].fillna(0).abs() > config.CATEGORY_SPIKE_THRESHOLD))
        ]
        for _, row in spikes.iterrows():
            cat_name = row["Category"]
            latest = row["Latest"]
            if pd.notna(row["Δ% (MoM)"]) and abs(row["Δ% (MoM)"]) > config.CATEGORY_SPIKE_THRESHOLD:
                direction = "increased" if row["Δ% (MoM)"] > 0 else "decreased"
                st.warning(
                    f"**{cat_name}** {direction} by {abs(row['Δ% (MoM)']):.0f}% vs last month "
                    f"({fmt(row['Prev Month'] if pd.notna(row['Prev Month']) else 0)} → {fmt(latest)})."
                )
            elif pd.notna(row["Δ% (3M)"]) and abs(row["Δ% (3M)"]) > config.CATEGORY_SPIKE_THRESHOLD:
                direction = "above" if row["Δ% (3M)"] > 0 else "below"
                st.info(
                    f"**{cat_name}** is {abs(row['Δ% (3M)']):.0f}% {direction} your 3-month average "
                    f"({fmt(row['3M Avg'])} → {fmt(latest)})."
                )
    else:
        st.info("Not enough category data to compute trends.")
else:
    st.info("Add expenses with categories to see spending trends.")

# --- "Other" Category Black Hole Flag ---
if not df_expenses.empty and "month" in df_expenses.columns:
    latest_month_exp = df_expenses[df_expenses["month"] == df_expenses["month"].max()]
    total_latest = latest_month_exp["amount"].sum()
    other_spend = latest_month_exp[latest_month_exp["category"] == config.OTHER_CATEGORY_NAME]["amount"].sum()
    if total_latest > 0 and other_spend > 0:
        other_pct = (other_spend / total_latest) * 100
        if other_pct > config.OTHER_CATEGORY_PCT_THRESHOLD:
            st.warning(
                f"⚠️ **\"{config.OTHER_CATEGORY_NAME}\"** makes up **{other_pct:.0f}%** of your latest month's spending "
                f"({fmt(other_spend)} of {fmt(total_latest)}). "
                f"Consider recategorizing these transactions for better financial insights."
            )

# --- Anomaly Detection (Unusual Transactions) ---
if not df_expenses.empty and len(df_expenses) > 5:
    cat_stats = df_expenses.groupby("category")["amount"].agg(["mean", "std"]).dropna()
    cat_stats = cat_stats[cat_stats["std"] > 0]

    anomalies = []
    for cat, row in cat_stats.iterrows():
        cat_txns = df_expenses[df_expenses["category"] == cat]
        threshold = row["mean"] + config.ANOMALY_STD_THRESHOLD * row["std"]
        unusual = cat_txns[cat_txns["amount"] > threshold]
        for _, txn in unusual.iterrows():
            z_score = (txn["amount"] - row["mean"]) / row["std"]
            anomalies.append({
                "Date": txn["date"].strftime("%Y-%m-%d") if hasattr(txn["date"], "strftime") else str(txn["date"]),
                "Category": cat,
                "Description": txn.get("description", "") or "",
                "Amount": txn["amount"],
                "Category Avg": row["mean"],
                "Z-score": z_score,
            })

    if anomalies:
        st.divider()
        st.subheader("⚠️ Unusual Transactions")
        st.caption(
            f"Transactions exceeding {config.ANOMALY_STD_THRESHOLD} standard deviations above their category average."
        )
        df_anomalies = pd.DataFrame(anomalies).sort_values("Z-score", ascending=False)
        df_anomalies["Amount"] = df_anomalies["Amount"].apply(fmt)
        df_anomalies["Category Avg"] = df_anomalies["Category Avg"].apply(fmt)
        df_anomalies["Z-score"] = df_anomalies["Z-score"].apply(lambda z: f"{z:.1f}σ")
        st.dataframe(df_anomalies, use_container_width=True, hide_index=True)

# --- Recurring Expense / Subscription Detection ---
if not df_expenses.empty and "month" in df_expenses.columns:
    st.divider()
    st.subheader("📌 Recurring Charges")

    # Normalize descriptions for matching: lowercase, strip whitespace
    df_recur = df_expenses.copy()
    df_recur["norm_desc"] = df_recur["description"].fillna("").str.strip().str.lower()
    df_recur["norm_amt"] = df_recur["amount"].round(2)
    df_recur["month_key"] = df_recur["month"].astype(str)

    # Group by normalized (description, amount) and count distinct months
    recur_groups = (
        df_recur.groupby(["norm_desc", "norm_amt"])
        .agg(
            distinct_months=("month_key", "nunique"),
            txn_count=("id", "count"),
            sample_desc=("description", "first"),
            category=("category", "first"),
        )
        .reset_index()
    )

    # Only keep groups that appear in >= N distinct months (and have a non-empty description)
    recurring = recur_groups[
        (recur_groups["distinct_months"] >= config.RECURRING_MIN_MONTHS)
        & (recur_groups["norm_desc"] != "")
    ].sort_values("norm_amt", ascending=False)

    if not recurring.empty:
        total_monthly_recurring = 0.0
        recur_rows = []
        for _, row in recurring.iterrows():
            # Estimate monthly cost: total spent / number of distinct months
            group_txns = df_recur[
                (df_recur["norm_desc"] == row["norm_desc"])
                & (df_recur["norm_amt"] == row["norm_amt"])
            ]
            total_spent = group_txns["amount"].sum()
            monthly_cost = total_spent / row["distinct_months"]
            total_monthly_recurring += monthly_cost

            # Determine frequency label
            if row["distinct_months"] <= 2:
                freq = "Bi-monthly"
            elif row["distinct_months"] <= 6:
                freq = "Quarterly-ish"
            else:
                freq = "Monthly"

            recur_rows.append({
                "Description": row["sample_desc"] or row["norm_desc"],
                "Category": row["category"],
                "Amount": fmt(row["norm_amt"]),
                "Frequency": f"{freq} ({row['distinct_months']} mo / {row['txn_count']} txns)",
                "Monthly Cost": fmt(monthly_cost),
            })

        st.caption(
            f"Detected {len(recurring)} recurring charge(s) totaling **{fmt(total_monthly_recurring)}/month**."
        )
        st.dataframe(pd.DataFrame(recur_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No recurring charges detected across your transaction history.")

# --- Weekly / Day-of-Week Spending Pattern ---
if not df_expenses.empty and "date" in df_expenses.columns:
    st.divider()
    st.subheader("📅 Spending by Day of Week")

    # Allow user to select which categories to include
    all_categories = sorted(df_expenses["category"].unique()) if "category" in df_expenses.columns else []
    default_cats = [c for c in ["Food", "Entertainment"] if c in all_categories] or all_categories[:3]
    selected_cats = st.multiselect(
        "Filter by category",
        options=all_categories,
        default=default_cats,
        key="dow_categories",
    )

    if selected_cats:
        dow_df = df_expenses[df_expenses["category"].isin(selected_cats)].copy()
        dow_df["day_name"] = dow_df["date"].dt.day_name()
        dow_df["day_num"] = dow_df["date"].dt.dayofweek  # 0=Mon, 6=Sun

        dow_summary = (
            dow_df.groupby(["day_num", "day_name"])["amount"]
            .agg(["sum", "count"])
            .reset_index()
            .sort_values("day_num")
        )
        dow_summary.columns = ["day_num", "Day", "Total Spent", "Transactions"]

        chart = (
            alt.Chart(dow_summary)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Day:N", sort=None, title="Day of Week"),
                y=alt.Y("Total Spent:Q", title=f"Total Spent ({config.CURRENCY})"),
                color=alt.Color(
                    "Day:N",
                    sort=None,
                    legend=None,
                    scale=alt.Scale(scheme="tableau10"),
                ),
                tooltip=["Day", "Total Spent", "Transactions"],
            )
            .properties(height=250)
        )
        st.altair_chart(chart, use_container_width=True)

        # Weekend vs weekday comparison
        weekday_total = dow_summary[dow_summary["day_num"] < 5]["Total Spent"].sum()
        weekend_total = dow_summary[dow_summary["day_num"] >= 5]["Total Spent"].sum()
        weekday_days = min(5, days_in_month)
        weekend_days = days_in_month - weekday_days
        weekday_avg = weekday_total / weekday_days if weekday_days > 0 else 0
        weekend_avg = weekend_total / weekend_days if weekend_days > 0 else 0

        col1, col2 = st.columns(2)
        col1.metric("Weekday Avg/Day", fmt(weekday_avg))
        col2.metric("Weekend Avg/Day", fmt(weekend_avg))
    else:
        st.info("Select categories to view spending patterns.")

# --- Analyze the feasibility of buying the item based on your average monthly income ---
st.divider()
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
    # Exclude the current (possibly incomplete) month from savings/WMA calculations
    # so that projections are based only on fully elapsed months.
    WMA_N = len(config.WMA_WEIGHTS)
    complete_months = monthly_summary.head(-1) if len(monthly_summary) > 1 else monthly_summary.copy()
    latest_incomes = complete_months["amount_income"].tail(WMA_N)
    latest_expenses = complete_months["amount_expense"].tail(WMA_N)
    latest_savings = latest_incomes - latest_expenses
    n_savings = len(latest_savings)
    if n_savings < WMA_N:
        latest_savings = [0] * (WMA_N - n_savings) + latest_savings
    avg_monthly_savings = sum(
        round(saving * w, 2) for saving, w in zip(latest_savings, config.WMA_WEIGHTS)
    )

    # compute trend adjustment
    complete_months["savings"] = (
        complete_months["amount_income"] - complete_months["amount_expense"]
    )
    complete_months = complete_months.sort_values("month").reset_index(drop=True)
    complete_months["month_index"] = np.arange(1, len(complete_months) + 1)
    _x = complete_months["month_index"]
    _y = complete_months["savings"]
    slope, intercept = np.polyfit(_x, _y, 1)
    # forecast savings for next month
    next_month_index = complete_months["month_index"].iloc[-1] + 1
    trend_adjusted_savings = intercept + slope * next_month_index

    avg_expense = (
        complete_months["amount_expense"].mean() if not complete_months.empty else 0
    )
    cusion = avg_expense * config.CUSION_FACTOR

    if len(complete_months) < config.MIN_ENTRY_SLOPE:
        slope = 0

    affordable_savings = max(avg_monthly_savings + slope - cusion, 0)

    if len(complete_months["amount_income"]) <= 0:
        st.warning(
            "Not enough savings data to calculate affordability. Add income and expense records first."
        )
    else:
        # --- Calculate affordability ---
        AFFORDABILITY_CAP = 1200  # 100 years — anything beyond this is effectively unaffordable
        if affordable_savings == 0:
            df["months_needed"] = AFFORDABILITY_CAP
        else:
            df["months_needed"] = (df["amount"] / affordable_savings).clip(upper=AFFORDABILITY_CAP).round(2)

        def cal_estimate_time(months):
            if months >= AFFORDABILITY_CAP:
                return "Not affordable"
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
            if months >= AFFORDABILITY_CAP:
                return "N/A — not affordable at current savings rate"
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

            if m >= AFFORDABILITY_CAP:
                st.error(
                    f"**{n}** ({fmt(amt)}) is not affordable at your current savings rate of {fmt(affordable_savings)}/month."
                )
            elif m <= 1:
                st.success(
                    f"You can afford **{n}** this month. Estimated cost: {fmt(amt)}."
                )
            elif m <= 3:
                st.info(
                    f"You're close to affording **{n}** — about **{cal_estimate_time(m)}** needed."
                )
            else:
                st.warning(
                    f"**{n}** will require about **{cal_estimate_time(m)}** of savings. Consider prioritizing smaller goals first."
                )

else:
    st.info("Looks like you don't have anything you wanted to buy yet.")
