import streamlit as st

from admin import api


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


# TODO: finish the implementation of modifying user
# maybe we need to enable edit model attribute value
@st.dialog("Edit user")
def edit_user(user_id: int):
    user = api.get_user(user_id)

    with st.form("create_user_form", clear_on_submit=True):
        name = st.text_input("Name", value=user.name) or ""
        password = st.text_input("New Password", placeholder="Enter new password...")
        email = st.text_input("Email", value=user.email)
        desc = st.text_input("Descrtiption", value=user.description)

        if password:
            password = api.create_new_password(password.strip())

        submitted = st.form_submit_button("Save")
        if submitted:
            name = name.strip()
            if not name:
                st.error("Name is required.")
                st.stop()
            if not api.validate_username_is_unique(name) and name != user.name:
                st.error(f"Name '{name}' already exist. It must be unique.")
                st.stop()
            if not api.is_username_valid(name) and name != user.name:
                st.error(
                    f"Cannot use '{name}' as your username. Choose something else."
                )
                st.stop()

            user.name = name
            if password:
                user.password = password
            if email:
                user.email = email
            if desc:
                user.description = desc

            try:
                user.save()
                st.success(f"User '{name}' has been modified.")
                st.rerun()  # refresh table + metrics
            except Exception as e:
                st.error(f"Failed to create user: {e}")
