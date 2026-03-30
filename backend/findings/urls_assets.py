"""URL routes for Assets."""

from django.urls import path

from .views import AssetDetailView, AssetListCreateView

urlpatterns = [
    path("", AssetListCreateView.as_view(), name="asset-list-create"),
    path("<uuid:pk>/", AssetDetailView.as_view(), name="asset-detail"),
]
