"""Design preview: shows the page templates with FAKE data.
No database and none of Moh's views are needed.

Run from the project root (the folder with manage.py), with the venv active:
    python design_preview.py
Then open http://127.0.0.1:8001/

Nothing you do here is saved. Forms just redirect back."""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import django
from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent

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
from django.http import Http404, HttpResponse  # noqa: E402
from django.shortcuts import redirect, render  # noqa: E402
from django.urls import path  # noqa: E402

from tracker.utils import (  # noqa: E402
    SEED_DATA, count_by_status, days_until_due, is_overdue,
)

PROJECTS_PER_PAGE = 2   # tiny on purpose, so pagination is easy to see
TASKS_PER_PAGE = 4      # the real app will use 10

TODAY = date.today()
ME = SimpleNamespace(username="sara", is_authenticated=True, is_staff=True)
OTHER = SimpleNamespace(username="alex")
STATUS_LABELS = {"todo": "To do", "doing": "Doing", "done": "Done"}
PRIORITY_LABELS = {"low": "Low", "medium": "Medium", "high": "High"}


# ---------- fake data built from SEED_DATA ----------
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
COMMENTS = {}
_task_pk = 0
for _i, _pdata in enumerate(SEED_DATA, start=1):
    _project = FakeProject(_i, _pdata)
    PROJECTS[_i] = _project
    for _tdata in _pdata["tasks"]:
        _task_pk += 1
        _task = FakeTask(_task_pk, _project, _tdata)
        _project.task_list.append(_task)
        TASKS[_task_pk] = _task
        COMMENTS[_task_pk] = []
COMMENTS[1] = [
    FakeComment(1, TASKS[1], OTHER, "Chapter 5 is the hard one, start there."),
    FakeComment(2, TASKS[1], ME, "Thanks, I will. Reading it tonight."),
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


def render_page(request, template, **context):
    context.setdefault("user", ME)
    return render(request, template, context)


def get_or_404(mapping, pk):
    try:
        return mapping[pk]
    except KeyError:
        raise Http404("No such item in the preview data")


# ---------- views ----------
def home(request):
    return redirect("dashboard")


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


def task_detail(request, pk):
    task = get_or_404(TASKS, pk)
    if request.method == "POST":
        return redirect("task_detail", pk=pk)
    return render_page(
        request, "tracker/task_detail.html",
        task=task, comments=COMMENTS.get(pk, []), comment_form=CommentDemo(),
    )


def task_advance(request, pk):
    get_or_404(TASKS, pk)
    return redirect("task_detail", pk=pk)


def comment_delete(request, pk):
    return redirect("dashboard")


def login_page(request):
    if request.method == "POST":
        return redirect("dashboard")
    return render(request, "accounts/login.html", {"form": LoginDemo(), "next": "", "user": SimpleNamespace(is_authenticated=False)})


def register_page(request):
    if request.method == "POST":
        return redirect("dashboard")
    return render(request, "accounts/register.html", {"form": RegisterDemo(), "user": SimpleNamespace(is_authenticated=False)})


def logout_page(request):
    return redirect("login")


def manage_stub(request):
    return HttpResponse("Staff panel: Day 3.")


urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("projects/", project_list, name="project_list"),
    path("projects/new/", project_create, name="project_create"),
    path("projects/<int:pk>/", project_detail, name="project_detail"),
    path("projects/<int:pk>/edit/", project_update, name="project_update"),
    path("projects/<int:pk>/delete/", project_delete, name="project_delete"),
    path("projects/<int:pk>/tasks/new/", task_create, name="task_create"),
    path("tasks/<int:pk>/", task_detail, name="task_detail"),
    path("tasks/<int:pk>/edit/", task_update, name="task_update"),
    path("tasks/<int:pk>/advance/", task_advance, name="task_advance"),
    path("comments/<int:pk>/delete/", comment_delete, name="comment_delete"),
    path("login/", login_page, name="login"),
    path("register/", register_page, name="register"),
    path("logout/", logout_page, name="logout"),
    path("manage/", manage_stub, name="manage_dashboard"),
]


if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    print("Design preview running at http://127.0.0.1:8001/  (Ctrl+C to stop)")
    execute_from_command_line([sys.argv[0], "runserver", "8001", "--noreload"])
