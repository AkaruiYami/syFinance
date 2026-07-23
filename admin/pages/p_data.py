import csv
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
    _parse_date,
    export_all_users_data_zip,
    import_csv,
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
    "Existing data is never deleted."
)

uploaded_zip = st.file_uploader("Upload backup zip", type=["zip"], key="restore_zip")

if uploaded_zip and st.button("Restore"):
    try:
        zip_bytes = uploaded_zip.read()
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            available = set(zf.namelist())
            existing_user_ids = {u.id for u in User.objects().all()}

            for filename, model_cls in MODEL_MAP.items():
                if filename not in available:
                    st.info(f"Skipping {filename}: not found in backup.")
                    continue

                with zf.open(filename) as f:
                    reader = csv.DictReader(io.TextIOWrapper(f))
                    if not reader.fieldnames:
                        st.info(f"Skipping {filename}: empty or no header.")
                        continue

                    imported = 0
                    skipped = 0
                    errors = []
                    fieldnames_lower = {h.strip().lower(): h for h in reader.fieldnames}

                    for i, row in enumerate(reader, 1):
                        try:
                            uid_raw = row.get(
                                fieldnames_lower.get("user_id", "user_id"), ""
                            ).strip()
                            if not uid_raw:
                                skipped += 1
                                errors.append(f"Row {i}: missing user_id")
                                continue

                            uid = int(uid_raw)
                            if uid not in existing_user_ids:
                                skipped += 1
                                errors.append(
                                    f"Row {i}: user_id {uid} does not exist"
                                )
                                continue

                            kwargs = {}
                            for field_name in model_cls._fields:
                                if field_name in ("user",):
                                    continue
                                csv_col = fieldnames_lower.get(field_name)
                                if csv_col and row.get(csv_col, "").strip():
                                    value = row[csv_col].strip()
                                    field = model_cls._fields[field_name]

                                    from models.field import DateField, FloatField

                                    if isinstance(field, DateField):
                                        kwargs[field_name] = _parse_date(value)
                                    elif isinstance(field, FloatField):
                                        kwargs[field_name] = float(value)
                                    else:
                                        kwargs[field_name] = value

                            kwargs["user"] = uid
                            instance = model_cls.new(**kwargs)
                            instance.save()
                            imported += 1

                        except Exception as e:
                            skipped += 1
                            errors.append(f"Row {i}: {e}")

                st.success(f"**{filename}**: {imported} imported, {skipped} skipped")
                if errors:
                    with st.expander(f"Errors in {filename}"):
                        for err in errors:
                            st.text(err)

    except Exception as e:
        st.error(f"Failed to restore: {e}")

st.divider()

# --- Section C: Import CSV for a User ---
st.subheader("Import CSV for a User")
st.markdown("Import a CSV file for a specific user.")

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

    uploaded_csv = st.file_uploader(
        "Upload CSV", type=["csv"], key="import_csv"
    )

    if uploaded_csv and st.button("Import"):
        result = import_csv(selected_model, uploaded_csv, target_user_id)

        col1, col2 = st.columns(2)
        col1.metric("Imported", result["imported"])
        col2.metric("Skipped", result["skipped"])

        if result["errors"]:
            with st.expander("Row-level errors"):
                for err in result["errors"]:
                    st.text(err)

        if result["imported"] > 0:
            st.success(f"Successfully imported {result['imported']} rows.")
