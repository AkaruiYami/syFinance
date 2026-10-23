from datetime import date, timedelta
from math import ceil

import altair as alt
import pandas as pd
import streamlit as st

from components.budget_view import select_period, show_metrics
from models.income import Income
from models.transaction import Transactions
from models.wishlist import Wishlist
from utils import config
from utils.auth import require_login
from utils.budget import comparison_period, records_in, summarize

require_login()
st.set_page_config(page_title=config.APP_NAME, layout="wide")
st.title("Financial Advisor")
st.markdown("Compare your spending, plan savings, and track your goals.")
user_id = int(st.session_state.user_id)
incomes = [r.to_dict() for r in Income.objects().filter(user_id=user_id).all()]
expenses = [r.to_dict() for r in Transactions.objects().filter(user_id=user_id).all()]
mode, period, policies, periods = select_period(user_id, incomes + expenses, "advisor")
unit = "cycle" if mode == "Payday cycle" else "month"
today = date.today()
values = show_metrics(incomes, expenses, period)
selected_expenses = records_in(expenses, period, today)
df_expenses = pd.DataFrame(selected_expenses)

history = [
    {"Period": item.label, "period": item, **summarize(incomes, expenses, item, today)}
    for item in periods
    if item.start <= period.start
]
completed = [r for r in history if r["completed"] and r["period"].end <= period.start]
st.subheader(f"Income and spending by {unit}")
trend = pd.DataFrame(
    [
        {"Period": r["Period"], "Income": r["income"], "Spending": r["spending"]}
        for r in history
    ]
)
st.altair_chart(
    alt.Chart(trend.melt("Period", var_name="Type", value_name="Amount"))
    .mark_line(point=True)
    .encode(
        x=alt.X("Period:N", sort=trend["Period"].tolist()),
        y=alt.Y("Amount:Q", title=f"Amount ({config.CURRENCY})"),
        color="Type:N",
        tooltip=["Period", "Type", "Amount"],
    ),
    width="stretch",
)
st.subheader("Spending comparison")
previous = comparison_period(period, mode, policies, today)
previous_values = summarize(incomes, expenses, previous, today)
st.caption(f"Compared with {previous.label}; open periods use matching elapsed days.")
st.metric(
    f"Spending versus previous {unit}",
    config.fmt(values["spending"]),
    delta=config.fmt(values["spending"] - previous_values["spending"]),
    delta_color="inverse",
)
if not values["completed"]:
    st.metric(
        "Estimated full-period spending", config.fmt(values["projected_spending"])
    )
    st.caption(
        "Estimate based on spending per elapsed day; one-off purchases can affect it. "
        "Recorded income is not extrapolated."
    )
st.subheader(f"Averages from completed {unit}s")
if completed:
    cols = st.columns(3)
    for col, label, key in zip(
        cols,
        ["Average income", "Average spending", "Average surplus / deficit"],
        ["income", "spending", "balance"],
    ):
        col.metric(label, config.fmt(sum(r[key] for r in completed) / len(completed)))
else:
    st.info("No earlier completed periods available.")
st.subheader("Personalized insights")
if values["income"] <= 0:
    st.info("No income recorded in this period. Add income to receive budget guidance.")
elif values["completed"]:
    st.info(
        f"This {unit} ended with a net surplus / deficit of {config.fmt(values['balance'])}."
    )
else:
    st.info(
        f"Recorded income less spending leaves {config.fmt(values['balance'])} so far."
    )
if values["income"] > 0 and values["spending"] > values["income"]:
    st.warning(
        f"Spending exceeds recorded income by {config.fmt(values['spending'] - values['income'])}."
    )
if period.savings_percent is not None and values["income"] > 0:
    if values["spendable"] < 0:
        st.warning(
            f"Spending is {config.fmt(-values['spendable'])} above the budget that reserves your savings target."
        )
    elif not values["completed"]:
        st.info(
            f"You can spend {config.fmt(values['spendable'])} more this cycle while retaining your planned reserve."
        )

st.subheader("Category trends")
if selected_expenses:
    subcategories = st.checkbox(
        "Show subcategory breakdown", key="advisor_subcategories"
    )

    def category_totals(records):
        result = {}
        for record in records:
            category = record["category"]
            if subcategories:
                category += " > " + (record.get("subcategory") or "(Uncategorized)")
            result[category] = result.get(category, 0) + float(record["amount"])
        return result

    current_categories = category_totals(selected_expenses)
    previous_categories = category_totals(records_in(expenses, previous, today))
    trailing = [
        category_totals(records_in(expenses, r["period"])) for r in completed[-3:]
    ]
    rows = []
    for category in sorted(current_categories.keys() | previous_categories.keys()):
        amount = current_categories.get(category, 0)
        before = previous_categories.get(category, 0)
        change = (amount - before) / before * 100 if before > 0 else None
        rows.append(
            {
                "Category": category,
                "Selected period": amount,
                "Previous comparison": before,
                "Change (%)": change,
                "Prior 3 completed periods average": sum(
                    t.get(category, 0) for t in trailing
                )
                / len(trailing)
                if trailing
                else None,
            }
        )
        if change is not None and change > config.CATEGORY_SPIKE_THRESHOLD:
            st.warning(
                f"{category} spending increased {change:.0f}% versus the previous comparison."
            )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    top = max(current_categories, key=current_categories.get)
    st.caption(
        f"Largest spending category: {top} ({config.fmt(current_categories[top])})."
    )
    other = sum(
        float(r["amount"])
        for r in selected_expenses
        if r["category"] == config.OTHER_CATEGORY_NAME
    )
    if (
        values["spending"] > 0
        and other / values["spending"] * 100 > config.OTHER_CATEGORY_PCT_THRESHOLD
    ):
        st.info(
            "A large share of spending is in Other. More specific categories can improve insights."
        )
else:
    st.info("No spending recorded in this period.")

st.subheader("Recurring charges")
recurring = {}
for row in completed:
    seen = set()
    for record in records_in(expenses, row["period"]):
        description = (record.get("description") or "").strip().lower()
        if description:
            seen.add((description, round(float(record["amount"]), 2)))
    for key in seen:
        recurring[key] = recurring.get(key, 0) + 1
recurring_rows = [
    {"Description": key[0], "Amount": key[1], "Completed periods": count}
    for key, count in recurring.items()
    if count >= config.RECURRING_MIN_MONTHS
]
if recurring_rows:
    st.dataframe(recurring_rows, hide_index=True)
else:
    st.caption("Not enough repeated payments across completed periods.")

st.subheader("Unusual transactions")
baseline = pd.DataFrame(
    [record for r in completed for record in records_in(expenses, r["period"])]
)
unusual = []
if not baseline.empty:
    stats = baseline.groupby("category")["amount"].agg(["mean", "std", "count"])
    for record in selected_expenses:
        if record["category"] in stats.index:
            stat = stats.loc[record["category"]]
            if (
                stat["count"] >= 3
                and stat["std"] > 0
                and record["amount"]
                > stat["mean"] + config.ANOMALY_STD_THRESHOLD * stat["std"]
            ):
                unusual.append(record)
if unusual:
    st.dataframe(
        pd.DataFrame(unusual)[["date", "category", "amount", "description"]],
        hide_index=True,
    )
else:
    st.caption("No unusual transactions found against the available completed history.")

st.subheader("Spending by day of week")
if not df_expenses.empty:
    df_expenses["weekday"] = pd.to_datetime(df_expenses["date"]).dt.dayofweek
    end = min(period.end, today + timedelta(days=1))
    counts = {day: 0 for day in range(7)}
    cursor = period.start
    while cursor < end:
        counts[cursor.weekday()] += 1
        cursor += timedelta(days=1)
    totals = df_expenses.groupby("weekday")["amount"].sum()
    names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    st.bar_chart(
        pd.DataFrame(
            [
                {
                    "Day": name,
                    "Average spending": totals.get(day, 0) / counts[day]
                    if counts[day]
                    else 0,
                }
                for day, name in enumerate(names)
            ]
        ),
        x="Day",
        y="Average spending",
        sort=False,
    )

st.subheader("Goals")
wishlist = (
    Wishlist.objects()
    .filter(user_id=user_id)
    .filter(status=Wishlist.Status.NOT_COMPLETE)
    .all()
)
if not wishlist:
    st.info("Add a wishlist item to see savings-based estimates.")
elif not completed:
    st.info("Complete at least one reporting period to estimate goal affordability.")
else:
    n = min(len(config.WMA_WEIGHTS), len(completed))
    recent = completed[-n:]
    weights = config.WMA_WEIGHTS[-n:]
    weight_sum = sum(weights)
    savings = (
        max(0, sum(r["balance"] * w for r, w in zip(recent, weights)) / weight_sum)
        if weight_sum
        else 0
    )
    st.caption(
        f"Based on weighted average surplus from completed {unit}s: {config.fmt(savings)} per {unit}. This is an estimate, not a cash balance."
    )
    st.dataframe(
        [
            {
                "Goal": wish.name,
                "Amount": config.fmt(wish.amount),
                f"Estimated {unit}s": str(ceil(wish.amount / savings))
                if savings > 0
                else "Not affordable at current rate",
            }
            for wish in wishlist
        ],
        hide_index=True,
        width="stretch",
    )
