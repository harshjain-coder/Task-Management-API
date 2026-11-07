from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("tasks", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="TaskTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="task_templates", to="auth.user")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="TaskDependency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("blocked_task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dependencies", to="tasks.task")),
                ("prerequisite_task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blocks", to="tasks.task")),
            ],
        ),
        migrations.CreateModel(
            name="TemplateTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("priority", models.CharField(choices=[("Low", "Low"), ("Medium", "Medium"), ("High", "High"), ("Urgent", "Urgent")], default="Medium", max_length=10)),
                ("category", models.CharField(blank=True, max_length=80)),
                ("relative_due_days", models.PositiveIntegerField(blank=True, help_text="Days after applying the template.", null=True)),
                ("position", models.PositiveIntegerField(default=0)),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="tasks.tasktemplate")),
            ],
            options={"ordering": ["position", "id"]},
        ),
        migrations.AddConstraint(
            model_name="taskdependency",
            constraint=models.UniqueConstraint(fields=("prerequisite_task", "blocked_task"), name="unique_task_dependency"),
        ),
        migrations.AddConstraint(
            model_name="tasktemplate",
            constraint=models.UniqueConstraint(fields=("user", "name"), name="unique_template_name_per_user"),
        ),
    ]
