import io
import sqlite3
import unittest
import zipfile
from datetime import date
from unittest.mock import patch

from models.base import BaseModel
from models.budget_policy import BudgetPolicy
from models.income import Income
from models.transaction import Transactions
from models.user import User
from models.wishlist import Wishlist
from utils.data_io import (
    export_all_users_data_zip,
    import_csv,
    reset_user_data,
)


class DataImportTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.connection_patch = patch.object(
            BaseModel, "get_connection", return_value=self.conn
        )
        self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)
        self.addCleanup(self.conn.close)
        self.tables_patch = patch.object(BaseModel, "_tables_created", set())
        self.tables_patch.start()
        self.addCleanup(self.tables_patch.stop)
        for model in (User, Income, Transactions, Wishlist, BudgetPolicy):
            model.create_table()
        for name in ("Alice", "Bob"):
            User.new(name=name, password="test").save()

    def load(self, rows, user_id=1):
        return import_csv(
            Transactions,
            io.StringIO("id,date,category,amount,description\n" + rows),
            user_id,
        )

    def test_upsert_preserves_id_and_updates_without_duplicates(self):
        self.assertEqual(self.load("42,2026-01-01,Food,10,Old")["imported"], 1)
        result = self.load("42,2026-01-02,Food,20,")
        self.assertEqual(result["updated"], 1)
        records = Transactions.objects().all()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].id, 42)
        self.assertEqual(records[0].amount, 20)
        self.assertIsNone(records[0].description)

    def test_missing_ids_append_invalid_and_other_owner_ids_skip(self):
        self.load("42,2026-01-01,Food,10,Original")
        result = self.load("42,2026-01-01,Food,99,Changed", user_id=2)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(Transactions.objects().first().amount, 10)
        result = self.load(
            ",2026-01-01,Food,10,New\n"
            "-1,2026-01-01,Food,10,Bad\n"
            "abc,2026-01-01,Food,10,Bad"
        )
        self.assertEqual((result["imported"], result["skipped"]), (1, 2))

    def test_csv_dates_use_day_month_year_and_preserve_iso(self):
        result = self.load(
            "41,01/12/2025,Food,10,December\n"
            "42,12/01/2025,Food,10,January\n"
            "43,13/12/2025,Food,10,Unambiguous\n"
            "44,29/02/2024,Food,10,Leap day\n"
            "45,2025-12-01,Food,10,ISO"
        )
        self.assertEqual((result["imported"], result["skipped"]), (5, 0))
        self.assertEqual(result["errors"], [])
        dates = {record.id: str(record.date) for record in Transactions.objects().all()}
        self.assertEqual(dates, {
            41: "2025-12-01", 42: "2025-01-12", 43: "2025-12-13",
            44: "2024-02-29", 45: "2025-12-01",
        })

    def test_invalid_day_first_dates_are_not_reinterpreted_as_us_dates(self):
        result = self.load(
            "41,12/31/2025,Food,10,US date\n"
            "42,29/02/2025,Food,10,Invalid leap day"
        )
        self.assertEqual((result["imported"], result["skipped"]), (0, 2))
        self.assertEqual(len(Transactions.objects().all()), 0)
        self.assertTrue(all("Invalid date" in error for error in result["errors"]))

    def test_backup_round_trip_is_repeatable(self):
        self.load("42,2026-01-01,Food,10,Original")
        with (
            zipfile.ZipFile(io.BytesIO(export_all_users_data_zip())) as backup,
            backup.open("transactions.csv") as csv_file,
        ):
            result = import_csv(Transactions, csv_file)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(Transactions.objects().all()), 1)

    def test_reset_is_scoped_to_user_and_data_type(self):
        self.load("42,2026-01-01,Food,10,Alice")
        self.load("43,2026-01-01,Food,10,Bob", user_id=2)
        Income.new(date="2026-01-01", amount=100, user=1).save()
        BudgetPolicy.new(
            effective_date=date.min,
            start_day=28,
            savings_percent=20,
            user=1,
        ).save()
        self.assertEqual(reset_user_data(1, Transactions), 1)
        self.assertEqual(len(Income.objects().all()), 1)
        self.assertEqual(reset_user_data(1), 1)
        self.assertEqual(len(Transactions.objects().all()), 1)
        self.assertEqual(len(User.objects().all()), 2)
        self.assertEqual(len(BudgetPolicy.objects().filter(user_id=1).all()), 1)


if __name__ == "__main__":
    unittest.main()
