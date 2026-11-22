from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    STUDENT = "student", "学生"
    TEACHER = "teacher", "教师"
    ADMIN = "admin", "业务管理员"


class User(AbstractUser):
    role = models.CharField(max_length=7, choices=Role.choices)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(role__in=Role.values), name="accounts_user_valid_role"),
        ]
