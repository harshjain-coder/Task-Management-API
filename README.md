# Smart Task Management API

A production-style REST API built with Django and Django REST Framework for secure task management, smart prioritization, and productivity analytics.

## Features

- JWT authentication with access and refresh tokens
- User registration and user-specific task access
- Task CRUD with validation and PATCH support
- Status: Pending, In Progress, Completed
- Priority: Low, Medium, High, Urgent
- Categories and due dates
- Smart priority score based on priority and deadline
- Automatic overdue task detection
- Search, filtering and sorting
- Pagination
- Productivity dashboard with completion rate
- Swagger/OpenAPI documentation
- Automated API tests including user-isolation tests
- PostgreSQL support with SQLite fallback for local development

## Tech Stack

- Python
- Django
- Django REST Framework
- JWT / SimpleJWT
- PostgreSQL
- Swagger / OpenAPI
- Postman
- Gunicorn
- Render

## API Endpoints

### Authentication

POST `/api/register/`

POST `/api/login/`

POST `/api/token/refresh/`

### Tasks

GET `/api/tasks/`

POST `/api/tasks/`

GET `/api/tasks/<id>/`

PUT/PATCH `/api/tasks/<id>/`

DELETE `/api/tasks/<id>/`

GET `/api/tasks/dashboard/`

### Search, Filter and Sort

`/api/tasks/?search=django`

`/api/tasks/?status=Completed`

`/api/tasks/?priority=High`

`/api/tasks/?category=Learning`

`/api/tasks/?ordering=due_date`

`/api/tasks/?page=2&page_size=10`

### API Documentation

Swagger UI: `/api/docs/`

OpenAPI schema: `/api/schema/`

## Smart Priority Score

Each task receives a score from 0 to 100 using a simple rule-based system. Higher task priority and closer or overdue deadlines increase the score, helping users identify tasks that need attention first.

## Authentication

Send the JWT access token with protected requests:

`Authorization: Bearer <access_token>`

## Run Locally

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Run tests:

```bash
python manage.py test
```
