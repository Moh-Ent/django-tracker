from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tracker.models import Project, Task, ActivityLog

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
        self.client.logout()
        logged_in = self.client.login(
            username='member',
            password='member-pass-123',
        )
        self.assertTrue(logged_in)

        response = self.client.get(reverse('manage_log'))
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


class StaffActivityLogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            'admin', password='admin-pass-123', is_staff=True
        )
        cls.normal = User.objects.create_user(
            'member', password='member-pass-123'
        )

        cls.created_log = ActivityLog.objects.create(
            user=cls.normal,
            action=ActivityLog.Action.CREATED,
            target_type='task',
            target_id=101,
        )
        cls.updated_log = ActivityLog.objects.create(
            user=cls.staff,
            action=ActivityLog.Action.UPDATED,
            target_type='project',
            target_id=202,
        )
        cls.deleted_log = ActivityLog.objects.create(
            user=cls.normal,
            action=ActivityLog.Action.DELETED,
            target_type='task',
            target_id=303,
        )

        # Set distinct timestamps so ordering is deterministic.
        now = timezone.now()
        cls.created_log.created_at = now - timedelta(minutes=3)
        cls.created_log.save(update_fields=['created_at'])

        cls.updated_log.created_at = now - timedelta(minutes=2)
        cls.updated_log.save(update_fields=['created_at'])

        cls.deleted_log.created_at = now - timedelta(minutes=1)
        cls.deleted_log.save(update_fields=['created_at'])

    def setUp(self):
        self.client.login(username='admin', password='admin-pass-123')

    def test_anonymous_user_is_redirected(self):
        self.client.logout()
        url = reverse('manage_log')
        response = self.client.get(url)

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={url}',
            fetch_redirect_response=False,
        )

    def test_non_staff_user_gets_404(self):
        self.client.logout()
        self.client.login(username='member', password='member-pass-123')

        response = self.client.get(reverse('manage_log'))

        self.assertEqual(response.status_code, 404)

    def test_staff_can_view_activity_logs(self):
        response = self.client.get(reverse('manage_log'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['logs']), 3)

    def test_logs_are_ordered_newest_first(self):
        response = self.client.get(reverse('manage_log'))

        log_ids = [log.pk for log in response.context['logs']]
        self.assertEqual(
            log_ids,
            [
                self.deleted_log.pk,
                self.updated_log.pk,
                self.created_log.pk,
            ],
        )

    def test_filter_by_action(self):
        response = self.client.get(
            reverse('manage_log'),
            {'action': ActivityLog.Action.UPDATED},
        )

        self.assertEqual(
            list(response.context['logs']),
            [self.updated_log],
        )

    def test_search_by_username(self):
        response = self.client.get(
            reverse('manage_log'), {'q': 'member'}
        )

        self.assertEqual(
            {log.pk for log in response.context['logs']},
            {self.created_log.pk, self.deleted_log.pk},
        )

    def test_search_by_target_type(self):
        response = self.client.get(
            reverse('manage_log'), {'q': 'project'}
        )

        self.assertEqual(
            list(response.context['logs']),
            [self.updated_log],
        )

    def test_search_by_target_id(self):
        response = self.client.get(
            reverse('manage_log'), {'q': '303'}
        )

        self.assertEqual(
            list(response.context['logs']),
            [self.deleted_log],
        )

    def test_empty_search_results(self):
        response = self.client.get(
            reverse('manage_log'), {'q': 'no-such-user-or-object'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['logs']), 0)

    def test_pagination(self):
        for index in range(25):
            ActivityLog.objects.create(
                user=self.normal,
                action=ActivityLog.Action.CREATED,
                target_type='task',
                target_id=1000 + index,
            )

        response = self.client.get(reverse('manage_log'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.num_pages, 2)
        self.assertEqual(len(response.context['logs']), 25)

        response = self.client.get(
            reverse('manage_log'), {'page': '2'}
        )
        self.assertEqual(len(response.context['logs']), 3)


class StaffActivityLogFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            'filteradmin',
            password='admin-pass-123',
            is_staff=True,
        )
        cls.member = User.objects.create_user(
            'filtermember',
            password='member-pass-123',
        )

        now = timezone.now()
        cls.old_log = ActivityLog.objects.create(
            user=cls.member,
            action=ActivityLog.Action.CREATED,
            target_type='task',
            target_id=101,
        )
        cls.old_log.created_at = now - timedelta(days=2)
        cls.old_log.save(update_fields=['created_at'])

        cls.recent_log = ActivityLog.objects.create(
            user=cls.staff,
            action=ActivityLog.Action.UPDATED,
            target_type='project',
            target_id=202,
        )

    def setUp(self):
        self.client.login(
            username='filteradmin',
            password='admin-pass-123',
        )
        self.url = reverse('manage_log')

    def test_filter_by_user(self):
        response = self.client.get(
            self.url,
            {'user': str(self.member.pk)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context['logs']),
            [self.old_log],
        )

    def test_filter_by_date_range(self):
        today = timezone.localdate()
        response = self.client.get(self.url, {
            'date_from': today.isoformat(),
            'date_to': today.isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context['logs']),
            [self.recent_log],
        )

    def test_invalid_date_returns_400(self):
        response = self.client.get(
            self.url,
            {'date_from': 'not-a-date'},
        )

        self.assertEqual(response.status_code, 400)

    def test_reversed_date_range_returns_400(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)

        response = self.client.get(self.url, {
            'date_from': today.isoformat(),
            'date_to': yesterday.isoformat(),
        })

        self.assertEqual(response.status_code, 400)

    def test_filters_can_be_combined(self):
        today = timezone.localdate()
        response = self.client.get(self.url, {
            'user': str(self.staff.pk),
            'action': ActivityLog.Action.UPDATED,
            'date_from': today.isoformat(),
            'date_to': today.isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context['logs']),
            [self.recent_log],
        )
