"""
Custom permissions for role-based access control.
"""

from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Only users with the 'admin' role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsAnalystOrAbove(BasePermission):
    """Admin or Analyst roles."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "analyst")
        )


class IsViewerOrAbove(BasePermission):
    """Any authenticated user with a valid role (viewer, analyst, admin)."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "analyst", "viewer")
        )
