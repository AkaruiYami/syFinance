import datetime
from models.base import BaseModel
from models.field import DateField, TextField


class User(BaseModel):
    name = TextField(null=False)
    password = TextField(null=False)
    email = TextField()
    description = TextField()
    role = TextField(null=False, default="user")
    date_created = DateField(null=False, default=datetime.datetime.now)
    last_updated = DateField(null=False, default=datetime.datetime.now)
