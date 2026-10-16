"""Design preview: shows the page templates with FAKE data.
No database and none of the real views are needed.

Run from the project root (the folder with manage.py), with the venv active:
    python tools/design_preview.py
Then open http://127.0.0.1:8001/

Nothing you do here is saved, except the Activate/Deactivate button on the
staff users page, which flips a fake user in memory so you can see it work."""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

BASE_DIR = Path(__file__).resolve().parent.parent   # tools/ lives one level below the project root
sys.path.insert(0, str(BASE_DIR))                   # so `import tracker.utils` works from tools/

import django  # noqa: E402
from django.conf import settings  # noqa: E402

settings.configure(
    DEBUG=True,
    SECRET_KEY="preview-only-not-secret",
    ALLOWED_HOSTS=["*"],
    ROOT_URLCONF=__name__,
    INSTALLED_APPS=["django.contrib.staticfiles"],
    TEMPLATES=[{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": ["django.template.context_processors.request"],
            "libraries": {"ui": "tracker.templatetags.ui"},
        },
    }],
    STATIC_URL="/static/",
    STATICFILES_DIRS=[BASE_DIR / "static"],
)
django.setup()

from django import forms  # noqa: E402
from django.core.paginator import Paginator  # noqa: E402
from django.http import Http404  # noqa: E402
from django.shortcuts import redirect, render  # noqa: E402
from django.urls import path  # noqa: E402

from tracker.utils import (  # noqa: E402
    SEED_DATA, count_by_status, days_until_due, is_overdue,
)

PROJECTS_PER_PAGE = 2   # tiny on purpose, so pagination is easy to see
TASKS_PER_PAGE = 4      # the real app uses 10
USERS_PER_PAGE = 5
LOGS_PER_PAGE = 6

TODAY = date.today()
STATUS_LABELS = {"todo": "To do", "doing": "Doing", "done": "Done"}
PRIORITY_LABELS = {"low": "Low", "medium": "Medium", "high": "High"}


# ---------- fake users ----------
def make_user(pk, username, active=True, staff=False, days_ago=30, projects=0):
    return SimpleNamespace(
        pk=pk, id=pk, username=username, email=f"{username}@campus.edu",
        is_active=active, is_staff=staff, is_authenticated=True,
        date_joined=datetime.now() - timedelta(days=days_ago), project_count=projects,
    )


ME = make_user(1, "sara", staff=True, days_ago=60, projects=3)
OTHER = make_user(2, "alex", days_ago=45, projects=2)
USERS = {u.pk: u for u in [
    ME, OTHER,
    make_user(3, "maya", days_ago=20, projects=4),
    make_user(4, "omar", active=False, days_ago=18, projects=1),
    make_user(5, "lina", days_ago=9, projects=2),
    make_user(6, "ravi", days_ago=5, projects=1),
    make_user(7, "noor", days_ago=2, projects=0),
    make_user(8, "tess", days_ago=1, projects=1),
]}


# ---------- fake projects / tasks from SEED_DATA ----------
class Manager:
    def __init__(self, items):
        self._items = items

    def count(self):
        return len(self._items)

    def all(self):
        return self._items


class FakeProject:
    def __init__(self, pk, data):
        self.pk = self.id = pk
        self.name = data["name"]
        self.description = data["description"]
        self.created_at = datetime.now() - timedelta(days=pk * 3)
        self.owner = ME
        self.task_list = []
        self.tasks = Manager(self.task_list)

    @property
    def done_count(self):
        return sum(1 for t in self.task_list if t.status == "done")


class FakeTask:
    def __init__(self, pk, project, data):
        self.pk = self.id = pk
        self.project = project
        self.title = data["title"]
        self.description = data["description"]
        self.status = data["status"]
        self.priority = data["priority"]
        days = data["due_in_days"]
        self.due_date = TODAY + timedelta(days=days) if days is not None else None
        self.created_at = datetime.now() - timedelta(days=pk)
        self.comment_list = []
        self.comments = Manager(self.comment_list)

    def get_status_display(self):
        return STATUS_LABELS[self.status]

    def get_priority_display(self):
        return PRIORITY_LABELS[self.priority]


class FakeComment:
    def __init__(self, pk, task, author, body):
        self.pk = pk
        self.task = task
        self.author = author
        self.body = body
        self.created_at = datetime.now() - timedelta(hours=pk * 5)


PROJECTS = {}
TASKS = {}
_task_pk = 0
for _i, _pdata in enumerate(SEED_DATA, start=1):
    _project = FakeProject(_i, _pdata)
    PROJECTS[_i] = _project
    for _tdata in _pdata["tasks"]:
        _task_pk += 1
        _task = FakeTask(_task_pk, _project, _tdata)
        _project.task_list.append(_task)
        TASKS[_task_pk] = _task
TASKS[1].comment_list.extend([
    FakeComment(1, TASKS[1], OTHER, "Chapter 5 is the hard one, start there."),
    FakeComment(2, TASKS[1], ME, "Thanks, I will. Reading it tonight."),
])


# ---------- fake activity log ----------
class FakeLog:
    def __init__(self, user, action, target_type, target_id, hours_ago):
        self.user = user
        self.action = action
        self.target_type = target_type
        self.target_id = target_id
        self.created_at = datetime.now() - timedelta(hours=hours_ago)

    def get_action_display(self):
        return self.action.title()


_log_users = [ME, OTHER, USERS[3], None, USERS[5]]   # None = a user that was deleted
_log_actions = ["created", "updated", "deleted", "updated", "created"]
LOGS = [
    FakeLog(_log_users[i % 5], _log_actions[i % 5], ["project", "task"][i % 2], i + 1, hours_ago=i * 9)
    for i in range(14)
]


# ---------- fake forms (real Django forms, so fields render properly) ----------
class LoginDemo(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class RegisterDemo(forms.Form):
    username = forms.CharField(help_text="Letters, digits and @/./+/-/_ only.")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput, help_text="At least 8 characters.")
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)


class ProjectDemo(forms.Form):
    name = forms.CharField(max_length=100)
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), required=False)


class TaskDemo(forms.Form):
    title = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), required=False)
    status = forms.ChoiceField(choices=list(STATUS_LABELS.items()))
    priority = forms.ChoiceField(choices=list(PRIORITY_LABELS.items()), initial="medium")
    due_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))


class CommentDemo(forms.Form):
    body = forms.CharField(label="Add a comment", widget=forms.Textarea(attrs={"rows": 3}))


# ---------- helpers ----------
class Msg:
    def __init__(self, tags, text):
        self.tags = tags
        self.text = text

    def __str__(self):
        return self.text


ANON = SimpleNamespace(is_authenticated=False, is_staff=False)


def render_page(request, template, **context):
    context.setdefault("user", ME)
    return render(request, template, context)


def get_or_404(mapping, pk):
    try:
        return mapping[pk]
    except KeyError:
        raise Http404("No such item in the preview data")


# ---------- views: user side ----------
def index(request):
    return redirect("dashboard")


def welcome(request):
    """The landing page, logged in."""
    return render_page(request, "home.html")


def welcome_anon(request):
    """The landing page, logged out."""
    return render(request, "home.html", {"user": ANON})


def dashboard(request):
    tasks = list(TASKS.values())
    overdue = [t for t in tasks if is_overdue(t.due_date, t.status, TODAY)]
    due_week = [
        t for t in tasks
        if t.status != "done" and t.due_date and 0 <= days_until_due(t.due_date, TODAY) <= 7
    ]
    return render_page(
        request, "tracker/dashboard.html",
        status_counts=count_by_status([t.status for t in tasks]),
        overdue_tasks=overdue,
        due_this_week=due_week,
        messages=[Msg("success", "Welcome back! (a sample flash message)")],
    )


def project_list(request):
    query = request.GET.get("q", "").strip()
    projects = [p for p in PROJECTS.values() if query.lower() in p.name.lower()]
    page_obj = Paginator(projects, PROJECTS_PER_PAGE).get_page(request.GET.get("page"))
    return render_page(request, "tracker/project_list.html", page_obj=page_obj, query=query)


def project_detail(request, pk):
    project = get_or_404(PROJECTS, pk)
    status = request.GET.get("status", "")
    priority = request.GET.get("priority", "")
    q = request.GET.get("q", "").strip()
    tasks = [
        t for t in project.task_list
        if (not status or t.status == status)
        and (not priority or t.priority == priority)
        and (not q or q.lower() in (t.title + " " + t.description).lower())
    ]
    page_obj = Paginator(tasks, TASKS_PER_PAGE).get_page(request.GET.get("page"))
    filters = {"status": status, "priority": priority, "q": q}
    return render_page(request, "tracker/project_detail.html", project=project, page_obj=page_obj, filters=filters)


def project_create(request):
    if request.method == "POST":
        return redirect("project_list")
    return render_page(request, "tracker/project_form.html", form=ProjectDemo())


def project_update(request, pk):
    project = get_or_404(PROJECTS, pk)
    if request.method == "POST":
        return redirect("project_detail", pk=pk)
    form = ProjectDemo(initial={"name": project.name, "description": project.description})
    form.instance = SimpleNamespace(pk=pk)   # a ModelForm has this; it switches the page to "Edit"
    return render_page(request, "tracker/project_form.html", form=form)


def project_delete(request, pk):
    project = get_or_404(PROJECTS, pk)
    if request.method == "POST":
        return redirect("project_list")
    return render_page(request, "tracker/project_confirm_delete.html", project=project)


def task_create(request, pk):
    project = get_or_404(PROJECTS, pk)
    if request.method == "POST":
        return redirect("project_detail", pk=pk)
    return render_page(request, "tracker/task_form.html", form=TaskDemo(), project=project)


def task_update(request, pk):
    task = get_or_404(TASKS, pk)
    if request.method == "POST":
        return redirect("task_detail", pk=pk)
    form = TaskDemo(initial={
        "title": task.title, "description": task.description, "status": task.status,
        "priority": task.priority, "due_date": task.due_date,
    })
    form.instance = SimpleNamespace(pk=pk)
    return render_page(request, "tracker/task_form.html", form=form, project=task.project)


def task_delete(request, pk):
    task = get_or_404(TASKS, pk)
    if request.method == "POST":
        return redirect("project_detail", pk=task.project.pk)
    return render_page(request, "tracker/task_confirm_delete.html", task=task)


def task_detail(request, pk):
    task = get_or_404(TASKS, pk)
    if request.method == "POST":
        return redirect("task_detail", pk=pk)
    return render_page(
        request, "tracker/task_detail.html",
        task=task, comments=task.comment_list, comment_form=CommentDemo(),
    )


def task_advance(request, pk):
    get_or_404(TASKS, pk)
    return redirect("task_detail", pk=pk)


def comment_delete(request, pk):
    return redirect("dashboard")


def login_page(request):
    if request.method == "POST":
        return redirect("dashboard")
    return render(request, "accounts/login.html", {"form": LoginDemo(), "next": "", "user": ANON})


def register_page(request):
    if request.method == "POST":
        return redirect("dashboard")
    return render(request, "accounts/register.html", {"form": RegisterDemo(), "user": ANON})


def logout_page(request):
    return redirect("login")


# ---------- views: staff panel ----------
def manage_dashboard(request):
    tasks = list(TASKS.values())
    week_ago = datetime.now() - timedelta(days=7)
    stats = {
        "total_users": len(USERS),
        "total_projects": len(PROJECTS),
        "total_tasks": len(tasks),
        "overdue_tasks": sum(1 for t in tasks if is_overdue(t.due_date, t.status, TODAY)),
        "new_signups_week": sum(1 for u in USERS.values() if u.date_joined >= week_ago),
    }
    return render_page(request, "manage_panel/dashboard.html", stats=stats)


def manage_users(request):
    page_obj = Paginator(list(USERS.values()), USERS_PER_PAGE).get_page(request.GET.get("page"))
    return render_page(request, "manage_panel/user_list.html", page_obj=page_obj)


def manage_user_toggle(request, pk):
    member = get_or_404(USERS, pk)
    if request.method == "POST" and member.pk != ME.pk:
        member.is_active = not member.is_active
    return redirect("manage_users")


def manage_log(request):
    f_user = request.GET.get("user", "").strip()
    f_action = request.GET.get("action", "")
    f_date = request.GET.get("date", "")
    rows = [
        row for row in LOGS
        if (not f_user or (row.user and f_user.lower() in row.user.username.lower()))
        and (not f_action or row.action == f_action)
        and (not f_date or row.created_at.date().isoformat() == f_date)
    ]
    page_obj = Paginator(rows, LOGS_PER_PAGE).get_page(request.GET.get("page"))
    filters = {"user": f_user, "action": f_action, "date": f_date}
    return render_page(request, "manage_panel/activity_log.html", page_obj=page_obj, filters=filters)


urlpatterns = [
    path("", index, name="home"),
    path("welcome/", welcome),
    path("welcome-logged-out/", welcome_anon),
    path("dashboard/", dashboard, name="dashboard"),
    path("projects/", project_list, name="project_list"),
    path("projects/new/", project_create, name="project_create"),
    path("projects/<int:pk>/", project_detail, name="project_detail"),
    path("projects/<int:pk>/edit/", project_update, name="project_update"),
    path("projects/<int:pk>/delete/", project_delete, name="project_delete"),
    path("projects/<int:pk>/tasks/new/", task_create, name="task_create"),
    path("tasks/<int:pk>/", task_detail, name="task_detail"),
    path("tasks/<int:pk>/edit/", task_update, name="task_update"),
    path("tasks/<int:pk>/delete/", task_delete, name="task_delete"),
    path("tasks/<int:pk>/advance/", task_advance, name="task_advance"),
    path("comments/<int:pk>/delete/", comment_delete, name="comment_delete"),
    path("login/", login_page, name="login"),
    path("register/", register_page, name="register"),
    path("logout/", logout_page, name="logout"),
    path("manage/", manage_dashboard, name="manage_dashboard"),
    path("manage/users/", manage_users, name="manage_users"),
    path("manage/users/<int:pk>/toggle/", manage_user_toggle, name="manage_user_toggle"),
    path("manage/activity/", manage_log, name="manage_log"),
]


if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    print("Design preview running at http://127.0.0.1:8001/  (Ctrl+C to stop)")
    execute_from_command_line([sys.argv[0], "runserver", "8001", "--noreload"])
