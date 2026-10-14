"""Run from the project root:  python -m tracker.check_utils"""
from datetime import date

from tracker.utils import count_by_status, days_until_due, is_overdue

today = date(2026, 10, 14)
yesterday = date(2026, 10, 13)
tomorrow = date(2026, 10, 15)

# is_overdue
assert is_overdue(yesterday, "todo", today) is True
assert is_overdue(yesterday, "doing", today) is True
assert is_overdue(yesterday, "done", today) is False   # done is never overdue
assert is_overdue(today, "todo", today) is False       # due today is not overdue
assert is_overdue(tomorrow, "todo", today) is False
assert is_overdue(None, "todo", today) is False        # no due date

# days_until_due
assert days_until_due(tomorrow, today) == 1
assert days_until_due(today, today) == 0
assert days_until_due(yesterday, today) == -1
assert days_until_due(date(2026, 10, 24), today) == 10

# count_by_status
assert count_by_status([]) == {"todo": 0, "doing": 0, "done": 0}
assert count_by_status(["todo", "todo", "done"]) == {"todo": 2, "doing": 0, "done": 1}
assert count_by_status(["doing"]) == {"todo": 0, "doing": 1, "done": 0}

print("All helper checks passed.")
