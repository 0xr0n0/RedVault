"""URL routes for Findings and Evidence."""

from django.urls import path

from .views import (
    EvidenceDetailView,
    EvidenceListCreateView,
    FindingDetailView,
    FindingHistoryView,
    FindingListCreateView,
    FindingStatsView,
    FindingTimelineView,
)

urlpatterns = [
    path("stats/", FindingStatsView.as_view(), name="finding-stats"),
    path("timeline/", FindingTimelineView.as_view(), name="finding-timeline"),
    path("", FindingListCreateView.as_view(), name="finding-list-create"),
    path("<uuid:pk>/", FindingDetailView.as_view(), name="finding-detail"),
    # History / audit log
    path(
        "<uuid:finding_pk>/history/",
        FindingHistoryView.as_view(),
        name="finding-history",
    ),
    # Nested evidence
    path(
        "<uuid:finding_pk>/evidence/",
        EvidenceListCreateView.as_view(),
        name="evidence-list-create",
    ),
    path(
        "<uuid:finding_pk>/evidence/<uuid:pk>/",
        EvidenceDetailView.as_view(),
        name="evidence-detail",
    ),
]
