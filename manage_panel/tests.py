from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tracker.models import Project, Task

User = get_user_model()


class StaffDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            'staffer', password='staff-pass-123', is_staff=True
        )
        cls.normal = User.objects.create_user('normal', password='normal-pass-123')

    def test_anonymous_is_redirected_to_login(self):
        url = reverse('manage_dashboard')
        response = self.client.get(url)
        self.assertRedirects(
            response, f"{reverse('login')}?next={url}", fetch_redirect_response=False
        )

    def test_normal_user_gets_404(self):
        self.client.login(username='normal', password='normal-pass-123')
        response = self.client.get(reverse('manage_dashboard'))
        self.assertEqual(response.status_code, 404)

    def test_staff_sees_correct_stats(self):
        project = Project.objects.create(owner=self.normal, name='P')
        today = timezone.localdate()
        Task.objects.create(
            project=project, title='Late', due_date=today - timedelta(days=2)
        )
        Task.objects.create(
            project=project, title='Late but done',
            due_date=today - timedelta(days=2), status=Task.Status.DONE,
        )
        self.client.login(username='staffer', password='staff-pass-123')
        response = self.client.get(reverse('manage_dashboard'))
        self.assertEqual(response.status_code, 200)
        stats = response.context['stats']
        self.assertEqual(stats['total_users'], 2)
        self.assertEqual(stats['total_projects'], 1)
        self.assertEqual(stats['total_tasks'], 2)
        self.assertEqual(stats['overdue_tasks'], 1)
        self.assertEqual(stats['new_signups_week'], 2)