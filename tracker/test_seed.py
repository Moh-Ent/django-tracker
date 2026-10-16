import os
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import ActivityLog, Comment, Project, Task
from .utils import SEED_DATA

User = get_user_model()


@mock.patch.dict(os.environ, {'DEMO_PASSWORD': 'test-pass-456'})
class SeedDemoTests(TestCase):
    def seed(self, *args):
        out = StringIO()
        call_command('seed_demo', *args, stdout=out)
        return out.getvalue()

    def test_creates_both_accounts(self):
        self.seed()
        demo = User.objects.get(username='demo')
        staff = User.objects.get(username='staffdemo')
        self.assertFalse(demo.is_staff)
        self.assertTrue(staff.is_staff)
        self.assertTrue(self.client.login(username='demo', password='test-pass-456'))

    def test_loads_all_seed_projects_and_tasks_for_demo_user(self):
        self.seed()
        demo = User.objects.get(username='demo')
        self.assertEqual(Project.objects.filter(owner=demo).count(), len(SEED_DATA))
        expected = sum(len(p['tasks']) for p in SEED_DATA)
        self.assertEqual(Task.objects.filter(project__owner=demo).count(), expected)
        self.assertTrue(Comment.objects.exists())
        self.assertTrue(ActivityLog.objects.filter(user=demo).exists())

    def test_due_dates_are_relative_to_today(self):
        self.seed()
        today = timezone.localdate()
        open_tasks = Task.objects.exclude(status=Task.Status.DONE)
        self.assertTrue(open_tasks.filter(due_date__lt=today).exists())
        self.assertTrue(open_tasks.filter(due_date__gte=today).exists())
        self.assertTrue(Task.objects.filter(due_date=None).exists())

    def test_running_twice_does_not_duplicate(self):
        self.seed()
        self.seed()
        self.assertEqual(Project.objects.count(), len(SEED_DATA))

    def test_reset_rebuilds_without_duplicates(self):
        self.seed()
        Project.objects.filter(name=SEED_DATA[0]['name']).delete()
        self.seed('--reset')
        self.assertEqual(Project.objects.count(), len(SEED_DATA))

    def test_reset_reactivates_and_resets_password(self):
        self.seed()
        User.objects.filter(username='demo').update(is_active=False)
        self.seed('--reset')
        self.assertTrue(self.client.login(username='demo', password='test-pass-456'))
