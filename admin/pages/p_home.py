import pandas as pd
import streamlit as st

from admin import api
from admin.components import create_user_dialog, delete_user_dialog, edit_user
from utils import config
from utils.auth import require_login, require_admin

require_login()
require_admin()

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title(config.APP_NAME)
st.markdown("Under construction")
st.divider()

users = api.get_users()
n_user = len(users)
st.metric("Number of User", n_user)

with st.container():
    col1, col2, col3, col4 = st.columns([0.1, 0.1, 0.1, 0.7])
    with col1:
        del_button = st.button("Delete User")
    with col2:
        create_button = st.button("Create User")
    with col3:
        modify_button = st.button("Modify User")
    with col4:
        st.space("stretch")


with st.container():
    data = {}
    data["User ID"] = [user.id for user in users]
    data["Name"] = [user.name for user in users]
    data["Email"] = [user.email or "" for user in users]
    data["Description"] = [user.description or "" for user in users]
    data["Role"] = [user.role or "user" for user in users]
    df = pd.DataFrame(data)

    df2 = df.copy()
    df2.insert(0, "Select", False)

    edited = st.data_editor(
        df2,
        disabled=[
            "User ID",
            "Name",
            "Email",
            "Description",
        ],  # keep columns read-only except Select and Role
        hide_index=True,
    )

    selected_user_ids = edited.loc[edited["Select"], "User ID"].tolist()
    selected_user_names = edited.loc[edited["Select"], "Name"].tolist()

    if selected_user_ids:
        st.dataframe(df[df["User ID"].isin(selected_user_ids)], hide_index=True)


if create_button:
    create_user_dialog()


if del_button:
    if not selected_user_ids:
        st.info("Select at least one user to delete.")
    else:
        delete_user_dialog(selected_user_ids, selected_user_names)


if modify_button:
    if len(selected_user_ids) != 1:
        st.warning("Make sure to select exactly one user to modify.")
    else:
        edit_user(selected_user_ids[0])
