"""URL routes for Report Generation."""

from django.urls import path

from .views import GenerateReportView, GeneratedReportListView, GeneratedReportDetailView

urlpatterns = [
    # Generated reports
    path("", GeneratedReportListView.as_view(), name="report-list"),
    path("<uuid:pk>/", GeneratedReportDetailView.as_view(), name="report-detail"),
    # Report generation
    path("generate/", GenerateReportView.as_view(), name="report-generate"),
]
