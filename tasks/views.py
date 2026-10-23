from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import User

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination

from .models import Task
from .serializers import TaskSerializer, RegisterSerializer


class TaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    'message': 'User registered successfully',
                    'username': user.username,
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = Task.objects.filter(user=request.user)

        task_status = request.query_params.get('status')
        priority = request.query_params.get('priority')
        category = request.query_params.get('category')
        search = request.query_params.get('search')
        ordering = request.query_params.get('ordering', '-created_at')

        if task_status:
            tasks = tasks.filter(status=task_status)
        if priority:
            tasks = tasks.filter(priority=priority)
        if category:
            tasks = tasks.filter(category__iexact=category)
        if search:
            tasks = tasks.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(category__icontains=search)
            )

        allowed_ordering = {
            'created_at', '-created_at', 'updated_at', '-updated_at',
            'due_date', '-due_date', 'title', '-title',
        }
        if ordering not in allowed_ordering:
            ordering = '-created_at'
        tasks = tasks.order_by(ordering)

        paginator = TaskPagination()
        page = paginator.paginate_queryset(tasks, request)
        serializer = TaskSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            task = serializer.save(user=request.user)
            return Response(
                TaskSerializer(task).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return Task.objects.get(pk=pk, user=request.user)
        except Task.DoesNotExist:
            return None

    def update_task(self, request, pk, partial=False):
        task = self.get_object(request, pk)
        if not task:
            return Response(
                {'error': 'Task not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TaskSerializer(task, data=request.data, partial=partial)
        if serializer.is_valid():
            if serializer.validated_data.get('status') == 'Completed':
                task.completed_at = task.completed_at or timezone.now()
            elif 'status' in serializer.validated_data:
                task.completed_at = None
            serializer.save()
            return Response(TaskSerializer(task).data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk):
        task = self.get_object(request, pk)
        if not task:
            return Response(
                {'error': 'Task not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(TaskSerializer(task).data)

    def put(self, request, pk):
        return self.update_task(request, pk, partial=True)

    def patch(self, request, pk):
        return self.update_task(request, pk, partial=True)

    def delete(self, request, pk):
        task = self.get_object(request, pk)
        if not task:
            return Response(
                {'error': 'Task not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = Task.objects.filter(user=request.user)
        total = tasks.count()
        completed = tasks.filter(status='Completed').count()
        pending = tasks.filter(status='Pending').count()
        in_progress = tasks.filter(status='In Progress').count()
        overdue = sum(1 for task in tasks if task.is_overdue)
        completion_rate = round((completed / total) * 100, 2) if total else 0

        return Response({
            'total_tasks': total,
            'completed': completed,
            'pending': pending,
            'in_progress': in_progress,
            'overdue': overdue,
            'completion_rate': completion_rate,
        })
