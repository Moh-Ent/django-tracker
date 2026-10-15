"""Pure-Python helpers. No Django imports, and no date.today():
`today` is always passed in so the same input gives the same answer."""

STATUSES = ("todo", "doing", "done")
PRIORITIES = ("low", "medium", "high")


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


def task_to_dict(task):
    """Turn a task (anything with id, title, status, priority, due_date)
    into a plain dict for the JSON endpoint."""
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
    }


def check_due_date(due_date, today):
    """Raise ValueError if due_date is before today.
    A missing due date (None) is allowed, because the field is optional."""
    if due_date is not None and due_date < today:
        raise ValueError("Due date cannot be in the past.")


# Demo data. due_in_days is relative to the day the data is loaded,
# so the demo always has some overdue, due-soon and later tasks.
# Negative = already overdue, None = no due date.
SEED_DATA = [
    {
        "name": "Semester Planner",
        "description": "Readings, quizzes and exams for this term, all in one place.",
        "tasks": [
            {"title": "Read chapters 4 and 5 for Databases", "description": "Focus on normalization and joins.", "status": "doing", "priority": "medium", "due_in_days": 2},
            {"title": "Statistics quiz 3", "description": "Covers hypothesis testing. Bring a calculator.", "status": "todo", "priority": "high", "due_in_days": 4},
            {"title": "Submit sociology reflection essay", "description": "Two pages, upload to the course portal.", "status": "todo", "priority": "high", "due_in_days": -2},
            {"title": "Buy the lab notebook", "description": "", "status": "done", "priority": "low", "due_in_days": -5},
            {"title": "Form a study group for finals", "description": "Ask three classmates and book a library room.", "status": "todo", "priority": "low", "due_in_days": 12},
            {"title": "Review midterm feedback", "description": "Note which topics lost the most points.", "status": "doing", "priority": "medium", "due_in_days": None},
        ],
    },
    {
        "name": "Capstone Project",
        "description": "Our final-year group project: a campus event finder.",
        "tasks": [
            {"title": "Write the project proposal", "description": "One page with goals, scope and a timeline.", "status": "done", "priority": "high", "due_in_days": -9},
            {"title": "Sketch the main screens", "description": "Home, event page and sign-up flow.", "status": "doing", "priority": "medium", "due_in_days": 3},
            {"title": "Set up the shared repository", "description": "Add branch rules and invite the team.", "status": "done", "priority": "medium", "due_in_days": -7},
            {"title": "Build the event list page", "description": "Search, filters and pagination.", "status": "todo", "priority": "high", "due_in_days": 6},
            {"title": "Prepare the midterm demo", "description": "Five minutes, three features, one backup video.", "status": "todo", "priority": "high", "due_in_days": 9},
            {"title": "Write the user survey", "description": "Ten questions, send to 30 students.", "status": "todo", "priority": "low", "due_in_days": -1},
        ],
    },
    {
        "name": "Part-time Job",
        "description": "Shifts, training and things to remember at the cafe.",
        "tasks": [
            {"title": "Finish the food safety course", "description": "Online module, about two hours.", "status": "doing", "priority": "high", "due_in_days": 5},
            {"title": "Swap Saturday shift with Maya", "description": "Needs manager approval.", "status": "todo", "priority": "medium", "due_in_days": 1},
            {"title": "Send availability for next month", "description": "", "status": "done", "priority": "medium", "due_in_days": -3},
            {"title": "Learn the new espresso machine", "description": "Ask for a walkthrough on a quiet shift.", "status": "todo", "priority": "low", "due_in_days": None},
        ],
    },
]
