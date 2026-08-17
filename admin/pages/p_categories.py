import pandas as pd
import streamlit as st

from admin import api
from admin.components import (
    create_category_dialog,
    delete_category_dialog,
    edit_category_dialog,
)
from utils import config
from utils.auth import require_admin, require_login

require_login()
require_admin()

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title("Category Management")
st.markdown("Add, edit, or remove expense categories.")
st.divider()

categories = api.get_categories()

col1, col2 = st.columns([0.15, 0.85])
with col1:
    add_button = st.button("Add Category")

if add_button:
    create_category_dialog()

if not categories:
    st.info("No categories defined yet. Add one to get started.")
else:
    data = []
    for cat in categories:
        usage = api.get_category_usage_count(cat.name)
        data.append({"ID": cat.id, "Category": cat.name, "Transactions": usage})

    df = pd.DataFrame(data)
    df_editor = df.copy()
    df_editor.insert(0, "Select", False)

    edited = st.data_editor(
        df_editor,
        disabled=["ID", "Category", "Transactions"],
        hide_index=True,
    )

    selected_ids = edited.loc[edited["Select"], "ID"].tolist()
    selected_names = edited.loc[edited["Select"], "Category"].tolist()

    if selected_ids:
        st.dataframe(
            df[df["ID"].isin(selected_ids)], hide_index=True
        )

    edit_button = st.button("Edit")
    delete_button = st.button("Delete")

    if edit_button:
        if len(selected_ids) != 1:
            st.warning("Select exactly one category to edit.")
        else:
            edit_category_dialog(selected_ids[0], selected_names[0])

    if delete_button:
        if not selected_ids:
            st.info("Select at least one category to delete.")
        elif len(selected_ids) == 1:
            delete_category_dialog(selected_ids[0], selected_names[0])
        else:
            for cid, cname in zip(selected_ids, selected_names):
                try:
                    api.delete_category(cid)
                except ValueError as e:
                    st.error(f"Cannot delete '{cname}': {e}")
            st.rerun()
