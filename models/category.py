from models.base import BaseModel
from models.field import TextField


class Category(BaseModel):
    name = TextField(null=False)
