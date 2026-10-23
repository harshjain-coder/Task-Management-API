from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Task


class TaskAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='harsh', password='StrongPass123')
        self.other_user = User.objects.create_user(username='other', password='StrongPass123')
        self.client.force_authenticate(user=self.user)

    def test_create_task_with_priority_and_category(self):
        response = self.client.post(reverse('task-list-create'), {
            'title': 'Learn Django',
            'description': 'Practice REST APIs',
            'priority': 'High',
            'category': 'Learning',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['priority'], 'High')
        self.assertEqual(response.data['category'], 'Learning')
        self.assertGreater(response.data['priority_score'], 0)

    def test_user_can_only_see_own_tasks(self):
        Task.objects.create(user=self.other_user, title='Private task')
        Task.objects.create(user=self.user, title='My task')

        response = self.client.get(reverse('task-list-create'))

        self.assertEqual(response.status_code, 200)
        titles = [task['title'] for task in response.data['results']]
        self.assertIn('My task', titles)
        self.assertNotIn('Private task', titles)

    def test_overdue_detection(self):
        task = Task.objects.create(
            user=self.user,
            title='Overdue task',
            due_date=timezone.localdate() - timedelta(days=1),
            priority='High',
        )

        response = self.client.get(reverse('task-detail', args=[task.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_overdue'])

    def test_dashboard(self):
        Task.objects.create(user=self.user, title='Done', status='Completed')
        Task.objects.create(user=self.user, title='Pending')
        Task.objects.create(
            user=self.user,
            title='Late',
            due_date=timezone.localdate() - timedelta(days=1),
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_tasks'], 3)
        self.assertEqual(response.data['completed'], 1)
        self.assertEqual(response.data['overdue'], 1)
        self.assertEqual(response.data['completion_rate'], 33.33)
