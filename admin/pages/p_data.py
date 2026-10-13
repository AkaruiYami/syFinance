import io
import zipfile
from datetime import datetime

import streamlit as st

from models.income import Income
from models.transaction import Transactions
from models.user import User
from models.wishlist import Wishlist
from utils import config
from utils.auth import require_admin, require_login
from utils.data_io import (
    MODEL_MAP,
    export_all_users_data_zip,
    import_csv,
    reset_user_data,
)

require_login()
require_admin()

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title("Data Management")
st.markdown("Backup, restore, and import data across all users.")
st.divider()

# --- Section A: Backup All Data ---
st.subheader("Backup All Data")
st.markdown("Export all user data as a single zip file.")

backup_zip = export_all_users_data_zip()
st.download_button(
    label="Download Full Backup",
    data=backup_zip,
    file_name=f"syfinance_backup_{datetime.now().strftime('%Y%m%d')}.zip",
    mime="application/zip",
)

st.divider()

# --- Section B: Restore from Backup ---
st.subheader("Restore from Backup")
st.markdown(
    "Upload a backup zip to restore records. "
    "Only records for users that still exist will be imported. "
    "Matching IDs update existing records for the same user. "
    "New IDs are preserved; records without IDs are added. "
    "Existing data is never deleted."
)

uploaded_zip = st.file_uploader("Upload backup zip", type=["zip"], key="restore_zip")

if uploaded_zip and st.button("Restore"):
    try:
        zip_bytes = uploaded_zip.read()
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            available = set(zf.namelist())
            for name, model_cls in MODEL_MAP.items():
                filename = f"{name}.csv"
                if filename not in available:
                    st.info(f"Skipping {filename}: not found in backup.")
                    continue

                with zf.open(filename) as f:
                    result = import_csv(model_cls, f)
                st.success(
                    f"**{filename}**: {result['imported']} created, "
                    f"{result['updated']} updated, {result['skipped']} skipped"
                )
                if result["errors"]:
                    with st.expander(f"Errors in {filename}"):
                        for err in result["errors"]:
                            st.text(err)

    except Exception as e:
        st.error(f"Failed to restore: {e}")

st.divider()

# --- Section C: Import CSV for a User ---
st.subheader("Import CSV for a User")
st.markdown(
    "Import a CSV file for a specific user. Matching IDs update that user's records. "
    "New IDs are preserved; leave the ID blank to create a new record. "
    "IDs belonging to another user are skipped."
)

all_users = User.objects().all()
if not all_users:
    st.warning("No users found in the database.")
else:
    user_names = {user.name: user.id for user in all_users}
    selected_name = st.selectbox("Target User", options=list(user_names.keys()))
    target_user_id = user_names[selected_name]

    model_choice = st.selectbox(
        "Data Type", options=["Income", "Transactions", "Wishlist"]
    )
    model_cls_map = {
        "Income": Income,
        "Transactions": Transactions,
        "Wishlist": Wishlist,
    }
    selected_model = model_cls_map[model_choice]

    uploaded_csv = st.file_uploader("Upload CSV", type=["csv"], key="import_csv")

    if uploaded_csv and st.button("Import"):
        result = import_csv(selected_model, uploaded_csv, target_user_id)

        col1, col2, col3 = st.columns(3)
        col1.metric("Created", result["imported"])
        col2.metric("Updated", result["updated"])
        col3.metric("Skipped", result["skipped"])

        if result["errors"]:
            with st.expander("Row-level errors"):
                for err in result["errors"]:
                    st.text(err)

        if result["imported"] + result["updated"] > 0:
            st.success(
                f"Created {result['imported']} and updated {result['updated']} rows."
            )

st.divider()
st.subheader("Reset Data")
st.markdown(
    "Permanently delete financial records for a selected user. "
    "User accounts and categories are kept. Download a backup first if needed."
)
if all_users:
    with st.form("reset_data"):
        reset_uid = st.selectbox(
            "User to reset",
            options=[user.id for user in all_users],
            format_func=lambda uid: next(
                f"{user.name} (ID {uid})" for user in all_users if user.id == uid
            ),
        )
        reset_types = {
            "All financial data": None,
            "Income": Income,
            "Transactions": Transactions,
            "Wishlist": Wishlist,
        }
        reset_type = st.selectbox("Data to delete", options=list(reset_types))
        confirmed = st.checkbox("I confirm I want to permanently delete this data")
        if st.form_submit_button("Reset Data", type="primary"):
            if not confirmed:
                st.error("Confirm deletion using the checkbox first.")
            else:
                try:
                    deleted = reset_user_data(reset_uid, reset_types[reset_type])
                    st.session_state["reset_data_message"] = (
                        f"Deleted {deleted} records."
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to reset data: {e}")
if message := st.session_state.pop("reset_data_message", None):
    st.success(message)
