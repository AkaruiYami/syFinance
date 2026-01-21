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


@st.dialog("Create User")
def create_user_dialog():
    with st.form("create_user_form", clear_on_submit=True):
        name = st.text_input("Name", placeholder="e.g. username")
        password = st.text_input("Password", type="password")
        email = st.text_input("Email")
        desc = st.text_input("Descrtiption")

        submitted = st.form_submit_button("Create")
        if submitted:
            name = name.strip()
            if not name:
                st.error("Name is required.")
                st.stop()
            if not api.validate_username_is_unique(name):
                st.error(f"Name '{name}' already exist. It must be unique.")
                st.stop()
            if not api.is_username_valid(name):
                st.error(
                    f"Cannot use '{name}' as your username. Choose something else."
                )
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


@st.dialog("Confirm delete")
def delete_user_dialog(user_ids: list, user_names: list):
    # Message
    if len(user_names) == 1:
        st.warning(f"Are you sure you want to delete **{user_names[0]}**?")
    else:
        st.warning("Are you sure you want to delete these users?")
        for n in user_names:
            st.write(f"- {n}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel"):
            st.rerun()

    with col2:
        if st.button("Delete", type="primary"):
            try:
                for uid in user_ids:
                    api.delete_user(uid)
                st.success("Deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete: {e}")


if create_button:
    create_user_dialog()


if del_button:
    if not selected_user_ids:
        st.info("Select at least one user to delete.")
    else:
        delete_user_dialog(selected_user_ids, selected_user_names)
