class BaseField:
    sql_type: str

    def __init__(self, null=True, default=None):
        self.null = null
        self.default = default
        self.name = None  # Will be set dynamically by the model


class DateField(BaseField):
    sql_type = "DATE"


class FloatField(BaseField):
    sql_type = "REAL"

    def __init__(self, null=True, default=None, decimal=None):
        super().__init__(null, default)
        self.decimal = decimal


class TextField(BaseField):
    sql_type = "TEXT"
