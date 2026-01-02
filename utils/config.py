import os
from dotenv import load_dotenv

load_dotenv()


APP_NAME = os.getenv("APP_NAME")
DB_PATH = os.getenv("DB_PATH")
CURRENCY = os.getenv("CURRENCY")
USERNAME = os.getenv("APP_USERNAME")
PASSWORD = os.getenv("APP_PASSWORD")

WMA_WEIGHTS = [1]
CUSION_FACTOR = 1.5
# set minimum amount of monthly data before taking account for slope
MIN_ENTRY_SLOPE = 5
