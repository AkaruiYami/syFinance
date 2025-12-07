from models.base import BaseModel
from models.field import DateField, FloatField, ForeignKey, TextField
from models.user import User


class Income(BaseModel):
    date = DateField(null=False)
    amount = FloatField(null=False, decimal=2)
    description = TextField()
    user = ForeignKey(User, null=True)
