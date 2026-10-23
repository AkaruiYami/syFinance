"""Date-based reporting without moving or duplicating financial records."""

import calendar
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from models.budget_policy import BudgetPolicy


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def month_day(year, month, day):
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def next_boundary(after, day):
    candidate = month_day(after.year, after.month, day)
    if candidate > after:
        return candidate
    year, month = (
        (after.year + 1, 1) if after.month == 12 else (after.year, after.month + 1)
    )
    return month_day(year, month, day)


@dataclass(frozen=True)
class Policy:
    effective_date: date
    start_day: int
    savings_percent: float
    id: int | None = None


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    savings_percent: float | None = None
    transition: bool = False

    @property
    def days(self):
        return (self.end - self.start).days

    @property
    def label(self):
        label = f"{self.start:%d %b %Y} – {self.end - timedelta(days=1):%d %b %Y}"
        return label + (" (transition cycle)" if self.transition else "")


def load_policies(user_id):
    return [
        Policy(
            as_date(row.effective_date), int(row.start_day), row.savings_percent, row.id
        )
        for row in BudgetPolicy.objects()
        .filter(user_id=user_id)
        .all(order_by="effective_date")
    ]


def period_for(day, mode="Calendar month", policies=()):
    day = as_date(day)
    if mode == "Calendar month" or not policies:
        start = day.replace(day=1)
        return Period(start, next_boundary(start, 1))
    applicable = [policy for policy in policies if policy.effective_date <= day]
    if not applicable:
        raise ValueError("No budget policy covers this date")
    policy = applicable[-1]
    start = month_day(day.year, day.month, policy.start_day)
    if start > day:
        previous = day.replace(day=1) - timedelta(days=1)
        start = month_day(previous.year, previous.month, policy.start_day)
    start = max(start, policy.effective_date)
    end = next_boundary(start, policy.start_day)
    future = [p.effective_date for p in policies if p.effective_date > day]
    if future:
        end = min(end, future[0])
    transition = (
        policy.effective_date != date.min
        and start == policy.effective_date
        and start != month_day(start.year, start.month, policy.start_day)
    )
    return Period(start, end, policy.savings_percent, transition)


def validate_policies(policies):
    policies = sorted(policies, key=lambda p: p.effective_date)
    if not policies or policies[0].effective_date != date.min:
        raise ValueError("Policy history must start with the initial policy")
    for index, policy in enumerate(policies):
        if not 1 <= policy.start_day <= 31:
            raise ValueError("Payday must be between 1 and 31")
        if not math.isfinite(policy.savings_percent) or not (
            0 <= policy.savings_percent <= 100
        ):
            raise ValueError("Savings target must be between 0 and 100%")
        if index:
            if policy.effective_date <= policies[index - 1].effective_date:
                raise ValueError("Policy dates must be unique")
            previous_day = policy.effective_date - timedelta(days=1)
            previous = period_for(previous_day, "Payday cycle", policies[:index])
            if previous.end != policy.effective_date:
                raise ValueError("Setting changes must start at a cycle boundary")
    return policies


def save_settings(user_id, start_day, savings_percent, today=None):
    today = today or date.today()
    policies = load_policies(user_id)
    active = [p for p in policies if p.effective_date <= today]
    effective = period_for(today, "Payday cycle", active).end if active else date.min
    updated = Policy(effective, int(start_day), float(savings_percent))
    if start_day != updated.start_day:
        raise ValueError("Payday must be a whole number")
    validate_policies(active + [updated])
    conn = BudgetPolicy.get_connection()
    with conn:
        conn.execute(
            "DELETE FROM budgetpolicy WHERE user_id = ? AND effective_date > ?",
            (user_id, today.isoformat()),
        )
        conn.execute(
            "INSERT INTO budgetpolicy "
            "(user_id, effective_date, start_day, savings_percent) VALUES (?, ?, ?, ?)",
            (
                user_id,
                effective.isoformat(),
                updated.start_day,
                updated.savings_percent,
            ),
        )
    return effective


def cancel_pending(user_id, today=None):
    today = today or date.today()
    conn = BudgetPolicy.get_connection()
    with conn:
        conn.execute(
            "DELETE FROM budgetpolicy WHERE user_id = ? AND effective_date > ?",
            (user_id, today.isoformat()),
        )


def records_in(records, period, cutoff=None):
    end = min(period.end, cutoff + timedelta(days=1)) if cutoff else period.end
    return [r for r in records if period.start <= as_date(r["date"]) < end]


def available_periods(records, mode, policies, today=None):
    today = today or date.today()
    earliest = min([today] + [as_date(r["date"]) for r in records])
    period = period_for(earliest, mode, policies)
    periods = []
    while period.start <= today:
        periods.append(period)
        period = period_for(period.end, mode, policies)
    return periods


def summarize(incomes, expenses, period, today=None):
    today = today or date.today()
    income = sum(float(r["amount"]) for r in records_in(incomes, period, today))
    spending = sum(float(r["amount"]) for r in records_in(expenses, period, today))
    elapsed = min(period.days, max(0, (today - period.start).days + 1))
    remaining_days = max(0, (period.end - max(today, period.start)).days)
    target = (
        income * period.savings_percent / 100
        if (period.savings_percent is not None)
        else None
    )
    spendable = income - spending - target if target is not None else None
    return {
        "income": income,
        "spending": spending,
        "balance": income - spending,
        "target": target,
        "spendable": spendable,
        "elapsed": elapsed,
        "remaining_days": remaining_days,
        "completed": period.end <= today,
        "daily_allowance": max(0, spendable) / remaining_days
        if (income > 0 and spendable is not None and remaining_days > 0)
        else None,
        "projected_spending": spending / elapsed * period.days if elapsed else 0,
    }


def comparison_period(period, mode, policies, today=None):
    today = today or date.today()
    previous = period_for(period.start - timedelta(days=1), mode, policies)
    elapsed = min(period.days, max(0, (today - period.start).days + 1))
    if today < period.end:
        previous = Period(
            previous.start,
            min(previous.end, previous.start + timedelta(days=elapsed)),
            previous.savings_percent,
            previous.transition,
        )
    return previous
