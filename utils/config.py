import os
from dotenv import load_dotenv

load_dotenv()


APP_NAME = os.getenv("APP_NAME")
DB_PATH = os.getenv("DB_PATH")
CURRENCY = os.getenv("CURRENCY")
