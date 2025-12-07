from models.field import DateField, ForeignKey, TextField, FloatField
from models.user import User
from .base import BaseModel
from datetime import datetime


class Wishlist(BaseModel):
    class Status:
        NOT_COMPLETE = "NOT COMPLETE"
        COMPLETED = "COMPLETED"
        CANCELED = "CANCELED"
        ON_HOLD = "ON HOLD"

    dateCreated = DateField(null=False, default=datetime.now)
    name = TextField(null=False)
    amount = FloatField(null=False, decimal=2)
    source = TextField()
    description = TextField()
    status = TextField(null=False, default=Status.NOT_COMPLETE)
    user = ForeignKey(User, null=True)
