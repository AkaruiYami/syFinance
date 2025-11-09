from .base import BaseModel


class Wishlist(BaseModel):
    STATUS = ["NOT COMPLETE", "COMPLETED", "CANCELED", "ON HOLD"]

    table_name = "wishlist"
    fields = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "dateCreated": "TEXT NOT NULL",
        "name": "TEXT NOT NULL",
        "amount": "REAL NOT NULL",
        "source": "TEXT",
        "description": "TEXT",
        "status": "TEXT NOT NULL",
    }
