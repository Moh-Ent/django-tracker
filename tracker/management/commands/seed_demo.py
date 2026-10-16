"""Load demo accounts and demo data.

    python manage.py seed_demo            # create the data (skips if it already exists)
    python manage.py seed_demo --reset    # wipe the demo user's data, then rebuild it

Accounts:
    demo       normal user, owns the seed projects and tasks
    staffdemo  staff user, can open /manage/

Both use the password in the DEMO_PASSWORD environment variable,
or "demo-pass-123" if it is not set.
"""
import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tracker.activity import log_action
from tracker.models import ActivityLog, Comment, Project, Task
from tracker.utils import SEED_DATA

DEFAULT_PASSWORD = 'demo'

# A few comments so the task page is not empty. (title of task -> comments)
DEMO_COMMENTS = {
    'Read chapters 4 and 5 for Databases': ['Finished chapter 4, joins next.'],
    'Prepare the midterm demo': [
        'I will record the backup video tonight.',
        'Remember to test the projector first.',
    ],
}


class Command(BaseCommand):
    help = 'Create the demo and staffdemo accounts and load the demo projects and tasks.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help="Delete the demo user's projects and activity first, then rebuild them.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        password = os.environ.get('DEMO_PASSWORD', DEFAULT_PASSWORD)

        demo, _ = User.objects.get_or_create(
            username='demo', defaults={'email': 'demo@example.com'}
        )
        staff, _ = User.objects.get_or_create(
            username='staffdemo', defaults={'email': 'staffdemo@example.com'}
        )
        staff.is_staff = True

        for user in (demo, staff):
            user.is_active = True
            user.set_password(password)
            user.save()

        if options['reset']:
            Project.objects.filter(owner=demo).delete()
            ActivityLog.objects.filter(user=demo).delete()
            self.stdout.write('Old demo data removed.')

        if Project.objects.filter(owner=demo).exists():
            self.stdout.write(self.style.WARNING(
                'Demo data already exists, nothing added. Use --reset to rebuild it.'
            ))
        else:
            self._load_data(demo)

        self.stdout.write(self.style.SUCCESS(
            "Accounts ready: 'demo' (normal) and 'staffdemo' (staff)."
        ))

    def _load_data(self, owner):
        today = timezone.localdate()
        project_count = task_count = 0

        for project_data in SEED_DATA:
            project = Project.objects.create(
                owner=owner,
                name=project_data['name'],
                description=project_data['description'],
            )
            log_action(owner, ActivityLog.Action.CREATED, project)
            project_count += 1

            for task_data in project_data['tasks']:
                days = task_data['due_in_days']
                task = Task.objects.create(
                    project=project,
                    title=task_data['title'],
                    description=task_data['description'],
                    status=task_data['status'],
                    priority=task_data['priority'],
                    due_date=today + timedelta(days=days) if days is not None else None,
                )
                log_action(owner, ActivityLog.Action.CREATED, task)
                if task.status != Task.Status.TODO:
                    # Tasks already in progress or done were moved at some point.
                    log_action(owner, ActivityLog.Action.UPDATED, task)
                task_count += 1

                for body in DEMO_COMMENTS.get(task.title, []):
                    Comment.objects.create(task=task, author=owner, body=body)

        self.stdout.write(f'Created {project_count} projects and {task_count} tasks.')