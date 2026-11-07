from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase
from .models import Task

class TaskAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_authenticate(user=self.user)

    def test_create_task(self):
        response = self.client.post("/api/tasks/", {
            "title": "Learn Django",
            "description": "Build a REST API",
            "priority": "High",
            "category": "Learning",
            "due_date": str(timezone.localdate() + timedelta(days=2)),
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertGreater(response.data["priority_score"], 0)

    def test_dashboard(self):
        Task.objects.create(user=self.user, title="Done", status="Completed")
        response = self.client.get("/api/tasks/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["completed"], 1)
