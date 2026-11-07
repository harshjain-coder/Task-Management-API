from django.conf import settings
from django.db import models
from django.utils import timezone


class Task(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    ]
    PRIORITY_CHOICES = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
        ("Urgent", "Urgent"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="Medium")
    category = models.CharField(max_length=80, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    parent_task = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="subtasks")

    @property
    def is_overdue(self):
        return bool(self.due_date and self.due_date < timezone.localdate() and self.status != "Completed")

    @property
    def priority_score(self):
        base = {"Low": 10, "Medium": 30, "High": 60, "Urgent": 80}.get(self.priority, 30)
        boost = 0
        if self.due_date and self.status != "Completed":
            days = (self.due_date - timezone.localdate()).days
            if days < 0:
                boost = 20
            elif days == 0:
                boost = 15
            elif days <= 2:
                boost = 10
            elif days <= 7:
                boost = 5
        return min(base + boost, 100)

    def save(self, *args, **kwargs):
        if self.status == "Completed" and self.completed_at is None:
            self.completed_at = timezone.now()
        elif self.status != "Completed":
            self.completed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class TaskDependency(models.Model):
    """A directed relationship: blocked_task cannot start until prerequisite_task is complete."""
    prerequisite_task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="blocks")
    blocked_task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="dependencies")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["prerequisite_task", "blocked_task"], name="unique_task_dependency"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.prerequisite_task_id == self.blocked_task_id:
            raise ValidationError("A task cannot depend on itself.")
        if self.prerequisite_task.user_id != self.blocked_task.user_id:
            raise ValidationError("Tasks must belong to the same user.")

    def __str__(self):
        return f"{self.blocked_task.title} depends on {self.prerequisite_task.title}"


class TaskTemplate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="task_templates")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_template_name_per_user"),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class TemplateTask(models.Model):
    template = models.ForeignKey(TaskTemplate, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=Task.PRIORITY_CHOICES, default="Medium")
    category = models.CharField(max_length=80, blank=True)
    relative_due_days = models.PositiveIntegerField(null=True, blank=True, help_text="Days after applying the template.")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.template.name}: {self.title}"


class Reminder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reminders")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="reminders")
    remind_at = models.DateTimeField()
    message = models.CharField(max_length=255, blank=True)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["remind_at"]

    def __str__(self):
        return f"Reminder: {self.task.title} at {self.remind_at}"
