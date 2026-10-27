from datetime import date, datetime

import pandas as pd
import streamlit as st

from components.budget_view import history_filter
from models.category import Category
from models.subcategory import Subcategory
from models.transaction import Transactions
from utils import config
from utils.auth import require_login
from utils.budget import available_periods, load_policies, period_for
from utils.data_io import export_model_csv

require_login()

MAX_ITEM_PER_PAGE = 10

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title("Transactions")
st.markdown("View, add, and manage your financial transactions here.")
st.divider()

# Category changes must rerun the page to refresh the available subcategories.
entry_key = f"transaction_entry_{st.session_state.get('transaction_entry_number', 0)}"
trans_date = st.date_input("Date", value=date.today(), key=f"{entry_key}_date")
categories = Category.objects().all(order_by="name")
cat_names = [c.name for c in categories] if categories else ["Other"]
category = st.selectbox("Category", cat_names, key=f"{entry_key}_category")
selected_cat = next((c for c in categories if c.name == category), None)
subcats = (
    Subcategory.objects().filter(category_id=selected_cat.id).all(order_by="name")
    if selected_cat
    else []
)
subcat_names = [s.name for s in subcats]
subcategory = None
if subcat_names:
    subcategory = st.selectbox(
        "Subcategory (optional)",
        ["—"] + subcat_names,
        key=f"{entry_key}_subcategory_{category}",
    )
    if subcategory == "—":
        subcategory = None
amount = st.number_input(
    f"Amount ({config.CURRENCY})",
    min_value=0.0,
    step=0.10,
    key=f"{entry_key}_amount",
)
description = st.text_area("Description", key=f"{entry_key}_description")
submitted = st.button("Add Transaction")

if submitted:
    if amount <= 0:
        st.warning("Amount must be greater than zero.")
    elif not description.strip():
        st.warning("Please add a description.")
    else:
        new_transaction = Transactions.new(
            date=trans_date,
            category=str(category),
            subcategory=subcategory,
            amount=float(amount),
            description=str(description),
            user=int(st.session_state.user_id),
        )
        new_transaction.save()
        st.session_state.transaction_entry_number = (
            st.session_state.get("transaction_entry_number", 0) + 1
        )
        st.toast("Transaction added!")
        st.rerun()

st.divider()
st.subheader("Transaction History")

records = (
    Transactions.objects()
    .filter(user_id=int(st.session_state.user_id))
    .all(order_by="date")
)

if records:
    history_records = history_filter(
        [rec.to_dict() for rec in records],
        int(st.session_state.user_id),
        "transaction_history",
    )
    df = pd.DataFrame(
        history_records,
        columns=["id", "date", "amount", "category", "subcategory", "description"],
    )
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float).map(config.fmt)
    df.set_index("id", inplace=True)
    df = df.sort_values("date", ascending=False)

    # paginated_table(df, MAX_ITEM_PER_PAGE, table_id="trans_rec")
    st.dataframe(
        df, column_config={"date": st.column_config.DateColumn(format="YYYY-MM-DD")}
    )

    st.divider()
    st.subheader("Export Data")
    csv_data = export_model_csv(Transactions, int(st.session_state.user_id))
    st.download_button(
        label="Download Transactions CSV",
        data=csv_data,
        file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

else:
    st.info("No transactions recorded yet.")

st.divider()
st.subheader("Summary")


@st.fragment
def summary_section():
    if records and history_records:
        df = pd.DataFrame(history_records)
        df["amount"] = df["amount"].astype(float)
        df["date"] = pd.to_datetime(df["date"])

        policies = load_policies(int(st.session_state.user_id))
        period = st.selectbox(
            "View spending by:",
            (["Payday cycle"] if policies else [])
            + [
                "Daily",
                "Weekly",
                "Monthly",
                "Yearly",
            ],
        )

        if period == "Payday cycle":
            df["period"] = df["date"].map(
                lambda value: period_for(value.date(), "Payday cycle", policies).label
            )
        elif period == "Daily":
            df["period"] = df["date"].dt.to_period("D").astype(str)
        elif period == "Weekly":
            df["period"] = df["date"].dt.to_period("W").astype(str)
        elif period == "Monthly":
            df["period"] = df["date"].dt.to_period("M").astype(str)
        elif period == "Yearly":
            df["period"] = df["date"].dt.to_period("Y").astype(str)

        st.write("### Filter by Category")
        all_categories = sorted(df["category"].unique())
        selected_categories = []

        MAX_CAT_PER_ROW = 5
        cols = st.columns(MAX_CAT_PER_ROW)
        for i, cat in enumerate(all_categories):
            with cols[i % MAX_CAT_PER_ROW]:
                if st.checkbox(cat, value=True, key=f"cat_{cat}"):
                    selected_categories.append(cat)

        if not selected_categories:
            selected_categories = all_categories

        show_subcats = st.checkbox(
            "Show subcategory breakdown", key="txn_subcat_toggle"
        )

        df_filtered = df[df["category"].isin(selected_categories)]

        if show_subcats:
            df_filtered = df_filtered.copy()
            df_filtered["subcategory"] = df_filtered["subcategory"].fillna(
                "(Uncategorized)"
            )
            label_col = "cat_sub_label"
            df_filtered[label_col] = (
                df_filtered["category"] + " > " + df_filtered["subcategory"]
            )
            summary = (
                df_filtered.groupby(["period", label_col])["amount"]
                .sum()
                .reset_index()
                .sort_values(["period", label_col])
            )
            pivot = summary.pivot(
                index="period", columns=label_col, values="amount"
            ).fillna(0)
        else:
            summary = (
                df_filtered.groupby(["period", "category"])["amount"]
                .sum()
                .reset_index()
                .sort_values(["period", "category"])
            )
            pivot = summary.pivot(
                index="period", columns="category", values="amount"
            ).fillna(0)

        # build full period range
        start = df["date"].min()
        end = df["date"].max()

        if period == "Payday cycle":
            full_periods = [
                item.label
                for item in available_periods(
                    history_records,
                    "Payday cycle",
                    policies,
                    today=max(date.today(), end.date()),
                )
                if item.start <= end.date()
            ]
        elif period == "Daily":
            full_periods = pd.period_range(start, end, freq="D").astype(str)
        elif period == "Weekly":
            full_periods = pd.period_range(start, end, freq="W").astype(str)
        elif period == "Monthly":
            full_periods = pd.period_range(start, end, freq="M").astype(str)
        elif period == "Yearly":
            full_periods = pd.period_range(start, end, freq="Y").astype(str)

        pivot = pivot.reindex(full_periods, fill_value=0)  # pyright: ignore

        line_tab, bar_tab = st.tabs(["Line", "Bar"])
        st.write(f"### {period} Spending")
        with line_tab:
            st.line_chart(pivot)
        with bar_tab:
            st.bar_chart(pivot)
        table_mode = st.selectbox(
            "Table Display Mode:", ["Show Aggregate", "Show Individually"]
        )

        st.write("### Summary Table")
        if table_mode == "Show Aggregate":
            agg = (
                df_filtered.groupby("period")["amount"]
                .sum()
                .reset_index()
                .sort_values("period")
            )
            agg["amount"] = agg["amount"].map(config.fmt)
            st.dataframe(agg)

        else:  # Show Individually
            summary_table = summary.copy()
            summary_table["amount"] = summary_table["amount"].map(config.fmt)
            st.dataframe(summary_table)

    else:
        st.info("No transactions yet to summarize.")


summary_section()
