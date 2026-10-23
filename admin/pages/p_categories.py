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

categories = api.get_categories()

_, action_col = st.columns([0.8, 0.2])
with action_col:
    add_button = st.button("Add Category", type="primary", use_container_width=True)

if add_button:
    create_category_dialog()

if not categories:
    st.info("No categories defined yet. Add one to get started.")
else:
    for cat in categories:
        usage = api.get_category_usage_count(cat.name)
        subcats = api.get_subcategories(cat.id)

        with st.expander(
            f"**{cat.name}** · {len(subcats)} subcategories · {usage} transactions"
        ):
            action_add, action_edit, action_delete = st.columns([0.5, 0.25, 0.25])
            with action_add:
                if st.button(
                    "Add Subcategory",
                    key=f"add_sub_btn_{cat.id}",
                    type="primary",
                    use_container_width=True,
                ):
                    create_subcategory_dialog(cat.id, cat.name)
            with action_edit:
                if st.button("Edit Category", key=f"edit_cat_{cat.id}"):
                    edit_category_dialog(cat.id, cat.name)
            with action_delete:
                if st.button("Delete Category", key=f"del_cat_{cat.id}"):
                    delete_category_dialog(cat.id, cat.name)

            if subcats:
                sub_data = []
                for sub in subcats:
                    sub_usage = api.get_subcategory_usage_count(sub.name)
                    sub_data.append(
                        {
                            "ID": sub.id,
                            "Subcategory": sub.name,
                            "Transactions": sub_usage,
                        }
                    )
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

                edit_col, delete_col, _ = st.columns([0.25, 0.25, 0.5])
                with edit_col:
                    if st.button(
                        "Edit Selected",
                        key=f"edit_sub_btn_{cat.id}",
                        use_container_width=True,
                    ):
                        if len(selected_sub_ids) != 1:
                            st.warning("Select exactly one subcategory to edit.")
                        else:
                            edit_subcategory_dialog(
                                selected_sub_ids[0], selected_sub_names[0]
                            )
                with delete_col:
                    if st.button(
                        "Delete Selected",
                        key=f"del_sub_btn_{cat.id}",
                        use_container_width=True,
                    ):
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
