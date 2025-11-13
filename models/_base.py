from typing import Self, Tuple
from ._types import QueryStr, SqlParameterSet


class QuerySet:
    def __init__(self, model_cls):
        self.model_cls = model_cls
        self.filters = []

    def filter(self, **kwargs) -> Self:
        self.filters.append(kwargs)
        return self  # allow chaining

    def _build_where(self) -> Tuple[QueryStr, SqlParameterSet]:
        clauses = []
        values = []
        for f in self.filters:
            for key, val in f.items():
                # support simple operators like __gt, __lt
                if "__" in key:
                    field, op = key.split("__", 1)
                    sql_op = {
                        "gt": ">",
                        "lt": "<",
                        "gte": ">=",
                        "lte": "<=",
                        "ne": "!=",
                        "eq": "=",
                    }.get(op, "=")
                    clauses.append(f"{field} {sql_op} ?")
                    values.append(val)
                else:
                    clauses.append(f"{key} = ?")
                    values.append(val)
        return " AND ".join(clauses), tuple(values)

    def all(self, order_by="id", order="asc"):
        where_clause, values = self._build_where()
        sql = f"SELECT * FROM {self.model_cls.__name__.lower()}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        sql += f" ORDER BY {order_by} {order}"
        conn = self.model_cls.get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, values)
        rows = cursor.fetchall()
        col_names = [col[0] for col in cursor.description]
        instances = []
        for row in rows:
            data = dict(zip(col_names, row))
            inst = self.model_cls(**{k: data[k] for k in self.model_cls._fields.keys()})
            inst.id = data.get("id")
            instances.append(inst)
        return instances

    def first(self):
        results = self.all()
        return results[0] if results else None
