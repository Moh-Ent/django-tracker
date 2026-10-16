from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import TaskForm
from .models import Comment, Project, Task

User = get_user_model()


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user('alice', password='alice-pass-123')
        cls.bob = User.objects.create_user('bob', password='bob-pass-123')
        cls.project = Project.objects.create(owner=cls.alice, name='Alice project')
        cls.task = Task.objects.create(project=cls.project, title='Alice task')
        cls.comment = Comment.objects.create(
            task=cls.task, author=cls.alice, body='Alice note'
        )

    def get_urls(self):
        return [
            reverse('project_detail', args=[self.project.pk]),
            reverse('project_update', args=[self.project.pk]),
            reverse('project_delete', args=[self.project.pk]),
            reverse('task_create', args=[self.project.pk]),
            reverse('task_detail', args=[self.task.pk]),
            reverse('task_update', args=[self.task.pk]),
            reverse('task_delete', args=[self.task.pk]),
        ]

    def post_urls(self):
        return [
            reverse('project_delete', args=[self.project.pk]),
            reverse('task_delete', args=[self.task.pk]),
            reverse('task_advance', args=[self.task.pk]),
            reverse('comment_delete', args=[self.comment.pk]),
        ]


class OtherUserTests(BaseTestCase):
    def setUp(self):
        self.client.login(username='bob', password='bob-pass-123')

    def test_bob_gets_404_on_alice_pages(self):
        for url in self.get_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_bob_cannot_change_alice_data(self):
        for url in self.post_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())
        self.assertTrue(Comment.objects.filter(pk=self.comment.pk).exists())
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.TODO)

    def test_bob_cannot_add_task_to_alice_project(self):
        url = reverse('task_create', args=[self.project.pk])
        response = self.client.post(url, {
            'title': 'Sneaky', 'status': 'todo', 'priority': 'low',
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Task.objects.count(), 1)


class AnonymousTests(BaseTestCase):
    def test_anonymous_is_redirected_to_login(self):
        for url in self.get_urls() + self.post_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('login')}?next={url}",
                    fetch_redirect_response=False,
                )


class OwnerTests(BaseTestCase):
    def setUp(self):
        self.client.login(username='alice', password='alice-pass-123')

    def test_advance_moves_task_forward(self):
        url = reverse('task_advance', args=[self.task.pk])
        self.client.post(url)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DOING)
        self.client.post(url)
        self.client.post(url)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DONE)

    def test_advance_refuses_get(self):
        url = reverse('task_advance', args=[self.task.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.TODO)

    def test_alice_can_delete_her_comment(self):
        url = reverse('comment_delete', args=[self.comment.pk])
        self.client.post(url)
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())


class TaskFormTests(TestCase):
    def data(self, **overrides):
        base = {'title': 'A task', 'description': '', 'status': 'todo', 'priority': 'low'}
        base.update(overrides)
        return base

    def test_past_due_date_is_rejected(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        form = TaskForm(data=self.data(due_date=yesterday.isoformat()))
        self.assertFalse(form.is_valid())
        self.assertIn('due_date', form.errors)

    def test_today_is_accepted(self):
        form = TaskForm(data=self.data(due_date=timezone.localdate().isoformat()))
        self.assertTrue(form.is_valid())

    def test_empty_title_is_rejected(self):
        form = TaskForm(data=self.data(title=''))
        self.assertFalse(form.is_valid())

class DashboardTests(BaseTestCase):
    def test_dashboard_requires_login(self):
        url = reverse('dashboard')
        response = self.client.get(url)
        self.assertRedirects(
            response, f"{reverse('login')}?next={url}", fetch_redirect_response=False
        )

    def test_counts_and_lists_only_own_tasks(self):
        today = timezone.localdate()
        Task.objects.create(
            project=self.project, title='Late', due_date=today - timedelta(days=2)
        )
        Task.objects.create(
            project=self.project, title='Late but done',
            due_date=today - timedelta(days=2), status=Task.Status.DONE,
        )
        Task.objects.create(
            project=self.project, title='Soon', due_date=today + timedelta(days=3)
        )
        bob_project = Project.objects.create(owner=self.bob, name='Bob project')
        Task.objects.create(
            project=bob_project, title='Bob late', due_date=today - timedelta(days=5)
        )

        self.client.login(username='alice', password='alice-pass-123')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual([t.title for t in response.context['overdue_tasks']], ['Late'])
        self.assertEqual([t.title for t in response.context['due_this_week']], ['Soon'])
        self.assertEqual(
            response.context['status_counts'], {'todo': 3, 'doing': 0, 'done': 1}
        )
class ProjectSearchTests(BaseTestCase):
    def test_search_only_returns_own_projects(self):
        Project.objects.create(owner=self.bob, name='Alice-themed project')
        self.client.login(username='bob', password='bob-pass-123')
        response = self.client.get(reverse('project_list'), {'q': 'Alice'})
        names = [p.name for p in response.context['page_obj']]
        self.assertEqual(names, ['Alice-themed project'])