"""Pure-Python helpers. No Django imports, and no date.today():
`today` is always passed in so the same input gives the same answer."""

STATUSES = ("todo", "doing", "done")


def is_overdue(due_date, status, today):
    """True only if due_date is before today and the task is not done.
    No due date means False."""
    if due_date is None:
        return False
    return due_date < today and status != "done"


def days_until_due(due_date, today):
    """Days from today to due_date. Negative if it is already past.
    Callers must check for a missing due_date first."""
    return (due_date - today).days


def count_by_status(statuses):
    """Count a list of status strings. The result always has
    todo, doing and done, even when a count is 0."""
    counts = {s: 0 for s in STATUSES}
    for s in statuses:
        if s in counts:
            counts[s] += 1
    return counts
