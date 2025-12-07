from models.base import BaseModel
from models.field import DateField, FloatField, ForeignKey, TextField
from models.user import User


class Transactions(BaseModel):
    date = DateField(null=False)
    category = TextField(null=False)
    amount = FloatField(null=False)
    description = TextField()
    user = ForeignKey(User, null=True)
