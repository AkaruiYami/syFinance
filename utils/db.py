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


def migrate_db(verbose: bool = True, interactive: bool = False) -> List[str]:
    """
    Run migration for all registered model tables.
    Adds any missing columns defined in model fields.

    Args:
        verbose: Print progress messages.
        interactive: If True, prompt for default values when needed (CLI mode).
                     If False, raise RuntimeError instead of blocking on stdin.

    Returns the list of table names that were migrated.
    """
    migrated = []
    for model_cls in BaseModel.get_all_tables():
        try:
            model_cls.migrate_table(interactive=interactive)
            migrated.append(model_cls.table_name)
            if verbose:
                print(f"[{model_cls.table_name}] has been migrated.")
        except Exception as exc:
            print(f"Failed to migrate table for {model_cls.__name__}: {exc}")
    if verbose:
        print("Migration completed.")
    return migrated
