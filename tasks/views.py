from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Task
from .serializers import TaskSerializer


class TaskListCreateView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        tasks = Task.objects.filter(user=request.user)

        task_status = request.query_params.get('status')

        if task_status:
            tasks = tasks.filter(status=task_status)

        serializer = TaskSerializer(tasks, many=True)

        return Response(serializer.data)

    def post(self, request):

        serializer = TaskSerializer(data=request.data)

        if serializer.is_valid():

            task = serializer.save(user=request.user)

            return Response(
                TaskSerializer(task).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class TaskDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):

        try:
            return Task.objects.get(
                pk=pk,
                user=request.user
            )

        except Task.DoesNotExist:
            return None

    def get(self, request, pk):

        task = self.get_object(request, pk)

        if not task:
            return Response(
                {"error": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TaskSerializer(task)

        return Response(serializer.data)

    def put(self, request, pk):

        task = self.get_object(request, pk)

        if not task:
            return Response(
                {"error": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TaskSerializer(
            task,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):

        task = self.get_object(request, pk)

        if not task:
            return Response(
                {"error": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        task.delete()

        return Response(
            {"message": "Task deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )