from django.db import models
from django.contrib.auth.models import User


class Task(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='Medium'
    )
    category = models.CharField(max_length=50, default='General')
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        from django.utils import timezone
        return bool(
            self.due_date
            and self.due_date < timezone.localdate()
            and self.status != 'Completed'
        )

    @property
    def priority_score(self):
        from django.utils import timezone

        priority_points = {
            'Low': 10,
            'Medium': 30,
            'High': 60,
            'Urgent': 80,
        }
        score = priority_points.get(self.priority, 30)

        if self.due_date:
            days_left = (self.due_date - timezone.localdate()).days
            if days_left < 0:
                score += 20
            elif days_left == 0:
                score += 15
            elif days_left <= 2:
                score += 10
            elif days_left <= 7:
                score += 5

        return min(score, 100)
