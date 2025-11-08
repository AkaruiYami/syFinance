from abc import ABC, abstractmethod
import sqlite3
from typing import Dict, List, Any, Type
from utils.config import DB_PATH


_conn = None


def get_connection():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH or "data/dev.db", check_same_thread=False)
    return _conn


class BaseModel(ABC):
    _registry: List[Type["BaseModel"]] = []
    table_name: str
    fields: Dict[str, str]  # {"fieldname": "SQL TYPE"}

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if cls is not BaseModel and cls not in cls._registry:
            BaseModel._registry.append(cls)

    @classmethod
    def get_all_tables(cls) -> List[Type["BaseModel"]]:
        """Get all the tables"""
        return list(cls._registry)

    #  --------------------------------------------------
    #   SQL Helper
    #  --------------------------------------------------

    @classmethod
    def create_table(cls):
        """Create table based on model definition."""
        conn = get_connection()
        cursor = conn.cursor()

        columns_sql = ", ".join(
            [f"{name} {type_}" for name, type_ in cls.fields.items()]
        )
        sql = f"CREATE TABLE IF NOT EXISTS {cls.table_name} ({columns_sql})"
        cursor.execute(sql)
        conn.commit()

    @classmethod
    def insert(cls, data: Dict[str, Any]):
        """Insert record using field dict."""
        conn = get_connection()
        cursor = conn.cursor()

        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        values = list(data.values())

        sql = f"INSERT INTO {cls.table_name} ({cols}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        conn.commit()

    @classmethod
    def all(cls) -> List[Dict[str, Any]]:
        """Return all rows."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(f"SELECT * FROM {cls.table_name}")
        rows = cursor.fetchall()

        # Convert to list of dictionaries
        col_names = [col[0] for col in cursor.description]
        return [dict(zip(col_names, row)) for row in rows]

    @classmethod
    def delete(cls, record_id: int):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {cls.table_name} WHERE id = ?", (record_id,))
        conn.commit()

    @classmethod
    def update(cls, record_id: int, data: Dict[str, Any]):
        conn = get_connection()
        cursor = conn.cursor()

        set_sql = ", ".join([f"{k}=?" for k in data])
        values = list(data.values()) + [record_id]

        sql = f"UPDATE {cls.table_name} SET {set_sql} WHERE id = ?"
        cursor.execute(sql, values)
        conn.commit()
