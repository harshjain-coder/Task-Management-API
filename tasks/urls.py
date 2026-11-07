from django.urls import path
from .views import (
    RegisterView, TaskListCreateView, TaskDetailView, DashboardView, AITaskCreateView,
    DependencyListView, DependencyDeleteView, TemplateListCreateView, TemplateDetailView, TemplateApplyView, AIProductivityInsightsView, ReminderListCreateView, ReminderDetailView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("tasks/", TaskListCreateView.as_view(), name="tasks"),
    path("tasks/<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
    path("tasks/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("ai/create-tasks/", AITaskCreateView.as_view(), name="ai-create-tasks"),
    path("dependencies/", DependencyListView.as_view(), name="dependency-create"),
    path("dependencies/<int:prerequisite_id>/<int:blocked_id>/", DependencyDeleteView.as_view(), name="dependency-delete"),
    path("templates/", TemplateListCreateView.as_view(), name="template-list-create"),
    path("templates/<int:pk>/", TemplateDetailView.as_view(), name="template-detail"),
    path("templates/<int:pk>/apply/", TemplateApplyView.as_view(), name="template-apply"),
    path("ai/insights/", AIProductivityInsightsView.as_view(), name="ai-insights"),
    path("reminders/", ReminderListCreateView.as_view(), name="reminder-list-create"),
    path("reminders/<int:pk>/", ReminderDetailView.as_view(), name="reminder-detail"),
]
