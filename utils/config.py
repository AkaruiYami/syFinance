import os
from dotenv import load_dotenv

load_dotenv()


APP_NAME = os.getenv("APP_NAME", "syFinance")
DB_PATH = os.getenv("DB_PATH", "data/finance.db")
CURRENCY = os.getenv("CURRENCY", "$")

WMA_WEIGHTS = [1]
CUSION_FACTOR = 1.5
# set minimum amount of monthly data before taking account for slope
MIN_ENTRY_SLOPE = 5

# Anomaly detection: flag transactions above mean + N * std dev
ANOMALY_STD_THRESHOLD = 2

# Category spike threshold: flag categories changing more than N%
CATEGORY_SPIKE_THRESHOLD = 25

# "Other" category: warn when it exceeds N% of total spend
OTHER_CATEGORY_NAME = "Other"
OTHER_CATEGORY_PCT_THRESHOLD = 30

# Recurring charge detection: minimum distinct months to qualify
RECURRING_MIN_MONTHS = 2
