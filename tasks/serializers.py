from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Task, TaskDependency, TaskTemplate, TemplateTask, Reminder


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class TaskSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    priority_score = serializers.ReadOnlyField()
    dependency_ids = serializers.PrimaryKeyRelatedField(
        many=True, source="dependencies", queryset=Task.objects.all(), required=False, write_only=True
    )
    dependencies = serializers.SerializerMethodField(read_only=True)
    blocked_by = serializers.SerializerMethodField(read_only=True)
    parent_task_id = serializers.PrimaryKeyRelatedField(source="parent_task", queryset=Task.objects.all(), required=False, allow_null=True)
    subtasks = serializers.SerializerMethodField(read_only=True)
    subtask_progress = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id", "user", "title", "description", "status", "priority",
            "category", "due_date", "created_at", "updated_at", "completed_at",
            "is_overdue", "priority_score", "dependency_ids", "dependencies", "blocked_by", "parent_task_id", "subtasks", "subtask_progress"
        )
        read_only_fields = (
            "id", "user", "created_at", "updated_at", "completed_at",
            "is_overdue", "priority_score", "dependencies", "blocked_by", "subtasks", "subtask_progress"
        )

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Title cannot be empty.")
        return value

    def validate_parent_task_id(self, value):
        if value is None:
            return value
        user = self.context["request"].user
        if value.user_id != user.id:
            raise serializers.ValidationError("Parent task must belong to your account.")
        task = self.instance
        if task and value.id == task.id:
            raise serializers.ValidationError("A task cannot be its own parent.")
        return value

    def validate_dependency_ids(self, value):
        task = self.instance
        user = self.context["request"].user
        ids = {obj.id for obj in value}
        if task and task.id in ids:
            raise serializers.ValidationError("A task cannot depend on itself.")
        if any(obj.user_id != user.id for obj in value):
            raise serializers.ValidationError("You can only use your own tasks as dependencies.")
        return value

    def create(self, validated_data):
        dependencies = validated_data.pop("dependencies", [])
        task = super().create(validated_data)
        for prerequisite in dependencies:
            TaskDependency.objects.get_or_create(prerequisite_task=prerequisite, blocked_task=task)
        return task

    def update(self, instance, validated_data):
        dependencies = validated_data.pop("dependencies", None)
        task = super().update(instance, validated_data)
        if dependencies is not None:
            TaskDependency.objects.filter(blocked_task=task).delete()
            for prerequisite in dependencies:
                TaskDependency.objects.get_or_create(prerequisite_task=prerequisite, blocked_task=task)
        return task

    def get_dependencies(self, obj):
        return [{"id": d.prerequisite_task_id, "title": d.prerequisite_task.title, "status": d.prerequisite_task.status}
                for d in obj.dependencies.select_related("prerequisite_task").all()]

    def get_blocked_by(self, obj):
        return [{"id": d.blocked_task_id, "title": d.blocked_task.title, "status": d.blocked_task.status}
                for d in obj.blocks.select_related("blocked_task").all()]

    def get_subtasks(self, obj):
        return [{"id": t.id, "title": t.title, "status": t.status, "priority": t.priority}
                for t in obj.subtasks.all()[:20]]

    def get_subtask_progress(self, obj):
        total = obj.subtasks.count()
        done = obj.subtasks.filter(status="Completed").count()
        return {"completed": done, "total": total, "percent": round(done * 100 / total) if total else 0}


class ReminderSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source="task.title", read_only=True)
    class Meta:
        model = Reminder
        fields = ("id", "task", "task_title", "remind_at", "message", "is_sent", "created_at")
        read_only_fields = ("id", "task_title", "created_at")

    def validate_task(self, value):
        if value.user_id != self.context["request"].user.id:
            raise serializers.ValidationError("Task must belong to your account.")
        return value


class TemplateTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateTask
        fields = ("id", "title", "description", "priority", "category", "relative_due_days", "position")

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Template task title cannot be empty.")
        return value


class TaskTemplateSerializer(serializers.ModelSerializer):
    items = TemplateTaskSerializer(many=True)

    class Meta:
        model = TaskTemplate
        fields = ("id", "name", "description", "created_at", "updated_at", "items")
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        template = TaskTemplate.objects.create(user=self.context["request"].user, **validated_data)
        TemplateTask.objects.bulk_create([TemplateTask(template=template, **item) for item in items])
        return template

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items is not None:
            instance.items.all().delete()
            TemplateTask.objects.bulk_create([TemplateTask(template=instance, **item) for item in items])
        return instance
