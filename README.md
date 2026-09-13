# Task Management API

A RESTful Task Management API built using Django and Django REST Framework.

## Features

- JWT Authentication
- User-specific tasks
- Create, Read, Update and Delete tasks
- Task status management
- Task filtering by status
- PostgreSQL database
- REST API architecture

## Tech Stack

- Python
- Django
- Django REST Framework
- JWT
- PostgreSQL
- Gunicorn
- Render

## API Endpoints

POST /api/login/

GET /api/tasks/

POST /api/tasks/

GET /api/tasks/<id>/

PUT /api/tasks/<id>/

DELETE /api/tasks/<id>/

GET /api/tasks/?status=Completed

## Authentication

Use JWT Bearer Token:

Authorization: Bearer <access_token>