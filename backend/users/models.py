"""
Custom User model with role-based access (Admin, Analyst, Viewer).
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user with a role field for RBAC."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        ANALYST = "analyst", "Analyst"
        VIEWER = "viewer", "Viewer"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER,
        help_text="Determines the user's permission level.",
    )
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_analyst(self):
        return self.role == self.Role.ANALYST

    @property
    def is_viewer(self):
        return self.role == self.Role.VIEWER
