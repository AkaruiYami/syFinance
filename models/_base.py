from typing import Self, Tuple
from ._types import QueryStr, SqlParameterSet


class QuerySet:
    def __init__(self, model_cls):
        self.model_cls = model_cls
        self.filters = []

    def filter(self, **kwargs) -> Self:
        self.filters.append(kwargs)
        return self  # allow chaining

    def _field_column(self, key: str) -> str:
        """
        Convert a logical field name to the actual DB column name.
        - For ForeignKey fields, use "<name>_id".
        - If the key already ends with _id, keep it.
        """
        if key.endswith("_id"):
            return key
        if key in self.model_cls._fields:
            from models.field import ForeignKey

            fld = self.model_cls._fields[key]
            if isinstance(fld, ForeignKey):
                return f"{key}_id"
            return key
        return key  # fallback (unknown field, treat as-is)

    def _build_where(self) -> Tuple[QueryStr, SqlParameterSet]:
        clauses = []
        values = []
        for f in self.filters:
            for raw_key, val in f.items():
                # support simple operators like __gt, __lt
                if "__" in raw_key:
                    field_part, op = raw_key.split("__", 1)
                    col = self._field_column(field_part)
                    sql_op = {
                        "gt": ">",
                        "lt": "<",
                        "gte": ">=",
                        "lte": "<=",
                        "ne": "!=",
                        "eq": "=",
                    }.get(op, "=")
                    clauses.append(f"{col} {sql_op} ?")
                    values.append(val)
                else:
                    col = self._field_column(raw_key)
                    clauses.append(f"{col} = ?")
                    values.append(val)
        return " AND ".join(clauses), tuple(values)

    def all(self, order_by="id", order="asc"):
        # Build select columns: include id and field names (for FK use <name>_id)
        cols = ["id"]
        from models.field import ForeignKey

        for name, fld in self.model_cls._fields.items():
            if isinstance(fld, ForeignKey):
                cols.append(f"{name}")
            else:
                cols.append(name)

        where_clause, values = self._build_where()
        sql = f"SELECT {', '.join(cols)} FROM {self.model_cls.__name__.lower()}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        sql += f" ORDER BY {order_by} {order}"

        conn = self.model_cls.get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, values)
        rows = cursor.fetchall()

        instances = []
        for row in rows:
            # prefer Model.from_row if present (handles FK storage attributes)
            if hasattr(self.model_cls, "from_row"):
                # If row is a sqlite3.Row or mapping-like, pass it directly
                inst = self.model_cls.from_row(row)
            else:
                # fallback: build mapping from columns -> values
                col_names = [col[0] for col in cursor.description]
                data = dict(zip(col_names, row))
                inst = self.model_cls(
                    **{k: data[k] for k in self.model_cls._fields.keys()}
                )
                inst.id = data.get("id")
                # populate FK storage attrs if any
                for name, fld in self.model_cls._fields.items():
                    if isinstance(fld, ForeignKey):
                        storage = getattr(fld, "storage_name", f"_{name}_id")
                        setattr(inst, storage, data.get(f"{name}_id"))
            instances.append(inst)
        return instances

    def first(self):
        results = self.all(order_by="id", order="asc")
        return results[0] if results else None
