# Django Project & Task Tracker

A small Trello-style task tracker built with Django. Each user keeps private projects and tasks, with comments, search and filters. Staff get a separate `/manage/` panel with site statistics, user management and an audit log of every change.

**Live demo:** (https://django-tracker-xxmr.onrender.com/)
(Free hosting: the first visit after a quiet period can take up to a minute to wake up.)

## Demo accounts

| Account | Role | Password |
|---|---|---|
| `demo` | Normal user with sample projects and tasks | `demo` |
| `staffdemo` | Staff, can open `/manage/` | `demo` |

The demo data is reloaded on every deploy, and accounts created by visitors are not kept.

## Features

**For users**
- Register, log in and log out
- Create, edit and delete projects and tasks
- Task status (To do, Doing, Done), priority and optional due date, with a one-click button to move a task forward
- Dashboard with task counts by status, overdue tasks and tasks due this week
- Keyword search on projects and tasks, filters by status and priority, and pagination that keeps your filters
- Comments on tasks; you can delete only your own
- JSON endpoint: `/api/projects/<id>/tasks/` (optional `?status=todo|doing|done`)

**For staff (`/manage/`)**
- Overview with totals for users, projects, tasks, overdue tasks and new signups this week
- User list with project counts and an activate/deactivate button (you can't deactivate yourself)
- Activity log with filters for user, action, date range and keyword
- The standard Django admin at `/admin/`, customised with inline tasks, filters, search and bulk actions

## Security decisions

- **Ownership filtering.** Every project and task lookup is filtered by the logged-in user (`owner=request.user`, or `project__owner` for tasks). Another user's URL returns a 404, so you can't tell whether it exists. This prevents IDOR (insecure direct object reference) attacks.
- **Login required.** All private views require login; anonymous visitors are redirected to the login page.
- **Staff-only panel.** `/manage/` returns 404 to everyone except staff, so non-staff can't even confirm it exists.
- **Audit log.** Every create, update and delete of a project or task is recorded with the user, action and target. Staff can browse and filter it.
- **Server-side authorship.** A comment's author is always taken from `request.user`, never from the form.
- **Safe state changes.** Status changes, deletions of comments and user activation use POST-only views with CSRF tokens. A template check (`tools/check_templates.py`) verifies that every POST form includes `{% csrf_token %}`.
- **Validation.** Forms reject empty titles and due dates in the past on creation. The log filters reject invalid dates and IDs.
- **Production settings.** With `DJANGO_DEBUG=False` the app refuses to start without a real secret key, redirects to HTTPS, and uses secure cookies and HSTS.

## Run it locally

Requires Python 3.12 or newer.

```bash
git clone https://github.com/Moh-Ent/django-tracker.git
cd django-tracker
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo        # creates demo and staffdemo with sample data
python manage.py runserver
```

Open http://127.0.0.1:8000/. Without `DEMO_PASSWORD` set, the demo accounts use the password `demo`. This is for local use only. To make your own admin account, run `python manage.py createsuperuser`.

Run the tests:

```bash
python manage.py test
python tools/check_templates.py
```

## Deploying to Render

1. Push the repo to GitHub.
2. On Render, create a **Web Service** from the repo.
3. Set the build command to `bash build.sh` and the start command to `gunicorn config.wsgi:application`.
4. Add these environment variables:

| Variable | Value |
|---|---|
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | a long random string |
| `DEMO_PASSWORD` | the password for the demo accounts (this demo uses `demo`) |
| `PYTHON_VERSION` | `3.13.5` |

`build.sh` installs the requirements, collects static files, runs migrations and loads the demo data. SQLite is used, so data resets on each redeploy.

## Project layout

```
config/        settings and root URLs
accounts/      register, login and logout
tracker/       projects, tasks, comments, activity log, JSON endpoint
manage_panel/  staff-only pages (stats, users, activity log)
templates/     all HTML templates
static/        CSS
tools/         template safety check
```

## Built with

Django 6.1, SQLite, Bootstrap 5, WhiteNoise, Gunicorn.

## Team

- Moh: models, views, permissions, admin, tests and deployment
- Design, templates and helper functions: *add your friend's name*
