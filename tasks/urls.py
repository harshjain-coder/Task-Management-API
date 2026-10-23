from django.urls import path

from .views import (
    RegisterView,
    TaskListCreateView,
    TaskDetailView,
    DashboardView,
)


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('tasks/', TaskListCreateView.as_view(), name='task-list-create'),
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('tasks/dashboard/', DashboardView.as_view(), name='dashboard'),
]
