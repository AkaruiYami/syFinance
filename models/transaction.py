from models.base import BaseModel
from models.field import DateField, FloatField, TextField


class Transactions(BaseModel):
    date = DateField(null=False)
    category = TextField(null=False)
    amount = FloatField(null=False)
    description = TextField()
