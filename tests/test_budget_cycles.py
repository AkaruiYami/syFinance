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
from utils.budget import (
    Period,
    Policy,
    available_periods,
    cancel_pending,
    comparison_period,
    period_for,
    records_in,
    save_settings,
    summarize,
    validate_policies,
)
from utils.data_io import export_all_users_data_zip, restore_budget_policies


class PaydayCycleTests(unittest.TestCase):
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
        User.new(name="Alice", password="test").save()

    def test_payday_boundaries_and_calendar_month(self):
        policy = Policy(date.min, 28, 20)
        period = period_for(date(2025, 10, 2), "Payday cycle", [policy])
        self.assertEqual(period.start, date(2025, 9, 28))
        self.assertEqual(period.end, date(2025, 10, 28))
        month = period_for(date(2025, 10, 2), "Calendar month", [policy])
        self.assertEqual(
            (month.start, month.end), (date(2025, 10, 1), date(2025, 11, 1))
        )

    def test_clamps_long_paydays_and_leap_year(self):
        policy = Policy(date.min, 31, 15)
        self.assertEqual(
            period_for(date(2024, 2, 29), "Payday cycle", [policy]).start,
            date(2024, 2, 29),
        )
        self.assertEqual(
            period_for(date(2025, 2, 27), "Payday cycle", [policy]).start,
            date(2025, 1, 31),
        )
        self.assertEqual(
            period_for(date(2025, 2, 28), "Payday cycle", [policy]).start,
            date(2025, 2, 28),
        )

    def test_transition_policy_starts_at_old_cycle_boundary(self):
        old = Policy(date.min, 28, 20)
        new = Policy(date(2025, 10, 28), 15, 10)
        validate_policies([old, new])
        transition = period_for(date(2025, 11, 1), "Payday cycle", [old, new])
        self.assertEqual(transition.start, date(2025, 10, 28))
        self.assertEqual(transition.end, date(2025, 11, 15))
        self.assertTrue(transition.transition)
        self.assertEqual(
            period_for(date(2025, 11, 16), "Payday cycle", [old, new]).start,
            date(2025, 11, 15),
        )

    def test_income_and_spending_appear_in_both_views(self):
        income = [{"date": "2025-09-28", "amount": 1000}]
        expense = [
            {"date": "2025-10-02", "amount": 200},
            {"date": "2025-10-29", "amount": 40},
        ]
        policy = Policy(date.min, 28, 20)
        cycle = period_for(date(2025, 10, 2), "Payday cycle", [policy])
        self.assertEqual(
            summarize(income, expense, cycle, date(2025, 10, 2))["spendable"], 600
        )
        self.assertEqual(
            sum(r["amount"] for r in records_in(income, period_for(date(2025, 9, 28)))),
            1000,
        )
        self.assertEqual(
            summarize(
                income, expense, period_for(date(2025, 10, 1)), date(2025, 10, 2)
            )["spending"],
            200,
        )

    def test_no_income_and_completed_cycle_values(self):
        period = Period(date(2025, 9, 28), date(2025, 10, 28), 20)
        self.assertIsNone(
            summarize([], [], period, date(2025, 10, 2))["daily_allowance"]
        )
        values = summarize(
            [{"date": "2025-09-28", "amount": 1000}],
            [{"date": "2025-10-01", "amount": 900}],
            period,
            date(2025, 10, 28),
        )
        self.assertTrue(values["completed"])
        self.assertEqual(values["balance"], 100)
        self.assertEqual(values["target"], 200)

    def test_comparison_uses_same_elapsed_days(self):
        old = Policy(date.min, 28, 20)
        current = period_for(date(2025, 10, 2), "Payday cycle", [old])
        previous = comparison_period(current, "Payday cycle", [old], date(2025, 10, 2))
        self.assertEqual(previous.start, date(2025, 8, 28))
        self.assertEqual(previous.end, date(2025, 9, 2))

    def test_setting_change_is_scheduled_to_next_cycle_boundary(self):
        effective = save_settings(1, 28, 20, date(2025, 9, 10))
        self.assertEqual(effective, date.min)
        next_effective = save_settings(1, 15, 10, date(2025, 10, 2))
        self.assertEqual(next_effective, date(2025, 10, 28))
        rows = BudgetPolicy.objects().filter(user_id=1).all(order_by="effective_date")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1].start_day, 15)

    def test_pending_change_can_be_replaced_or_cancelled(self):
        save_settings(1, 28, 20, date(2025, 9, 10))
        save_settings(1, 15, 10, date(2025, 10, 2))
        save_settings(1, 20, 15, date(2025, 10, 2))
        rows = BudgetPolicy.objects().filter(user_id=1).all(order_by="effective_date")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1].start_day, 20)
        cancel_pending(1, date(2025, 10, 2))
        self.assertEqual(len(BudgetPolicy.objects().filter(user_id=1).all()), 1)

    def test_invalid_policy_timeline_rejected(self):
        with self.assertRaises(ValueError):
            validate_policies(
                [Policy(date.min, 28, 20), Policy(date(2025, 10, 20), 15, 10)]
            )

    def test_policy_backup_round_trip_and_invalid_group_atomicity(self):
        save_settings(1, 28, 20, date(2025, 9, 10))
        with zipfile.ZipFile(io.BytesIO(export_all_users_data_zip())) as archive:
            restored = restore_budget_policies(
                io.BytesIO(archive.read("budget_policies.csv"))
            )
        self.assertEqual(restored["updated"], 1)
        self.assertEqual(len(BudgetPolicy.objects().filter(user_id=1).all()), 1)

    def test_policy_restore_rejects_other_users_id(self):
        save_settings(1, 28, 20, date(2025, 9, 10))
        policy_id = BudgetPolicy.objects().filter(user_id=1).first().id
        User.new(name="Bob", password="test").save()
        result = restore_budget_policies(
            io.StringIO(
                "id,user_id,effective_date,start_day,savings_percent\n"
                f"{policy_id},2,0001-01-01,15,10\n"
            )
        )
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(BudgetPolicy.objects().filter(user_id=1).first().start_day, 28)
        invalid = io.StringIO(
            "id,user_id,effective_date,start_day,savings_percent\n"
            "700,1,0001-01-01,31,20\n"
            "701,1,2025-10-20,15,10\n"
        )
        result = restore_budget_policies(invalid)
        self.assertEqual(result["skipped"], 2)
        self.assertEqual(len(BudgetPolicy.objects().filter(user_id=1).all()), 1)

    def test_calendar_period_range_has_no_gaps(self):
        rows = [
            {"date": "2025-09-28", "amount": 1},
            {"date": "2025-10-29", "amount": 2},
        ]
        periods = available_periods(rows, "Calendar month", [], date(2025, 10, 30))
        self.assertEqual(
            [(p.start, p.end) for p in periods],
            [
                (date(2025, 9, 1), date(2025, 10, 1)),
                (date(2025, 10, 1), date(2025, 11, 1)),
            ],
        )


if __name__ == "__main__":
    unittest.main()
