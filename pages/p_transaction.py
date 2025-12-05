import pandas as pd
import streamlit as st
from datetime import date

from components import paginated_table
from utils import config
from models.transaction import Transactions


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
    new_transaction = Transactions.new(
        date=trans_date,
        category=str(category),
        amount=float(amount),
        description=str(description),
    )
    new_transaction.save()
    st.success("Transaction added!")

st.divider()
st.subheader("Transaction History")

records = Transactions.objects().all(order_by="date")

if records:
    df = pd.DataFrame([rec.to_dict() for rec in records])
    df["amount"] = (
        df["amount"].astype(float).map(lambda x: f"{config.CURRENCY} {x:.2f}")
    )
    df.set_index("id", inplace=True)

    paginated_table(df, MAX_ITEM_PER_PAGE, table_id="trans_rec")

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

        st.write(f"### {period} Spending")
        # st.bar_chart(pivot)
        st.line_chart(pivot)
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
            agg["amount"] = agg["amount"].map(lambda x: f"{config.CURRENCY} {x:.2f}")
            paginated_table(agg, MAX_ITEM_PER_PAGE, table_id="trans_aggr")

        else:  # Show Individually
            summary_table = summary.copy()
            summary_table["amount"] = summary_table["amount"].map(
                lambda x: f"{config.CURRENCY} {x:.2f}"
            )
            paginated_table(summary_table, MAX_ITEM_PER_PAGE, table_id="trans_ind")

    else:
        st.info("No transactions yet to summarize.")


summary_section()
