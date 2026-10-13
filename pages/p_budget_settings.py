from datetime import date

import streamlit as st

from utils.auth import require_login
from utils.budget import cancel_pending, load_policies, period_for, save_settings

require_login()
st.set_page_config(page_title="Budget Settings", layout="wide")
st.title("Budget Settings")
st.markdown(
    "Choose when your salary-funded spending cycle starts. Calendar-month reports "
    "and the dates on your records remain available."
)
user_id = int(st.session_state.user_id)
today = date.today()
policies = load_policies(user_id)
active = [p for p in policies if p.effective_date <= today]
pending = [p for p in policies if p.effective_date > today]
current = active[-1] if active else None
if current:
    st.info(
        f"Current cycle: {period_for(today, 'Payday cycle', policies).label}. "
        f"Start day {current.start_day}; savings target {current.savings_percent:g}%."
    )
    st.caption(
        "Changes apply from the next cycle; previous settings remain in history."
    )
else:
    st.info(
        "First setup applies to all existing history. It does not change your records "
        "or calendar-month reports."
    )
if pending:
    scheduled = pending[0]
    st.info(
        f"Scheduled for {scheduled.effective_date:%d %b %Y}: "
        f"start day {scheduled.start_day}, target {scheduled.savings_percent:g}%. "
        "Changing payday may create a shorter transition cycle."
    )
    if st.button("Cancel pending change"):
        cancel_pending(user_id)
        st.rerun()
defaults = pending[0] if pending else current
with st.form("budget_settings"):
    day = st.number_input(
        "Monthly cycle start day",
        min_value=1,
        max_value=31,
        value=defaults.start_day if defaults else 1,
        step=1,
    )
    st.caption("If the date is missing in a month, use that month's last day.")
    target = st.number_input(
        "Savings target (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(defaults.savings_percent) if defaults else 20.0,
        step=1.0,
    )
    if st.form_submit_button("Save budget settings", type="primary"):
        try:
            effective = save_settings(user_id, day, target)
            st.session_state["budget_saved"] = (
                "Budget settings applied to your history."
                if effective == date.min
                else f"Budget settings scheduled for {effective:%d %b %Y}."
            )
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
if message := st.session_state.pop("budget_saved", None):
    st.success(message)
if policies:
    st.subheader("Settings history")
    st.table(
        [
            {
                "Effective from": "Initial history"
                if p.effective_date == date.min
                else p.effective_date.isoformat(),
                "Start day": p.start_day,
                "Savings target (%)": p.savings_percent,
                "Status": "Pending"
                if p.effective_date > today
                else "Active"
                if p == current
                else "Previous",
            }
            for p in policies
        ]
    )
