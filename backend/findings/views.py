"""
Views for Findings, Evidence, ReportTemplates, and Report Generation.
"""

import json
import os
import re
import subprocess
import sys
import uuid as uuid_mod
from collections import Counter
from datetime import date

from django.conf import settings
from django.db import models
from django.db.models import Avg, Count, Q, Case, When, IntegerField
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from rest_framework import generics, parsers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdminRole, IsAnalystOrAbove, IsViewerOrAbove

from .models import Asset, Client, Evidence, Finding, FindingHistory, GeneratedReport
from .serializers import (
    AssetDetailSerializer,
    AssetListSerializer,
    ClientDetailSerializer,
    ClientListSerializer,
    EvidenceSerializer,
    FindingDetailSerializer,
    FindingHistorySerializer,
    FindingListSerializer,
    GeneratedReportSerializer,
    GenerateReportRequestSerializer,
)


# ───────────────────────────────────────────────
# Client CRUD
# ───────────────────────────────────────────────
class ClientListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/clients/       — list clients (viewer+)
    POST /api/v1/clients/       — create client (admin only)
    """

    queryset = (
        Client.objects.select_related("created_by")
        .annotate(asset_count=Count("assets"))
        .order_by("name")
    )
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ClientDetailSerializer
        return ClientListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated(), IsViewerOrAbove()]


class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/clients/<uuid>/  — retrieve
    PUT    /api/v1/clients/<uuid>/  — full update (admin only)
    PATCH  /api/v1/clients/<uuid>/  — partial update (admin only)
    DELETE /api/v1/clients/<uuid>/  — delete (admin only)
    """

    queryset = (
        Client.objects.select_related("created_by")
        .annotate(asset_count=Count("assets"))
    )
    serializer_class = ClientDetailSerializer

    def get_permissions(self):
        if self.request.method in ("DELETE", "PUT", "PATCH"):
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated(), IsViewerOrAbove()]


# ───────────────────────────────────────────────
# Asset CRUD
# ───────────────────────────────────────────────
class AssetListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/assets/       — list assets (viewer+)
    POST /api/v1/assets/       — create asset (analyst+)
    """

    queryset = (
        Asset.objects.select_related("created_by", "client")
        .annotate(finding_count=Count("findings"))
        .order_by("name")
    )
    filterset_fields = ["asset_type", "client"]
    search_fields = ["name", "ip_address", "hostname", "url", "os", "description"]
    ordering_fields = ["name", "asset_type", "created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AssetDetailSerializer
        return AssetListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAnalystOrAbove()]
        return [IsAuthenticated(), IsViewerOrAbove()]


class AssetDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/assets/<uuid>/  — retrieve
    PUT    /api/v1/assets/<uuid>/  — full update (analyst+)
    PATCH  /api/v1/assets/<uuid>/  — partial update (analyst+)
    DELETE /api/v1/assets/<uuid>/  — delete (admin only)
    """

    queryset = (
        Asset.objects.select_related("created_by", "client")
        .annotate(finding_count=Count("findings"))
    )
    serializer_class = AssetDetailSerializer

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsAdminRole()]
        if self.request.method in ("PUT", "PATCH"):
            return [IsAuthenticated(), IsAnalystOrAbove()]
        return [IsAuthenticated(), IsViewerOrAbove()]


# ──────────────────────────────────────────────
# Finding CRUD
# ──────────────────────────────────────────────
class FindingListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/findings/       — list findings (viewer+)
    POST /api/v1/findings/       — create finding (analyst+)
    """

    queryset = Finding.objects.select_related("created_by", "assigned_to", "asset").annotate(
        evidence_count=models.Count("evidences")
    ).order_by("-created_at")
    filterset_fields = ["severity", "status", "assigned_to", "asset"]
    search_fields = ["title", "description", "affected_assets", "references"]
    ordering_fields = ["created_at", "severity", "cvss_score", "status"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return FindingDetailSerializer
        return FindingListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAnalystOrAbove()]
        return [IsAuthenticated(), IsViewerOrAbove()]


class FindingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/findings/<uuid>/  — retrieve
    PUT    /api/v1/findings/<uuid>/  — full update (analyst+)
    PATCH  /api/v1/findings/<uuid>/  — partial update (analyst+)
    DELETE /api/v1/findings/<uuid>/  — delete (admin only)
    """

    queryset = Finding.objects.select_related("created_by", "assigned_to", "asset").prefetch_related("evidences")
    serializer_class = FindingDetailSerializer

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsAdminRole()]
        if self.request.method in ("PUT", "PATCH"):
            return [IsAuthenticated(), IsAnalystOrAbove()]
        return [IsAuthenticated(), IsViewerOrAbove()]


class FindingHistoryView(generics.ListAPIView):
    """
    GET /api/v1/findings/<uuid>/history/  — chronological audit log
    """

    serializer_class = FindingHistorySerializer
    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    def get_queryset(self):
        return (
            FindingHistory.objects
            .filter(finding_id=self.kwargs["finding_pk"])
            .select_related("changed_by")
            .order_by("timestamp")
        )


# ──────────────────────────────────────────────
# Evidence CRUD (nested under findings)
# ──────────────────────────────────────────────
class EvidenceListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/findings/<uuid>/evidence/  — list evidence
    POST /api/v1/findings/<uuid>/evidence/  — upload evidence (analyst+)
    """

    serializer_class = EvidenceSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        return Evidence.objects.filter(finding_id=self.kwargs["finding_pk"])

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAnalystOrAbove()]
        return [IsAuthenticated(), IsViewerOrAbove()]

    def perform_create(self, serializer):
        serializer.save(
            finding_id=self.kwargs["finding_pk"],
            uploaded_by=self.request.user,
        )


class EvidenceDetailView(generics.RetrieveDestroyAPIView):
    """
    GET    /api/v1/findings/<uuid>/evidence/<uuid>/  — download/info
    DELETE /api/v1/findings/<uuid>/evidence/<uuid>/  — delete (analyst+)
    """

    serializer_class = EvidenceSerializer

    def get_queryset(self):
        return Evidence.objects.filter(finding_id=self.kwargs["finding_pk"])

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsAnalystOrAbove()]
        return [IsAuthenticated(), IsViewerOrAbove()]

    def perform_destroy(self, instance):
        if instance.file:
            instance.file.delete(save=False)
        instance.delete()


# ──────────────────────────────────────────────
# Dashboard Statistics
# ──────────────────────────────────────────────
class FindingStatsView(APIView):
    """
    GET /api/v1/findings/stats/ — aggregated finding statistics.
    All counts computed in a single DB round-trip.
    """

    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    def get(self, request):
        # Aggregate everything in one query
        stats = Finding.objects.aggregate(
            total=Count("id"),
            # By status
            open=Count("id", filter=Q(status="open")),
            in_progress=Count("id", filter=Q(status="in_progress")),
            remediated=Count("id", filter=Q(status="remediated")),
            closed=Count("id", filter=Q(status="closed")),
            accepted=Count("id", filter=Q(status="accepted")),
            # By severity
            critical=Count("id", filter=Q(severity="critical")),
            high=Count("id", filter=Q(severity="high")),
            medium=Count("id", filter=Q(severity="medium")),
            low=Count("id", filter=Q(severity="low")),
            informational=Count("id", filter=Q(severity="informational")),
            # Open by severity (the most actionable metric)
            open_critical=Count("id", filter=Q(status="open", severity="critical")),
            open_high=Count("id", filter=Q(status="open", severity="high")),
            open_medium=Count("id", filter=Q(status="open", severity="medium")),
            open_low=Count("id", filter=Q(status="open", severity="low")),
            open_informational=Count("id", filter=Q(status="open", severity="informational")),
            # Average CVSS
            avg_cvss=Avg("cvss_score"),
            # Evidence count
            total_evidence=Count("evidences"),
        )

        # Recent findings (last 5)
        recent = (
            Finding.objects.select_related("created_by")
            .order_by("-created_at")
            .values("id", "title", "severity", "status", "created_at", "created_by__username")[:5]
        )

        stats["avg_cvss"] = round(float(stats["avg_cvss"] or 0), 1)
        stats["recent_findings"] = list(recent)

        return Response(stats)


class FindingTimelineView(APIView):
    """
    GET /api/v1/findings/timeline/?group=day|month&days=90
    Returns findings count grouped by day or month over a time window.
    """

    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    def get(self, request):
        group = request.query_params.get("group", "day")
        # Limit lookback to max 365 days to prevent abuse
        try:
            days = min(int(request.query_params.get("days", 90)), 365)
        except (ValueError, TypeError):
            days = 90

        since = timezone.now() - timezone.timedelta(days=days)

        if group == "month":
            trunc_fn = TruncMonth("created_at")
        else:
            trunc_fn = TruncDate("created_at")

        qs = (
            Finding.objects.filter(created_at__gte=since)
            .annotate(period=trunc_fn)
            .values("period")
            .annotate(
                total=Count("id"),
                critical=Count("id", filter=Q(severity="critical")),
                high=Count("id", filter=Q(severity="high")),
                medium=Count("id", filter=Q(severity="medium")),
                low=Count("id", filter=Q(severity="low")),
                informational=Count("id", filter=Q(severity="informational")),
            )
            .order_by("period")
        )

        data = []
        for row in qs:
            data.append({
                "date": row["period"].isoformat() if row["period"] else None,
                "total": row["total"],
                "critical": row["critical"],
                "high": row["high"],
                "medium": row["medium"],
                "low": row["low"],
                "informational": row["informational"],
            })

        return Response({"group": group, "days": days, "data": data})


# ──────────────────────────────────────────────
# Report Generation — Typst PDF
# ──────────────────────────────────────────────

SEVERITY_ORDER = ["critical", "high", "medium", "low", "informational"]
TEMPLATES_DIR = os.path.join(settings.BASE_DIR, "report_templates")


def _md_to_typst(text: str) -> str:
    """Convert Markdown to Typst markup via Pandoc."""
    if not text:
        return ""
    # Shift markdown headings down one level (## → ###) so finding
    # subsections become level-3 headings under the level-2 finding title
    text = re.sub(
        r"^(#{2,6}) ",
        lambda m: "#" + m.group(1) + " ",
        text,
        flags=re.MULTILINE,
    )
    try:
        r = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "typst", "--wrap=none"],
            input=text,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode:
            print(f"[report-gen] pandoc error: {r.stderr}", file=sys.stderr)
            return text
        output = r.stdout
        # Reformat Pandoc image output so figures use image() directly
        # Pandoc produces: #figure([#image("path");], caption: [...])
        # We want:         #figure(image("path"), caption: [...])
        # Width is controlled globally in report.typ via a show rule.
        output = re.sub(
            r'#figure\(\[#image\("([^"]+)"\);\]',
            r'#figure(image("\1")',
            output,
        )
        return output
    except FileNotFoundError:
        # pandoc not installed — return raw text as fallback
        return text


def _build_report_content(finding) -> str:
    """Build combined markdown content from finding fields, then convert to Typst."""
    parts = []

    if finding.description:
        parts.append("## Description\n\n" + finding.description.strip())

    if finding.impact:
        parts.append("## Impact\n\n" + finding.impact.strip())

    if finding.recommendations:
        parts.append("## Recommendations\n\n" + finding.recommendations.strip())

    if finding.affected_assets:
        # One asset per line — render as a bullet list
        lines = [l.strip() for l in finding.affected_assets.strip().splitlines() if l.strip()]
        if lines:
            bullet_list = "\n".join(f"- {line}" for line in lines)
            parts.append("## Affected Assets\n\n" + bullet_list)

    if finding.references:
        # One reference per line — render as a bullet list
        lines = [l.strip() for l in finding.references.strip().splitlines() if l.strip()]
        if lines:
            bullet_list = "\n".join(f"- {line}" for line in lines)
            parts.append("## References\n\n" + bullet_list)

    content = "\n\n".join(parts)

    # Convert media URLs to local file paths so Typst can resolve images.
    # Handles both full URLs (http://host/media/...) and absolute paths (/media/...).
    media_root = str(settings.MEDIA_ROOT)
    media_prefix = media_root + '/' if not media_root.endswith('/') else media_root
    # Handle full URLs: http://host/media/...
    content = re.sub(
        r'https?://[^/\s]+/media/',
        media_prefix,
        content,
    )
    # Handle relative paths: /media/...
    content = re.sub(
        r'(?<![:/])/media/',
        media_prefix,
        content,
    )

    typst_content = _md_to_typst(content)

    return typst_content


def _sev_label(severity: str) -> str:
    """Normalize severity for display."""
    if severity == "informational":
        return "Info"
    return severity.capitalize()


class GenerateReportView(APIView):
    """
    POST /api/v1/reports/generate/
    Body: {
        "finding_ids": ["<uuid>", ...],
        "client_name": "optional override",
        "asset_name": "optional override",
        "date_from": "YYYY-MM-DD",
        "date_to": "YYYY-MM-DD"
    }
    Generates a PDF report via Typst and returns the download URL.
    """

    permission_classes = [IsAuthenticated, IsAnalystOrAbove]

    def post(self, request):
        serializer = GenerateReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        finding_ids = serializer.validated_data["finding_ids"]
        client_name = serializer.validated_data.get("client_name", "")
        asset_name = serializer.validated_data.get("asset_name", "")
        date_from = serializer.validated_data.get("date_from", "")
        date_to = serializer.validated_data.get("date_to", "")

        # Fetch findings and sort by severity (critical → informational)
        findings = list(
            Finding.objects.filter(id__in=finding_ids)
            .select_related("asset", "asset__client", "created_by", "assigned_to")
            .prefetch_related("evidences")
            .annotate(
                severity_order=Case(
                    When(severity="critical", then=0),
                    When(severity="high", then=1),
                    When(severity="medium", then=2),
                    When(severity="low", then=3),
                    When(severity="informational", then=4),
                    output_field=IntegerField(),
                )
            )
            .order_by("severity_order", "-cvss_score")
        )

        if not findings:
            return Response(
                {"detail": "No valid findings found for the given IDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Auto-detect client/asset from findings if not provided
        if not client_name:
            clients = set()
            for f in findings:
                if f.asset and f.asset.client:
                    clients.add(f.asset.client.name)
            client_name = ", ".join(sorted(clients)) if clients else "N/A"

        if not asset_name:
            assets = set()
            for f in findings:
                if f.asset:
                    assets.add(f.asset.name)
            asset_name = ", ".join(sorted(assets)) if assets else "N/A"

        today = date.today()
        if not date_from:
            date_from = str(today)
        if not date_to:
            date_to = str(today)

        # Count by severity
        counts = Counter(f.severity for f in findings)

        # Build JSON payload for Typst template
        data = {
            "asset": asset_name,
            "client": client_name,
            "from": str(date_from),
            "to": str(date_to),
            "date": str(today),
            "total": len(findings),
            "critical": counts.get("critical", 0),
            "high": counts.get("high", 0),
            "medium": counts.get("medium", 0),
            "low": counts.get("low", 0),
            "info": counts.get("informational", 0),
            "findings": [
                {
                    "num": str(i),
                    "id": str(f.id),
                    "title": f.title,
                    "severity": _sev_label(f.severity),
                    "cvss": str(f.cvss_score) if f.cvss_score is not None else "",
                    "cvss-vector": f.cvss_vector or "",
                    "status": f.get_status_display(),
                    "date": str(f.created_at.date()) if f.created_at else str(today),
                    "asset": asset_name,
                    "report-content": _build_report_content(f),
                }
                for i, f in enumerate(findings, 1)
            ],
        }

        # Write the JSON data to a temp file
        reports_dir = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid_mod.uuid4().hex[:8]
        data_filename = f"report_data_{timestamp}_{unique_id}.json"
        data_path = os.path.join(reports_dir, data_filename)

        with open(data_path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)

        # Compile Typst template to PDF
        pdf_filename = f"report_{timestamp}_{unique_id}.pdf"
        pdf_path = os.path.join(reports_dir, pdf_filename)
        template_path = os.path.join(TEMPLATES_DIR, "report.typ")

        cmd = [
            "typst", "compile",
            "--root", "/",
            "--font-path", "/usr/share/fonts",
            "--input", f"data-path={data_path}",
            "--input", f"tpl-dir={TEMPLATES_DIR}",
            str(template_path),
            str(pdf_path),
        ]

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except FileNotFoundError:
            # Clean up data file
            os.unlink(data_path)
            return Response(
                {"detail": "typst is not installed on the server. "
                           "Install typst to enable PDF report generation."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Clean up the data JSON file
        try:
            os.unlink(data_path)
        except OSError:
            pass

        if r.returncode:
            return Response(
                {"detail": f"Report generation failed: {r.stderr[:500]}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Create GeneratedReport record
        report_name = f"Report - {client_name} - {asset_name} - {timestamp}"
        report = GeneratedReport.objects.create(
            name=report_name,
            template=None,
            file=f"reports/{pdf_filename}",
            finding_count=len(findings),
            generated_by=request.user,
        )

        result = GeneratedReportSerializer(report).data
        return Response(result, status=status.HTTP_201_CREATED)


# ───────────────────────────────────────────────
# Generated Report list / detail
# ───────────────────────────────────────────────
class GeneratedReportListView(generics.ListAPIView):
    """GET /api/v1/reports/ — list previously generated reports."""

    queryset = GeneratedReport.objects.select_related("generated_by", "template")
    serializer_class = GeneratedReportSerializer
    permission_classes = [IsViewerOrAbove]


class GeneratedReportDetailView(generics.RetrieveDestroyAPIView):
    """
    GET    /api/v1/reports/<uuid>/ — retrieve report metadata
    DELETE /api/v1/reports/<uuid>/ — delete a generated report (admin only)
    """

    queryset = GeneratedReport.objects.select_related("generated_by", "template")
    serializer_class = GeneratedReportSerializer
    lookup_field = "pk"

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAdminRole()]
        return [IsViewerOrAbove()]
