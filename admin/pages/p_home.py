import altair as alt
import pandas as pd
import streamlit as st

from admin import api
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
    df = pd.DataFrame(data)

    df2 = df.copy()
    df2.insert(0, "Select", False)

    edited = st.data_editor(
        df2,
        disabled=["User ID", "Name"],  # keep columns read-only except Select
        hide_index=True,
    )

    selected_user_ids = edited.loc[edited["Select"], "User ID"].tolist()

    if selected_user_ids:
        st.dataframe(df[df["User ID"].isin(selected_user_ids)], hide_index=True)


@st.dialog("Create User")
def create_user_dialog():
    with st.form("create_user_form", clear_on_submit=True):
        name = st.text_input("Name", placeholder="e.g. AkaruiYami")
        password = st.text_input("Password", type="password")
        email = st.text_input("Email")
        desc = st.text_input("Descrtiption")

        submitted = st.form_submit_button("Create")
        if submitted:
            name = name.strip()
            if not name:
                st.error("Name is required.")
                st.stop()

            password = password.strip()
            if not password:
                st.error("Password is required.")
                st.stop()

            try:
                api.create_user(name, password, email, desc)
                st.success(f"User '{name}' created.")
                st.rerun()  # refresh table + metrics
            except Exception as e:
                st.error(f"Failed to create user: {e}")


if create_button:
    create_user_dialog()
