import pandas as pd
import streamlit as st

from admin import api
from admin.components import (
    create_category_dialog,
    create_subcategory_dialog,
    delete_category_dialog,
    delete_subcategory_dialog,
    edit_category_dialog,
    edit_subcategory_dialog,
)
from utils import config
from utils.auth import require_admin, require_login

require_login()
require_admin()

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title("Category Management")
st.markdown("Add, edit, or remove expense categories and subcategories.")
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
    for cat in categories:
        usage = api.get_category_usage_count(cat.name)
        subcats = api.get_subcategories(cat.id)

        with st.expander(f"**{cat.name}** — {len(subcats)} subcategories, {usage} transactions"):
            cat_col1, cat_col2 = st.columns([0.85, 0.15])
            with cat_col2:
                if st.button("Edit", key=f"edit_cat_{cat.id}"):
                    edit_category_dialog(cat.id, cat.name)
                if st.button("Delete", key=f"del_cat_{cat.id}", type="secondary"):
                    delete_category_dialog(cat.id, cat.name)

            if subcats:
                sub_data = []
                for sub in subcats:
                    sub_usage = api.get_subcategory_usage_count(sub.name)
                    sub_data.append({
                        "ID": sub.id,
                        "Subcategory": sub.name,
                        "Transactions": sub_usage,
                    })
                sub_df = pd.DataFrame(sub_data)
                sub_editor = sub_df.copy()
                sub_editor.insert(0, "Select", False)

                edited_subs = st.data_editor(
                    sub_editor,
                    disabled=["ID", "Subcategory", "Transactions"],
                    hide_index=True,
                    key=f"sub_editor_{cat.id}",
                )

                selected_sub_ids = edited_subs.loc[edited_subs["Select"], "ID"].tolist()
                selected_sub_names = edited_subs.loc[
                    edited_subs["Select"], "Subcategory"
                ].tolist()

                sub_btn1, sub_btn2 = st.columns(2)
                with sub_btn1:
                    if st.button("Edit Subcategory", key=f"edit_sub_btn_{cat.id}"):
                        if len(selected_sub_ids) != 1:
                            st.warning("Select exactly one subcategory to edit.")
                        else:
                            edit_subcategory_dialog(
                                selected_sub_ids[0], selected_sub_names[0]
                            )
                with sub_btn2:
                    if st.button("Delete Subcategory", key=f"del_sub_btn_{cat.id}"):
                        if not selected_sub_ids:
                            st.info("Select at least one subcategory to delete.")
                        elif len(selected_sub_ids) == 1:
                            delete_subcategory_dialog(
                                selected_sub_ids[0], selected_sub_names[0]
                            )
                        else:
                            for sid, sname in zip(selected_sub_ids, selected_sub_names):
                                try:
                                    api.delete_subcategory(sid)
                                except ValueError as e:
                                    st.error(f"Cannot delete '{sname}': {e}")
                            st.rerun()
            else:
                st.info("No subcategories yet.")

            if st.button("Add Subcategory", key=f"add_sub_btn_{cat.id}"):
                create_subcategory_dialog(cat.id, cat.name)
