from models.base import BaseModel
from models.field import DateField, FloatField, ForeignKey, IntegerField
from models.user import User


class BudgetPolicy(BaseModel):
    """A user's budget rules from an inclusive cycle boundary onward."""

    effective_date = DateField(null=False)
    start_day = IntegerField(null=False)
    savings_percent = FloatField(null=False)
    user = ForeignKey(User, null=False)
