from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("Pending","Pending"),("In Progress","In Progress"),("Completed","Completed")], default="Pending", max_length=20)),
                ("priority", models.CharField(choices=[("Low","Low"),("Medium","Medium"),("High","High"),("Urgent","Urgent")], default="Medium", max_length=10)),
                ("category", models.CharField(blank=True, max_length=80)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
