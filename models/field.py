from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from models.base import BaseModel


class BaseField:
    sql_type: str

    def __init__(self, null=True, default=None):
        self.null = null
        self.default = default
        self.name = None  # Will be set dynamically by the model


class DateField(BaseField):
    sql_type = "DATE"


class FloatField(BaseField):
    sql_type = "REAL"

    def __init__(self, null=True, default=None, decimal=None):
        super().__init__(null, default)
        self.decimal = decimal


class TextField(BaseField):
    sql_type = "TEXT"


class ForeignKey(BaseField):
    """
    Descriptor-style ForeignKey.
    - `to` may be a BaseModel subclass or a string with the target class name.
    - Stores the referenced object's id in instance._<name>_id.
    - Accessing the attribute returns the target model instance (or None).
    - Assign either a model instance or an integer id (or None).
    """

    sql_type = "INTEGER"

    def __init__(
        self,
        to: type[BaseModel],
        null=True,
        default=None,
        on_delete: Optional[str] = None,
    ):
        """
        to: model class or model class name (str)
        on_delete: optional string for SQL (e.g., "CASCADE", "SET NULL") — will be appended
        """
        super().__init__(null=null, default=default)
        self.to = to
        self.on_delete = on_delete
        self.storage_name = None

    def __set_name__(self, owner, name):
        self.name = name
        self.storage_name = f"_{name}_id"

    def resolve_target_class(self):
        """
        Return the target BaseModel subclass. Accepts either a class (direct) or string name.
        If string, find in BaseModel._registry.
        """
        from models.base import BaseModel

        if isinstance(self.to, str):
            for cls in BaseModel._registry:
                if (
                    cls.__name__ == self.to
                    or getattr(cls, "table_name", None) == self.to
                ):
                    return cls
            raise ValueError(f"Related model '{self.to}' not found in registry.")
        return self.to

    def __get__(self, instance, owner):
        if instance is None:
            return self
        fk_id = getattr(instance, self.storage_name, None)  # pyright: ignore
        if fk_id is None:
            return None
        target_cls = self.resolve_target_class()
        return target_cls.get(fk_id)

    def __set__(self, instance, value):
        """
        Accept either:
          - model instance of target class -> store its id (must be saved)
          - int (primary key)
          - None
        """
        if value is None:
            setattr(instance, self.storage_name, None)  # pyright: ignore
            return

        target_cls = self.resolve_target_class()

        # model instance passed
        if hasattr(value, "__class__") and isinstance(value, target_cls):  # pyright: ignore
            if getattr(value, "id", None) is None:
                raise ValueError(
                    "Can't assign unsaved related object (id is None). Save it first."
                )
            setattr(instance, self.storage_name, value.id)  # pyright: ignore
            return

        # numeric id passed
        if isinstance(value, int):
            setattr(instance, self.storage_name, value)  # pyright: ignore
            return

        raise TypeError(f"Can't assign {type(value)!r} to ForeignKey '{self.name}'")

    def get_column_definitions(self):
        target_table = (
            self.to.table_name
            if hasattr(self.to, "table_name")
            else (self.to if isinstance(self.to, str) else None)
        )
        cols = [f"{self.name}_id {self.sql_type}", f"FOREIGN KEY ({self.name}_id)"]
        if not self.null:
            cols[0] += " NOT NULL"
        if target_table:
            cols[1] += f" REFERENCES {target_table}(id)"
            if self.on_delete:
                cols[1] += f" ON DELETE {self.on_delete}"
        return cols
