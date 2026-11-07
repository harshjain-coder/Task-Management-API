from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "priority", "category", "due_date")
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "description", "category")
from .models import TaskDependency, TaskTemplate, TemplateTask
admin.site.register(TaskDependency)
admin.site.register(TaskTemplate)
admin.site.register(TemplateTask)
