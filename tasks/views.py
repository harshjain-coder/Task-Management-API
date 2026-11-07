from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
import json
import os
import time
from google import genai
from dotenv import load_dotenv
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))
from django.utils import timezone
from .models import Task, TaskDependency, TaskTemplate, Reminder
from .serializers import RegisterSerializer, TaskSerializer, ReminderSerializer,TaskTemplateSerializer


def call_gemini_with_retry(client, model, input_text, response_format=None, max_retries=3):
    """Retry transient Gemini rate-limit and server errors with short backoff."""
    for attempt in range(max_retries):
        try:
            kwargs = {"model": model, "input": input_text}
            if response_format is not None:
                kwargs["response_format"] = response_format
            return client.interactions.create(**kwargs)
        except Exception as exc:
            error_text = str(exc).lower()
            retryable = (
                "429", "500", "502", "503", "504",
                "rate limit", "resource exhausted", "service unavailable",
                "internal server error", "bad gateway", "gateway timeout",
                "high demand", "temporarily unavailable",
            )
            if not any(marker in error_text for marker in retryable):
                raise
            if attempt == max_retries - 1:
                raise
            delay = 2 ** (attempt + 1)
            print(f"Gemini temporarily unavailable; retrying in {delay}s "
                  f"(attempt {attempt + 1}/{max_retries}).", flush=True)
            time.sleep(delay)


class TaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Account created successfully.",
            "user": {"id": user.id, "username": user.username, "email": user.email},
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=201)

class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TaskPagination

    def get_queryset(self):
        qs = Task.objects.filter(user=self.request.user)
        params = self.request.query_params

        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("priority"):
            qs = qs.filter(priority=params["priority"])
        if params.get("category"):
            qs = qs.filter(category__icontains=params["category"])
        if params.get("search"):
            q = params["search"]
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(category__icontains=q))

        ordering = params.get("ordering", "-created_at")
        allowed = {"created_at", "-created_at", "updated_at", "-updated_at",
                   "due_date", "-due_date", "title", "-title"}
        if ordering in allowed:
            qs = qs.order_by(ordering)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Task.objects.filter(user=request.user)
        total = qs.count()
        completed = qs.filter(status="Completed").count()
        pending = qs.filter(status="Pending").count()
        in_progress = qs.filter(status="In Progress").count()
        overdue = sum(1 for task in qs if task.is_overdue)
        rate = round((completed / total) * 100, 1) if total else 0
        return Response({
            "total": total,
            "completed": completed,
            "pending": pending,
            "in_progress": in_progress,
            "overdue": overdue,
            "completion_rate": rate,
        })


class AITaskCreateView(APIView):
    """Turn natural-language instructions into real tasks using the Gemini Interactions API."""
    permission_classes = [permissions.IsAuthenticated]

    TASK_SCHEMA = {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Urgent"]},
                        "category": {"type": "string"},
                        "due_date": {"type": "string"},
                        "status": {"type": "string", "enum": ["Pending", "In Progress", "Completed"]},
                    },
                    "required": ["title", "description", "priority", "category", "due_date", "status"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["tasks"],
        "additionalProperties": False,
    }

    def post(self, request):
        message = str(request.data.get("message", "")).strip()
        if not message:
            return Response({"detail": "Please describe what you want to create."}, status=400)
        if len(message) > 5000:
            return Response({"detail": "Message is too long. Keep it under 5000 characters."}, status=400)

        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key or api_key.lower() in {"your_actual_api_key_here", "your_real_api_key_here", "change-me"}:
            return Response({
                "detail": "AI Task Assistant is not configured. Add GEMINI_API_KEY to your backend .env file, then restart Django."
            }, status=503)

        today = timezone.localdate().isoformat()
        model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"
        instructions = f"""
You are the AI Task Assistant for a task-management application.
Today's date is {today} and the user's timezone is Asia/Kolkata.
Understand English, Hindi and Hinglish.
Convert the user's request into ONLY the actionable tasks they explicitly requested.
Create one object for every distinct task. Never invent unrelated tasks.
For each task:
- title: concise actionable title, max 200 characters
- description: useful short description
- priority: infer urgency; if unclear use Medium
- category: choose a simple category such as Work, Study, Personal, Health, Finance, etc.; if unclear use Personal
- due_date: YYYY-MM-DD when a deadline is stated or can be resolved from relative language such as today, tomorrow, kal, parso, next Monday; otherwise empty string
- status: Pending unless the user explicitly asks for In Progress or Completed
Return only data matching the JSON schema.
""".strip()

        try:
            client = genai.Client(api_key=api_key, http_options={"api_version": "v1"})
            response = call_gemini_with_retry(
                client=client,
                model=model,
                input_text=f"{instructions}\n\nUSER REQUEST:\n{message}",
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": self.TASK_SCHEMA,
                },
            )
            parsed = json.loads(response.output_text)
        except Exception as exc:
            # Keep provider details and credentials out of the browser response.
            print(f"Gemini task creation failed: {exc.__class__.__name__}: {exc}", flush=True)
            return Response({
                "detail": "AI service is temporarily unavailable. Please try again in a moment."
            }, status=503)

        task_data = parsed.get("tasks", [])
        if not task_data:
            return Response({"detail": "I couldn't find any actionable tasks in that message."}, status=400)
        task_data = task_data[:20]

        allowed_priorities = {"Low", "Medium", "High", "Urgent"}
        allowed_statuses = {"Pending", "In Progress", "Completed"}
        created = []
        try:
            with transaction.atomic():
                for item in task_data:
                    title = str(item.get("title", "")).strip()[:200]
                    if not title:
                        continue
                    raw_due = str(item.get("due_date", "")).strip()
                    due_date = None
                    if raw_due:
                        try:
                            due_date = timezone.datetime.strptime(raw_due, "%Y-%m-%d").date()
                        except ValueError:
                            due_date = None
                    task = Task.objects.create(
                        user=request.user,
                        title=title,
                        description=str(item.get("description", "")).strip(),
                        priority=item.get("priority") if item.get("priority") in allowed_priorities else "Medium",
                        category=str(item.get("category", "")).strip()[:80] or "Personal",
                        due_date=due_date,
                        status=item.get("status") if item.get("status") in allowed_statuses else "Pending",
                    )
                    created.append(task)
        except Exception:
            return Response({"detail": "AI generated tasks, but they could not be saved. Check the backend terminal."}, status=500)

        return Response({
            "message": f"Created {len(created)} task{'s' if len(created) != 1 else ''} successfully.",
            "tasks": TaskSerializer(created, many=True).data,
        }, status=201)


class AIProductivityInsightsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Task.objects.filter(user=request.user)
        total = qs.count()
        completed = qs.filter(status="Completed").count()
        overdue = sum(1 for t in qs if t.is_overdue)
        urgent = qs.filter(priority="Urgent").exclude(status="Completed")
        categories = {}
        for t in qs.exclude(status="Completed"):
            key = t.category or "Uncategorized"
            categories[key] = categories.get(key, 0) + 1
        top_category = max(categories, key=categories.get) if categories else None
        base = {
            "summary": f"You have {total} tasks, {completed} completed, and {overdue} overdue.",
            "recommendations": [],
            "metrics": {"total": total, "completed": completed, "overdue": overdue, "urgent_open": urgent.count(), "completion_rate": round(completed * 100 / total, 1) if total else 0, "top_category": top_category}
        }
        if overdue:
            base["recommendations"].append("Clear overdue tasks first and move the most important one into In Progress.")
        if urgent.exists():
            base["recommendations"].append("Review your urgent tasks and break the biggest one into smaller subtasks.")
        if total and completed / total >= 0.7:
            base["recommendations"].append("Your completion rate is strong. Protect a focused work block for the remaining high-priority tasks.")
        if not base["recommendations"]:
            base["recommendations"].append("Start by setting due dates and priorities on your most important tasks.")

        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"
        if api_key and model:
            try:
                client = genai.Client(api_key=api_key, http_options={"api_version": "v1"})
                prompt = json.dumps({"metrics": base["metrics"], "tasks": list(qs.values("title","status","priority","category","due_date")[:100])}, default=str)
                response = call_gemini_with_retry(
                    client=client,
                    model=model,
                    input_text=("Give concise, practical productivity insights from the following task data. "
                                "Return one short summary and exactly 3 actionable recommendations. "
                                "Do not invent facts.\n" + prompt),
                )
                text = response.output_text.strip()
                if text:
                    base["ai_insight"] = text
            except Exception:
                pass
        return Response(base)


class ReminderListCreateView(generics.ListCreateAPIView):
    serializer_class = ReminderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Reminder.objects.filter(user=self.request.user).select_related("task")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReminderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReminderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Reminder.objects.filter(user=self.request.user).select_related("task")


def dependency_would_cycle(prerequisite, blocked):
    """Return True if adding prerequisite -> blocked would create a dependency cycle."""
    target_id = prerequisite.id
    stack = [blocked.id]
    seen = set()
    while stack:
        current_id = stack.pop()
        if current_id in seen:
            continue
        seen.add(current_id)
        if current_id == target_id:
            return True
        stack.extend(TaskDependency.objects.filter(blocked_task_id=current_id).values_list("prerequisite_task_id", flat=True))
    return False


class DependencyListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        prerequisite_id = request.data.get("prerequisite_task_id")
        blocked_id = request.data.get("blocked_task_id")
        if not prerequisite_id or not blocked_id:
            return Response({"detail": "prerequisite_task_id and blocked_task_id are required."}, status=400)
        if str(prerequisite_id) == str(blocked_id):
            return Response({"detail": "A task cannot depend on itself."}, status=400)
        tasks = Task.objects.filter(user=request.user, id__in=[prerequisite_id, blocked_id])
        if tasks.count() != 2:
            return Response({"detail": "Both tasks must belong to your account."}, status=404)
        prerequisite = tasks.get(id=prerequisite_id)
        blocked = tasks.get(id=blocked_id)
        if dependency_would_cycle(prerequisite, blocked):
            return Response({"detail": "This dependency would create a cycle."}, status=400)
        dependency, created = TaskDependency.objects.get_or_create(
            prerequisite_task=prerequisite, blocked_task=blocked
        )
        if not created:
            return Response({"detail": "Dependency already exists."}, status=200)
        return Response(TaskSerializer(blocked, context={"request": request}).data, status=201)


class DependencyDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, prerequisite_id, blocked_id):
        deleted, _ = TaskDependency.objects.filter(
            prerequisite_task__id=prerequisite_id,
            blocked_task__id=blocked_id,
            prerequisite_task__user=request.user,
            blocked_task__user=request.user,
        ).delete()
        if not deleted:
            return Response({"detail": "Dependency not found."}, status=404)
        return Response(status=204)


class TemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskTemplate.objects.filter(user=self.request.user).prefetch_related("items")


class TemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskTemplate.objects.filter(user=self.request.user).prefetch_related("items")


class TemplateApplyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            template = TaskTemplate.objects.prefetch_related("items").get(pk=pk, user=request.user)
        except TaskTemplate.DoesNotExist:
            return Response({"detail": "Template not found."}, status=404)
        if not template.items.exists():
            return Response({"detail": "This template has no tasks."}, status=400)

        from datetime import timedelta
        today = timezone.localdate()
        created = []
        with transaction.atomic():
            for item in template.items.all():
                due = today + timedelta(days=item.relative_due_days) if item.relative_due_days is not None else None
                created.append(Task.objects.create(
                    user=request.user, title=item.title, description=item.description,
                    priority=item.priority, category=item.category, due_date=due
                ))
        return Response({
            "message": f"Created {len(created)} tasks from '{template.name}'.",
            "tasks": TaskSerializer(created, many=True, context={"request": request}).data,
        }, status=201)
