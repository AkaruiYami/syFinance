import csv
import io
import zipfile
from datetime import datetime

from models.field import DateField, FloatField
from models.income import Income
from models.transaction import Transactions
from models.user import User
from models.wishlist import Wishlist

MODEL_MAP = {
    "income": Income,
    "transactions": Transactions,
    "wishlist": Wishlist,
}

REQUIRED_COLUMNS = {
    Income: ["date", "amount"],
    Transactions: ["date", "category", "amount"],
    Wishlist: ["name", "amount"],
}

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]


def _parse_date(value):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            continue
    raise ValueError(f"Invalid date: '{value}'. Expected one of: {', '.join(DATE_FORMATS)}")


def _get_csv_columns(model_cls):
    return list(model_cls._fields.keys())


def _record_to_csv_row(record, model_cls):
    record_dict = record.to_dict()
    row = {}
    for col in _get_csv_columns(model_cls):
        if col in record_dict:
            row[col] = record_dict[col]
        else:
            fk_key = f"{col}_id"
            row[col] = record_dict.get(fk_key)
    row["id"] = record.id
    return row


def export_model_csv(model_cls, user_id):
    records = model_cls.objects().filter(user_id=user_id).all()
    columns = ["id"] + _get_csv_columns(model_cls)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()

    for record in records:
        row = _record_to_csv_row(record, model_cls)
        writer.writerow(row)

    return output.getvalue().encode("utf-8")


def export_all_user_data_zip(user_id):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, model_cls in MODEL_MAP.items():
            csv_bytes = export_model_csv(model_cls, user_id)
            zf.writestr(f"{name}.csv", csv_bytes)
    return buf.getvalue()


def export_all_users_data_zip():
    users = User.objects().all()
    user_map = {user.id: user.name for user in users}

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Users roster
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "name", "email", "role"])
        writer.writeheader()
        for user in users:
            writer.writerow({
                "id": user.id,
                "name": user.name,
                "email": user.email or "",
                "role": user.role or "user",
            })
        zf.writestr("users.csv", output.getvalue().encode("utf-8"))

        # Per-model exports with user_id and user_name tags
        for name, model_cls in MODEL_MAP.items():
            records = model_cls.objects().all()
            columns = ["user_id", "user_name", "id"] + _get_csv_columns(model_cls)

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()

            for record in records:
                row = _record_to_csv_row(record, model_cls)
                uid = row.pop("user", None) or row.pop("user_id", None)
                row["user_id"] = uid
                row["user_name"] = user_map.get(uid, "")
                writer.writerow(row)

            zf.writestr(f"{name}.csv", output.getvalue().encode("utf-8"))

    return buf.getvalue()


def import_csv(model_cls, file, user_id):
    result = {"imported": 0, "skipped": 0, "errors": []}

    try:
        content = file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
    except Exception as e:
        result["errors"].append(f"Failed to read file: {e}")
        return result

    reader = csv.DictReader(io.StringIO(content))

    # Validate required columns
    required = REQUIRED_COLUMNS.get(model_cls, [])
    if reader.fieldnames is None:
        result["errors"].append("CSV file is empty or has no header row.")
        return result

    header_lower = [h.strip().lower() for h in reader.fieldnames]
    missing = [col for col in required if col not in header_lower]
    if missing:
        result["errors"].append(f"Missing required columns: {', '.join(missing)}")
        return result

    # Build index map for case-insensitive access
    col_index = {h.strip().lower(): h for h in reader.fieldnames}

    for i, row in enumerate(reader, 1):
        try:
            kwargs = {}

            # Map required and optional columns
            for field_name in model_cls._fields:
                if field_name in ("user",):
                    continue
                csv_col = col_index.get(field_name)
                if csv_col and row.get(csv_col, "").strip():
                    value = row[csv_col].strip()
                    field = model_cls._fields[field_name]

                    if isinstance(field, DateField):
                        kwargs[field_name] = _parse_date(value)
                    elif isinstance(field, FloatField):
                        kwargs[field_name] = float(value)
                    else:
                        kwargs[field_name] = value

            # Validate required fields are present
            for col in required:
                if col not in kwargs or kwargs[col] is None:
                    raise ValueError(f"Required field '{col}' is missing or empty")

            # Set the user FK
            kwargs["user"] = user_id

            instance = model_cls.new(**kwargs)
            instance.save()
            result["imported"] += 1

        except Exception as e:
            result["skipped"] += 1
            result["errors"].append(f"Row {i}: {e}")

    return result
