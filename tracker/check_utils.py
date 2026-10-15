"""Run from the project root:  python -m tracker.check_utils"""
from datetime import date
from types import SimpleNamespace

from tracker.utils import (
    PRIORITIES, SEED_DATA, STATUSES, check_due_date, count_by_status,
    days_until_due, is_overdue, task_to_dict,
)

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

# task_to_dict
task = SimpleNamespace(id=7, title="Quiz", status="todo", priority="high", due_date=tomorrow)
assert task_to_dict(task) == {
    "id": 7, "title": "Quiz", "status": "todo", "priority": "high", "due_date": "2026-10-15",
}
no_date = SimpleNamespace(id=8, title="Idea", status="doing", priority="low", due_date=None)
assert task_to_dict(no_date)["due_date"] is None

# check_due_date
check_due_date(tomorrow, today)          # future: fine
check_due_date(today, today)             # today: fine
check_due_date(None, today)              # optional field: fine
try:
    check_due_date(yesterday, today)
    raise AssertionError("expected ValueError for a past date")
except ValueError:
    pass

# SEED_DATA shape
assert len(SEED_DATA) >= 2
for project in SEED_DATA:
    assert project["name"] and "description" in project and project["tasks"]
    for t in project["tasks"]:
        assert t["title"]
        assert t["status"] in STATUSES
        assert t["priority"] in PRIORITIES
        assert t["due_in_days"] is None or isinstance(t["due_in_days"], int)
all_tasks = [t for p in SEED_DATA for t in p["tasks"]]
assert any(t["due_in_days"] is not None and t["due_in_days"] < 0 and t["status"] != "done" for t in all_tasks)  # has overdue
assert {t["status"] for t in all_tasks} == set(STATUSES)  # uses every status

print("All helper checks passed.")
