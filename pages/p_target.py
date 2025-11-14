from datetime import date
import pandas as pd
import streamlit as st

from models.wishlist import Wishlist
from utils import config


from utils.auth import require_login

require_login()

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title("Target")
st.markdown("List down your target, goal, or wishlist.")
st.divider()

with st.form("add_wishlist", clear_on_submit=True):
    item_name = st.text_input("Item Name")
    amount = st.number_input(f"Amount ({config.CURRENCY})", min_value=0.0, step=0.10)
    source = st.text_input("Source")
    description = st.text_area("Description")
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


def truncate_text(text, length=50):
    if len(text) > length:
        return text[:length] + "..."
    return text


@st.fragment
def wishlist_listing_section():
    wishlist = Wishlist.all(order="desc")

    if wishlist:
        df = pd.DataFrame(wishlist)
        df_display = df.drop("id", axis=1)

        page_size = 5
        total_items = len(df_display)
        total_pages = (total_items - 1) // page_size + 1

        if "wishlist_page" not in st.session_state:
            st.session_state.wishlist_page = 1

        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            if st.button("Previous") and st.session_state.wishlist_page > 1:
                st.session_state.wishlist_page -= 1
        with col3:
            if st.button("Next") and st.session_state.wishlist_page < total_pages:
                st.session_state.wishlist_page += 1
        with col2:
            st.html(
                f"<p style='text-align: center;'>{st.session_state.wishlist_page} of {total_pages}</p>"
            )

        start_idx = (st.session_state.wishlist_page - 1) * page_size
        end_idx = start_idx + page_size
        page_df = df_display.iloc[start_idx:end_idx]

        st.write("### Wishlist Items")
        for idx, row in page_df.iterrows():
            with st.container(border=True):
                # Container with border, padding, margin, and rounded corners using HTML + CSS
                st.markdown(f"**Name:** {row['name']}")
                st.markdown(f"**Date Created:** {row['dateCreated']}")
                st.markdown(f"**Amount:** {config.CURRENCY} {row['amount']:.2f}")

                truncated_source = truncate_text(row["source"])
                with st.expander(f"Source (click to expand)"):
                    st.write(row["source"])
                st.write(f"Preview: {truncated_source}")

                truncated_description = truncate_text(row["description"])
                with st.expander(f"Description (click to expand)"):
                    st.write(row["description"])
                st.write(f"Preview: {truncated_description}")

                st.markdown(f"**Status:** {row['status']}")
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        # -----------------------------
        # Update Item Status
        # -----------------------------
        st.markdown("### Update Item Status")
        selected_item = st.selectbox("Select Item", df["name"].tolist())
        new_status = st.selectbox("New Status", Wishlist.STATUS)

        if st.button("Update Status"):
            item_id = int(df[df["name"] == selected_item]["id"].values[0])  # pyright: ignore
            Wishlist.update(item_id, {"status": new_status})
            st.success(f"Status of '{selected_item}' updated to {new_status}.")
            st.rerun(scope="fragment")

    else:
        st.info("No item in wishlist yet.")


wishlist_listing_section()
