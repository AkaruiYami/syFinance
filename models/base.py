from abc import ABC
import sqlite3
from typing import Dict, List, Type, TypeVar

from models._base import QuerySet
from models.field import BaseField

T = TypeVar("T", bound="BaseModel")


class BaseModel(ABC):
    _registry: List[Type["BaseModel"]] = []
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

        db_path = pathlib.Path(os.getenv("DB_PATH", "data/dev.db"))
        if not db_path.parent.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)

        if not hasattr(cls, "_conn"):
            cls._conn = sqlite3.connect(db_path, check_same_thread=False)
        return cls._conn

    @classmethod
    def new(cls: Type[T], **kwargs) -> T:
        return cls(**kwargs)

    @classmethod
    def objects(cls) -> QuerySet:
        return QuerySet(cls)

    @classmethod
    def create_table(cls):
        conn = cls.get_connection()
        cursor = conn.cursor()
        columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
        for name, field in cls._fields.items():
            col_def = f"{name} {field.sql_type}"
            if not field.null:
                col_def += " NOT NULL"
            columns.append(col_def)
        sql = (
            f"CREATE TABLE IF NOT EXISTS {cls.__name__.lower()} ({', '.join(columns)})"
        )
        cursor.execute(sql)
        conn.commit()

    @classmethod
    def get_all_tables(cls) -> List[Type["BaseModel"]]:
        return cls._registry

    def to_dict(self) -> Dict:
        """
        Convert model instance to dictionary including id.
        """
        data = {field_name: getattr(self, field_name) for field_name in self._fields}
        data["id"] = self.id
        return data

    def save(self):
        """
        If instance has an id → UPDATE, else → INSERT
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        fields = list(self._fields.keys())
        values = [getattr(self, f) for f in fields]

        if self.id:  # already exists → UPDATE
            set_clause = ", ".join([f"{f}=?" for f in fields])
            sql = f"UPDATE {self.__class__.__name__.lower()} SET {set_clause} WHERE id = ?"
            cursor.execute(sql, values + [self.id])
        else:  # new record → INSERT
            placeholders = ", ".join(["?"] * len(values))
            sql = f"INSERT INTO {self.__class__.__name__.lower()} ({', '.join(fields)}) VALUES ({placeholders})"
            cursor.execute(sql, values)
            self.id = cursor.lastrowid

        conn.commit()
