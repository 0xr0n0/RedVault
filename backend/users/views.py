"""
Views for authentication (login, token refresh, profile, change password).
"""

from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .permissions import IsAdminRole
from .serializers import (
    ChangePasswordSerializer,
    UserProfileSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


# ──────────────────────────────────────────────
# Auth endpoints
# ──────────────────────────────────────────────
class LoginThrottle(AnonRateThrottle):
    rate = "5/minute"


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — obtain JWT pair."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]


class RefreshView(TokenRefreshView):
    """POST /api/v1/auth/refresh/ — refresh access token."""

    permission_classes = [AllowAny]


class ProfileView(generics.RetrieveAPIView):
    """GET /api/v1/auth/profile/ — current user info."""

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/ — change own password."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(
            {"detail": "Password updated successfully."}, status=status.HTTP_200_OK
        )


# ──────────────────────────────────────────────
# User CRUD (admin-only)
# ──────────────────────────────────────────────
class UserListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/users/       — list all users (admin only)
    POST /api/v1/users/       — create a user (admin only)
    """

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdminRole]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["username", "date_joined", "role"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserSerializer
        return UserProfileSerializer


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/users/<id>/  — retrieve user
    PUT    /api/v1/users/<id>/  — full update
    PATCH  /api/v1/users/<id>/  — partial update
    DELETE /api/v1/users/<id>/  — deactivate user
    """

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserProfileSerializer

    def perform_destroy(self, instance):
        # Soft delete: deactivate instead of removing
        instance.is_active = False
        instance.save()
