from models.base import BaseModel
from models.field import DateField, FloatField, TextField


class Income(BaseModel):
    date = DateField(null=False)
    amount = FloatField(null=False, decimal=2)
    description = TextField()
