from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("tasks", "0002_taskdependency_tasktemplate_templatetask")]
    operations = [
        migrations.AddField(
            model_name="task", name="parent_task",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="subtasks", to="tasks.task"),
        ),
        migrations.CreateModel(
            name="Reminder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("remind_at", models.DateTimeField()),
                ("message", models.CharField(blank=True, max_length=255)),
                ("is_sent", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reminders", to="tasks.task")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reminders", to="auth.user")),
            ],
            options={"ordering":["remind_at"]},
        ),
    ]
