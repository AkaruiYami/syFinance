from models.base import BaseModel


class Transaction(BaseModel):
    table_name = "transactions"
    fields = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "date": "TEXT NOT NULL",
        "category": "TEXT NOT NULL",
        "amount": "REAL NOT NULL",
        "description": "TEXT",
    }
