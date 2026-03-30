"""User CRUD URL routes (admin-only)."""

from django.urls import path

from .views import UserDetailView, UserListCreateView

urlpatterns = [
    path("", UserListCreateView.as_view(), name="user-list-create"),
    path("<int:pk>/", UserDetailView.as_view(), name="user-detail"),
]
