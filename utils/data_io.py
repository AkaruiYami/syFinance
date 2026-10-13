import csv
import io
import sqlite3
import zipfile
from datetime import datetime

from models.budget_policy import BudgetPolicy
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
    raise ValueError(
        f"Invalid date: '{value}'. Expected one of: {', '.join(DATE_FORMATS)}"
    )


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
        zf.writestr("budget_policies.csv", export_model_csv(BudgetPolicy, user_id))
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
            writer.writerow(
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email or "",
                    "role": user.role or "user",
                }
            )
        zf.writestr("users.csv", output.getvalue().encode("utf-8"))

        # Per-model exports with user_id and user_name tags
        backup_models = {**MODEL_MAP, "budget_policies": BudgetPolicy}
        for name, model_cls in backup_models.items():
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


def _upsert_record(model_cls, kwargs, raw_id):
    """Save an imported row, preserving supplied IDs and user ownership."""
    record_id = None
    if raw_id:
        record_id = int(raw_id)
        if record_id <= 0:
            raise ValueError("ID must be a positive integer")

    conn = model_cls.get_connection()
    with conn:
        existing = (
            model_cls.objects().filter(id=record_id).first()
            if record_id is not None
            else None
        )
        if existing is not None:
            if existing.to_dict()["user_id"] != kwargs["user"]:
                raise ValueError(f"ID {record_id} belongs to another user")
            instance = existing
            for name, value in kwargs.items():
                setattr(instance, name, value)
        else:
            instance = model_cls.new(**kwargs)

        data = instance.to_dict()
        data.pop("id")
        if record_id is not None:
            data["id"] = record_id
        columns = list(data)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(
            f"{column} = excluded.{column}" for column in columns if column != "id"
        )
        conn.execute(
            f"INSERT INTO {model_cls.table_name} ({', '.join(columns)}) "
            f"VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}",
            list(data.values()),
        )
    return "updated" if existing is not None else "imported"


def reset_user_data(user_id, model_cls=None):
    """Delete selected financial records for one user in a single transaction."""
    models = [model_cls] if model_cls is not None else list(MODEL_MAP.values())
    if any(model not in MODEL_MAP.values() for model in models):
        raise ValueError("Unsupported data type")
    conn = models[0].get_connection()
    deleted = 0
    with conn:
        for model in models:
            cursor = conn.execute(
                f"DELETE FROM {model.table_name} WHERE user_id = ?", (user_id,)
            )
            deleted += cursor.rowcount
    return deleted


def import_csv(model_cls, file, user_id=None):
    result = {"imported": 0, "updated": 0, "skipped": 0, "errors": []}
    if model_cls not in MODEL_MAP.values():
        result["errors"].append("Use backup restore to import budget policies.")
        return result

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
                csv_col = col_index.get(field_name.lower())
                if csv_col:
                    value = (row.get(csv_col) or "").strip()
                    if not value:
                        if field_name in required:
                            raise ValueError(f"Required field '{field_name}' is empty")
                        kwargs[field_name] = None
                        continue
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

            # Backup rows carry their owner; ordinary CSV imports use the target user.
            uid = user_id
            if uid is None:
                uid = int((row.get(col_index.get("user_id")) or "").strip())
                if User.objects().filter(id=uid).first() is None:
                    raise ValueError(f"user_id {uid} does not exist")
            kwargs["user"] = uid
            raw_id = (row.get(col_index.get("id")) or "").strip()
            outcome = _upsert_record(model_cls, kwargs, raw_id)
            result[outcome] += 1

        except Exception as e:
            result["skipped"] += 1
            result["errors"].append(f"Row {i}: {e}")

    return result


def restore_budget_policies(file):
    """Merge policy backups atomically per user, validating the whole timeline."""
    from collections import defaultdict

    from utils.budget import Policy, as_date, load_policies, validate_policies

    result = {"imported": 0, "updated": 0, "skipped": 0, "errors": []}
    content = file.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    groups = defaultdict(list)
    for index, raw_row in enumerate(reader, 1):
        row = {(key or "").strip().lower(): value for key, value in raw_row.items()}
        try:
            uid = int(row.get("user_id") or row.get("user") or "")
            groups[uid].append(row)
        except (ValueError, TypeError):
            result["skipped"] += 1
            result["errors"].append(f"Policy row {index}: invalid user ID")

    conn = BudgetPolicy.get_connection()
    for uid, rows in groups.items():
        try:
            created = updated = 0
            with conn:
                if User.objects().filter(id=uid).first() is None:
                    raise ValueError("User does not exist")
                incoming = []
                for row in rows:
                    record_id = int(row["id"])
                    if record_id <= 0:
                        raise ValueError("Policy ID must be positive")
                    existing = BudgetPolicy.objects().filter(id=record_id).first()
                    if existing and existing.to_dict()["user_id"] != uid:
                        raise ValueError(
                            f"Policy ID {record_id} belongs to another user"
                        )
                    incoming.append(
                        Policy(
                            as_date(row["effective_date"]),
                            int(row["start_day"]),
                            float(row["savings_percent"]),
                            record_id,
                        )
                    )
                    updated += existing is not None
                    created += existing is None
                ids = [p.id for p in incoming]
                if len(ids) != len(set(ids)):
                    raise ValueError("Duplicate policy IDs in backup")
                merged = [p for p in load_policies(uid) if p.id not in ids] + incoming
                validate_policies(merged)
                for policy in incoming:
                    conn.execute(
                        "INSERT INTO budgetpolicy "
                        "(id, user_id, effective_date, start_day, savings_percent) "
                        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
                        "effective_date=excluded.effective_date, "
                        "start_day=excluded.start_day, savings_percent=excluded.savings_percent",
                        (
                            policy.id,
                            uid,
                            policy.effective_date.isoformat(),
                            policy.start_day,
                            policy.savings_percent,
                        ),
                    )
            result["imported"] += created
            result["updated"] += updated
        except (ValueError, TypeError, KeyError, OverflowError, sqlite3.Error) as exc:
            result["skipped"] += len(rows)
            result["errors"].append(f"User {uid} policies: {exc}")
    return result
