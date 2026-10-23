"""Shared reporting controls and budget metrics for Streamlit pages."""

from datetime import date, timedelta

import streamlit as st

from utils import config
from utils.budget import available_periods, load_policies, summarize


def select_period(user_id, records, key, include_all=False):
    policies = load_policies(user_id)
    if not policies:
        st.info("Set your payday and savings target in Budget Settings to use cycles.")
    modes = ["Payday cycle", "Calendar month"] if policies else ["Calendar month"]
    if include_all:
        modes = ["All dates"] + modes
    mode = st.selectbox("Reporting view", modes, key=f"{key}_view_{user_id}")
    if mode == "All dates":
        return mode, None, policies, []
    periods = available_periods(records, mode, policies)
    period = st.selectbox(
        "Period",
        list(reversed(periods)),
        format_func=lambda p: p.label,
        key=f"{key}_period_{mode}_{user_id}",
    )
    st.caption(period.label)
    return mode, period, policies, periods


def show_metrics(incomes, expenses, period):
    values = summarize(incomes, expenses, period)
    completed = values["completed"]
    cols = st.columns(3)
    cols[0].metric("Recorded income", config.fmt(values["income"]))
    cols[1].metric("Spending", config.fmt(values["spending"]))
    cols[2].metric(
        "Net surplus / deficit" if completed else "Remaining balance",
        config.fmt(values["balance"]),
    )
    if not completed:
        st.caption(f"Day {values['elapsed']} of {period.days}; actuals through today.")
    if period.savings_percent is not None:
        st.caption(
            f"Savings target: {period.savings_percent:g}% of recorded income. "
            "This is a planned reserve, not a savings transfer. Budgets do not carry over."
        )
        if values["income"] <= 0:
            st.info(
                "Awaiting income. Spending is recorded; budget guidance needs income."
            )
        else:
            cols = st.columns(3)
            cols[0].metric("Savings target", config.fmt(values["target"]))
            cols[1].metric("Spendable remaining", config.fmt(values["spendable"]))
            if completed:
                met = values["balance"] >= values["target"]
                cols[2].metric("Savings target result", "Met" if met else "Not met")
            elif values["spendable"] < 0:
                cols[2].metric("Over budget", config.fmt(-values["spendable"]))
            else:
                cols[2].metric("Daily allowance", config.fmt(values["daily_allowance"]))
    return values


def history_filter(records, user_id, key):
    mode, period, _, _ = select_period(user_id, records, key, include_all=True)
    filtered = records
    if period:
        # History includes scheduled records; dashboard actuals exclude future dates.
        from utils.budget import records_in

        filtered = records_in(records, period)
    query = st.text_input("Search descriptions", key=f"{key}_search").strip().lower()
    if query:
        filtered = [
            r for r in filtered if query in (r.get("description") or "").lower()
        ]
    if mode == "All dates":
        dates = [date.fromisoformat(str(r["date"])[:10]) for r in records]
        if dates:
            chosen = st.date_input(
                "Date range", value=(min(dates), max(dates)), key=f"{key}_dates"
            )
            if isinstance(chosen, tuple) and len(chosen) == 2:
                from utils.budget import Period, records_in

                filtered = records_in(
                    filtered, Period(chosen[0], chosen[1] + timedelta(days=1))
                )
    return filtered
