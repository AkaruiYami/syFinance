from datetime import date
import pandas as pd
import streamlit as st

from models.wishlist import Wishlist
from utils import config

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title("Target")
st.markdown("List down your target, goal, or wishlist.")
st.divider()

with st.form("add_wishlist", clear_on_submit=True):
    item_name = st.text_input("Item Name")
    amount = st.number_input(f"Amount ({config.CURRENCY})", min_value=0.0, step=0.10)
    source = st.text_input("Source")
    description = st.text_input("Description")
    submitted = st.form_submit_button("Add Item")

if submitted and not item_name:
    st.warning("Item name cannot be empty.")
elif submitted and not amount:
    st.warning("Amount cannot be empty.")
elif submitted:
    date_submitted = date.today()
    new_data = {
        "dateCreated": str(date_submitted),
        "name": str(item_name),
        "amount": float(amount),
        "source": str(source),
        "description": str(description),
        "status": "NOT COMPLETE",
    }
    Wishlist.insert(new_data)

st.divider()
st.subheader("Wishlist")


@st.fragment
def wishlist_listing_section():
    wishlist = Wishlist.all(order="desc")

    if wishlist:
        df = pd.DataFrame(wishlist)
        df_display = df.drop("id", axis=1)
        st.table(df_display)

        # -----------------------------
        # Update Item Status
        # -----------------------------
        st.markdown("### Update Item Status")
        selected_item = st.selectbox("Select Item", df["name"].tolist())
        new_status = st.selectbox("New Status", Wishlist.STATUS)

        if st.button("Update Status"):
            # Find the selected item's ID
            item_id = int(df[df["name"] == selected_item]["id"].values[0])  # pyright: ignore
            Wishlist.update(item_id, {"status": new_status})
            st.success(f"Status of '{selected_item}' updated to {new_status}.")
            st.rerun(scope="fragment")
    else:
        st.info("No item in wishlist yet.")


wishlist_listing_section()
