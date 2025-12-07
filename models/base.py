from abc import ABC
import sqlite3
from typing import Dict, List, Optional, Set, Type, TypeVar

from models._base import QuerySet
from models.field import BaseField
from utils import config

T = TypeVar("T", bound="BaseModel")


class BaseModel(ABC):
    _registry: List[Type["BaseModel"]] = []
    _tables_created: Set[Type["BaseModel"]] = set()
    table_name: str

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._fields: Dict[str, BaseField] = {}
        cls.table_name = cls.__name__.lower()
        for attr_name, attr_value in cls.__dict__.items():
            if not isinstance(attr_value, BaseField):
                continue
            attr_value.name = attr_name  # pyright: ignore
            cls._fields[attr_name] = attr_value
        BaseModel._registry.append(cls)

    def __init__(self, **kwargs):
        for name, field in self._fields.items():
            value = kwargs.get(
                name, field.default() if callable(field.default) else field.default
            )
            setattr(self, name, value)
        self.id = None

    @classmethod
    def get_connection(cls) -> sqlite3.Connection:
        import os
        import pathlib

        db_path = pathlib.Path(config.DB_PATH or "./data/finance.db")
        if not db_path.parent.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)

        if not hasattr(cls, "_conn"):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            cls._conn = conn
        return cls._conn

    @classmethod
    def new(cls: Type[T], **kwargs) -> T:
        return cls(**kwargs)

    @classmethod
    def objects(cls) -> QuerySet:
        return QuerySet(cls)

    @classmethod
    def create_table(cls, _creating: Optional[Set] = None):
        from models.field import ForeignKey

        if _creating is None:
            _creating = set()

        if cls in BaseModel._tables_created:
            return

        if cls in _creating:
            return

        _creating.add(cls)

        for name, field in cls._fields.items():
            if isinstance(field, ForeignKey):
                try:
                    target_cls = field.resolve_target_class()
                except Exception:
                    continue

                if target_cls is not None and target_cls is not cls:
                    target_cls.create_table(_creating=_creating)

        conn = cls.get_connection()
        cursor = conn.cursor()
        columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]

        for name, field in cls._fields.items():
            if isinstance(field, ForeignKey):
                col_def = field.get_column_definition()
                columns.append(col_def)
            else:
                if not getattr(field, "sql_type", None):
                    raise ValueError(f"Field '{name}' has no sql_type defined.")
                col_def = f"{name} {field.sql_type}"
                if not field.null:
                    col_def += " NOT NULL"
                columns.append(col_def)

        sql = f"CREATE TABLE IF NOT EXISTS {cls.table_name} ({', '.join(columns)})"
        cursor.execute(sql)
        conn.commit()

        BaseModel._tables_created.add(cls)
        _creating.remove(cls)

    @classmethod
    def get_all_tables(cls) -> List[Type["BaseModel"]]:
        return cls._registry

    def to_dict(self) -> Dict:
        data = {}
        from models.field import ForeignKey

        for field_name, field in self._fields.items():
            if isinstance(field, ForeignKey):
                # read stored id
                storage_name = getattr(field, "storage_name", f"_{field_name}_id")
                data[f"{field_name}"] = getattr(self, storage_name, None)
            else:
                data[field_name] = getattr(self, field_name)
        data["id"] = self.id
        return data

    def save(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        fields = []
        values = []
        from models.field import ForeignKey

        for name, field in self._fields.items():
            if isinstance(field, ForeignKey):
                col_name = f"{name}"
                storage_name = getattr(field, "storage_name", f"_{name}_id")
                val = getattr(self, storage_name, None)
                fields.append(col_name)
                values.append(val)
            else:
                fields.append(name)
                values.append(getattr(self, name))

        for name, field in self._fields.items():
            if not field.null:
                if isinstance(field, ForeignKey):
                    storage_name = getattr(field, "storage_name", f"_{name}_id")
                    if getattr(self, storage_name, None) is None:
                        raise ValueError(f"Field '{name}' cannot be NULL.")
                else:
                    if getattr(self, name) is None:
                        raise ValueError(f"Field '{name}' cannot be NULL.")

        if self.id:
            set_clause = ", ".join([f"{f}=?" for f in fields])
            sql = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
            cursor.execute(sql, values + [self.id])
        else:
            placeholders = ", ".join(["?"] * len(values))
            sql = f"INSERT INTO {self.table_name} ({', '.join(fields)}) VALUES ({placeholders})"
            cursor.execute(sql, values)
            self.id = cursor.lastrowid

        conn.commit()

    @classmethod
    def from_row(cls: Type[T], row: sqlite3.Row) -> T:
        data = dict(row)  # convert Row → dict
        kwargs = {k: data[k] for k in cls._fields if k in data}
        instance = cls(**kwargs)
        instance.id = data.get("id")

        from models.field import ForeignKey

        for field_name, field in cls._fields.items():
            if isinstance(field, ForeignKey):
                storage_name = getattr(field, "storage_name", f"_{field_name}_id")
                instance_val = data.get(f"{field_name}", None)
                setattr(instance, storage_name, instance_val)

        return instance

    @classmethod
    def migrate_table(cls):
        conn = cls.get_connection()
        cursor = conn.cursor()

        cursor.execute(f"PRAGMA table_info({cls.table_name})")
        existing_cols = {row[1]: row for row in cursor.fetchall()}  # name -> row

        for name, field in cls._fields.items():
            if name not in existing_cols:
                col_def = f"{name} {field.sql_type}"

                # Handle NOT NULL constraint
                if not field.null:
                    # Ask user for a default value to backfill
                    user_val = input(
                        f"Table '{cls.table_name}' is missing NOT NULL column '{name}'. "
                        f"Please provide a default value: "
                    ).strip()
                    if not user_val:
                        raise ValueError(
                            f"Cannot add NOT NULL column '{name}' without a value."
                        )
                    col_def += f" NOT NULL DEFAULT '{user_val}'"
                else:
                    # Nullable column
                    if getattr(field, "default", None) is not None:
                        col_def += f" DEFAULT {field.default}"

                cursor.execute(f"ALTER TABLE {cls.table_name} ADD COLUMN {col_def}")
                print(f"Added column '{name}' to {cls.table_name}")

        conn.commit()
