from models.base import BaseModel
from models.category import Category
from models.field import ForeignKey, TextField


class Subcategory(BaseModel):
    name = TextField(null=False)
    category = ForeignKey(Category, null=False)
