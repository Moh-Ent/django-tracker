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

class StaffUserManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            'admin', password='admin-pass-123', is_staff=True
        )
        cls.normal = User.objects.create_user(
            'member', password='member-pass-123', email='member@example.com'
        )
        cls.inactive = User.objects.create_user(
            'inactive', password='inactive-pass-123', is_active=False
        )

        Project.objects.create(owner=cls.normal, name='Member project')

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse('manage_users'))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('manage_users')}",
            fetch_redirect_response=False,
        )

    def test_non_staff_user_gets_404(self):
        self.client.login(username='member', password='member-pass-123')
        response = self.client.get(reverse('manage_users'))
        self.assertEqual(response.status_code, 404)

    def test_user_list_includes_project_counts(self):
        self.client.login(username='admin', password='admin-pass-123')
        response = self.client.get(reverse('manage_users'))

        self.assertEqual(response.status_code, 200)
        member = next(
            user for user in response.context['users']
            if user.username == 'member'
        )
        self.assertEqual(member.project_count, 1)

    def test_search_matches_email(self):
        self.client.login(username='admin', password='admin-pass-123')
        response = self.client.get(
            reverse('manage_users'), {'q': 'member@example.com'}
        )

        usernames = [user.username for user in response.context['users']]
        self.assertEqual(usernames, ['member'])

    def test_staff_can_deactivate_user(self):
        self.client.login(username='admin', password='admin-pass-123')
        response = self.client.post(
            reverse('manage_user_toggle', args=[self.normal.pk]),
            {'action': 'deactivate'},
        )

        self.assertRedirects(response, reverse('manage_users'))
        self.normal.refresh_from_db()
        self.assertFalse(self.normal.is_active)

    def test_staff_can_activate_user(self):
        self.client.login(username='admin', password='admin-pass-123')
        self.client.post(
            reverse('manage_user_toggle', args=[self.inactive.pk]),
            {'action': 'activate'},
        )

        self.inactive.refresh_from_db()
        self.assertTrue(self.inactive.is_active)

    def test_staff_cannot_deactivate_themselves(self):
        self.client.login(username='admin', password='admin-pass-123')
        self.client.post(
            reverse('manage_user_toggle', args=[self.staff.pk]),
            {'action': 'deactivate'},
        )

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_toggle_requires_post(self):
        self.client.login(username='admin', password='admin-pass-123')
        response = self.client.get(
            reverse('manage_user_toggle', args=[self.normal.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_invalid_action_returns_400(self):
        self.client.login(username='admin', password='admin-pass-123')
        response = self.client.post(
            reverse('manage_user_toggle', args=[self.normal.pk]),
            {'action': 'delete'},
        )
        self.assertEqual(response.status_code, 400)