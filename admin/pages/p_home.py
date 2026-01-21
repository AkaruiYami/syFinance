import pandas as pd
import streamlit as st

from admin import api
from admin.components import create_user_dialog, delete_user_dialog
from utils import config
from utils.auth import require_login

require_login()

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title(config.APP_NAME)
st.markdown("Under construction")
st.divider()

users = api.get_users()
n_user = len(users)
st.metric("Number of User", n_user)

with st.container():
    col1, col2, col3 = st.columns([0.1, 0.1, 0.8])
    with col1:
        del_button = st.button("Delete User")
    with col2:
        create_button = st.button("Create User")
    with col3:
        st.space("stretch")


with st.container():
    data = {}
    data["User ID"] = [user.id for user in users]
    data["Name"] = [user.name for user in users]
    data["Email"] = [user.email for user in users]
    data["Descrtiption"] = [user.description for user in users]
    df = pd.DataFrame(data)

    df2 = df.copy()
    df2.insert(0, "Select", False)

    edited = st.data_editor(
        df2,
        disabled=[
            "User ID",
            "Name",
            "Email",
            "Descrtiption",
        ],  # keep columns read-only except Select
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
