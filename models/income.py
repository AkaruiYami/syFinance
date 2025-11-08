from models.base import BaseModel


class Income(BaseModel):
    table_name = "income"
    fields = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "date": "TEXT NOT NULL",
        "amount": "REAL NOT NULL",
        "description": "TEXT",
    }
