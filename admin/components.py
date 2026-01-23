import streamlit as st

from admin import api


@st.dialog("Create User")
def create_user_dialog():
    with st.form("create_user_form", clear_on_submit=True):
        name = st.text_input("Name", placeholder="e.g. username")
        password = st.text_input("Password", type="password")
        email = st.text_input("Email")
        desc = st.text_input("Description")

        # Role selection
        role_options = ["user", "admin"]
        selected_role = st.selectbox("Role", role_options, index=0)
        custom_role = st.text_input(
            "Custom Role (optional)", placeholder="Enter custom role..."
        )
        final_role = custom_role.strip() if custom_role.strip() else selected_role

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

            if not final_role:
                st.error("Role is required.")
                st.stop()

            try:
                api.create_user(name, password, email, desc, final_role)
                st.success(f"User '{name}' created with role '{final_role}'.")
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


@st.dialog("Edit user")
def edit_user(user_id: int):
    user = api.get_user(user_id)

    with st.form("edit_user_form", clear_on_submit=True):
        name = st.text_input("Name", value=user.name) or ""
        password = st.text_input(
            "New Password", placeholder="Leave empty to keep current password..."
        )
        email = st.text_input("Email", value=user.email or "")
        desc = st.text_input("Description", value=user.description or "")

        # Role management
        current_role = user.role or "user"
        role_options = ["user", "admin"]
        selected_role = st.selectbox(
            "Role",
            role_options,
            index=role_options.index(current_role)
            if current_role in role_options
            else 0,
        )
        custom_role = st.text_input(
            "Custom Role (optional)",
            placeholder="Enter custom role...",
            value=current_role if current_role not in role_options else "",
        )
        final_role = custom_role.strip() if custom_role.strip() else selected_role

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

            # Check role modification permissions
            if final_role != current_role and not api.can_modify_user_role(
                user_id, final_role
            ):
                st.error("You cannot modify this user's role.")
                st.stop()

            user.name = name
            if password:
                user.password = password
            user.email = email.strip() if email else ""
            user.description = desc.strip() if desc else ""
            user.role = final_role

            try:
                user.save()
                # Update session state if editing current user
                if st.session_state.get("user_id") == user_id:
                    st.session_state.user_role = final_role
                st.success(f"User '{name}' has been modified.")
                st.rerun()  # refresh table + metrics
            except Exception as e:
                st.error(f"Failed to modify user: {e}")
