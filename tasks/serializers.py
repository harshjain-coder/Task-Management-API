from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Task


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class TaskSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)
    priority_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'user', 'title', 'description', 'status', 'priority',
            'category', 'due_date', 'created_at', 'updated_at',
            'completed_at', 'is_overdue', 'priority_score'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at', 'completed_at',
            'is_overdue', 'priority_score'
        ]

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Title cannot be empty.')
        return value
