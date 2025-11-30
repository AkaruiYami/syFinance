from typing import List
from models.base import BaseModel


def init_db(verbose: bool = True) -> List[str]:
    """
    Create all registered model tables.

    Returns the list of table names that were created (or already existed).
    """
    created = []
    for model_cls in BaseModel.get_all_tables():
        try:
            model_cls.create_table()
            created.append(model_cls.table_name)
            if verbose:
                print(f"[{model_cls.table_name}] has been created.")
        except Exception as exc:
            print(f"Failed to create table for {model_cls.__name__}: {exc}")
    if verbose:
        print("Table creation completed.")
    return created
