import pandas as pd
import streamlit as st
from datetime import date, datetime

from utils import config
from models.transaction import Transactions
from utils.data_io import export_model_csv


from utils.auth import require_login

require_login()

MAX_ITEM_PER_PAGE = 10

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title("Transactions")
st.markdown("View, add, and manage your financial transactions here.")
st.divider()

# Add transaction form
with st.form("add_transaction", clear_on_submit=True):
    trans_date = st.date_input("Date", value=date.today())
    category = st.selectbox(
        "Category",
        ["Food", "Transport", "Bills", "Shopping", "Entertainment", "Other"],
    )
    amount = st.number_input(f"Amount ({config.CURRENCY})", min_value=0.0, step=0.10)
    description = st.text_area("Description")
    submitted = st.form_submit_button("Add Transaction")

if submitted:
    if amount <= 0:
        st.warning("Amount must be greater than zero.")
    elif not description.strip():
        st.warning("Please add a description.")
    else:
        new_transaction = Transactions.new(
            date=trans_date,
            category=str(category),
            amount=float(amount),
            description=str(description),
            user=int(st.session_state.user_id),
        )
        new_transaction.save()
        st.success("Transaction added!")

st.divider()
st.subheader("Transaction History")

records = (
    Transactions.objects()
    .filter(user_id=int(st.session_state.user_id))
    .all(order_by="date")
)

if records:
    df = pd.DataFrame([rec.to_dict() for rec in records])
    df = df.drop("user_id", axis=1)
    df["amount"] = (
        df["amount"].astype(float).map(config.fmt)
    )
    df.set_index("id", inplace=True)
    df = df.sort_values("date", ascending=False)

    # paginated_table(df, MAX_ITEM_PER_PAGE, table_id="trans_rec")
    st.dataframe(df)

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
    st.info("Table will display recorded transactions once persistence is added.")

st.divider()
st.subheader("Summary")


@st.fragment
def summary_section():
    if records:
        df = pd.DataFrame([rec.to_dict() for rec in records])
        df["amount"] = df["amount"].astype(float)
        df["date"] = pd.to_datetime(df["date"])

        period = st.selectbox(
            "View spending by:",
            [
                "Daily",
                "Weekly",
                "Monthly",
                "Yearly",
            ],
        )

        if period == "Daily":
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

        df_filtered = df[df["category"].isin(selected_categories)]
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

        if period == "Daily":
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
