from models.base import BaseModel


def init_db():
    for models in BaseModel.get_all_tables():
        models.create_table()
        print(f"[{models.table_name}] has been created.")
    print("Table creation completed.")
