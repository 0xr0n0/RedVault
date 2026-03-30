"""
Serializers for Finding, Evidence, ReportTemplate, and GeneratedReport models.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Asset,
    Client,
    Evidence,
    Finding,
    FindingHistory,
    GeneratedReport,
    ReportTemplate,
    validate_evidence_file,
)

User = get_user_model()


# ── Client Serializers ──
class ClientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for client list views."""

    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    asset_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "description",
            "asset_count",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]


class ClientDetailSerializer(serializers.ModelSerializer):
    """Full serializer for client detail/create/update."""

    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    asset_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "description",
            "asset_count",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class ClientMinimalSerializer(serializers.ModelSerializer):
    """Tiny serializer for embedding client info inside assets."""

    class Meta:
        model = Client
        fields = ["id", "name"]


# ── Asset Serializers ──
class AssetListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for asset list views."""

    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    finding_count = serializers.IntegerField(read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True, default=None)

    class Meta:
        model = Asset
        fields = [
            "id",
            "name",
            "asset_type",
            "ip_address",
            "hostname",
            "url",
            "os",
            "client",
            "client_name",
            "finding_count",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]


class AssetDetailSerializer(serializers.ModelSerializer):
    """Full serializer for asset detail/create/update."""

    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    finding_count = serializers.IntegerField(read_only=True, default=0)
    client_name = serializers.CharField(source="client.name", read_only=True, default=None)

    class Meta:
        model = Asset
        fields = [
            "id",
            "name",
            "asset_type",
            "ip_address",
            "hostname",
            "url",
            "os",
            "description",
            "client",
            "client_name",
            "finding_count",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class AssetMinimalSerializer(serializers.ModelSerializer):
    """Tiny serializer for embedding asset info inside findings."""

    class Meta:
        model = Asset
        fields = ["id", "name", "asset_type", "ip_address", "hostname"]


# ── Evidence Serializer ──
class RelativeFileField(serializers.FileField):
    """Return the file path relative to MEDIA_URL instead of an absolute URL."""

    def to_representation(self, value):
        if not value:
            return None
        return value.url  # e.g. /media/evidence/<uuid>/<file>


class EvidenceSerializer(serializers.ModelSerializer):
    """Nested serializer for evidence items."""

    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True
    )
    file = RelativeFileField(validators=[validate_evidence_file])

    class Meta:
        model = Evidence
        fields = [
            "id",
            "file",
            "caption",
            "uploaded_by",
            "uploaded_by_username",
            "uploaded_at",
        ]
        read_only_fields = ["id", "uploaded_by", "uploaded_by_username", "uploaded_at"]


class FindingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    assigned_to_username = serializers.CharField(
        source="assigned_to.username", read_only=True, default=None
    )
    evidence_count = serializers.IntegerField(read_only=True)
    asset_name = serializers.CharField(source="asset.name", read_only=True, default=None)

    class Meta:
        model = Finding
        fields = [
            "id",
            "title",
            "severity",
            "cvss_score",
            "status",
            "asset",
            "asset_name",
            "affected_assets",
            "created_by",
            "created_by_username",
            "assigned_to",
            "assigned_to_username",
            "evidence_count",
            "created_at",
            "updated_at",
        ]


class FindingDetailSerializer(serializers.ModelSerializer):
    """Full serializer with all fields + nested evidence."""

    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    assigned_to_username = serializers.CharField(
        source="assigned_to.username", read_only=True, default=None
    )
    evidences = EvidenceSerializer(many=True, read_only=True)
    asset_detail = AssetMinimalSerializer(source="asset", read_only=True)

    class Meta:
        model = Finding
        fields = [
            "id",
            "title",
            "description",
            "impact",
            "recommendations",
            "severity",
            "cvss_score",
            "cvss_vector",
            "asset",
            "asset_detail",
            "affected_assets",
            "references",
            "status",
            "created_by",
            "created_by_username",
            "assigned_to",
            "assigned_to_username",
            "evidences",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        instance = super().create(validated_data)
        FindingHistory.log_create(instance, self.context["request"].user)
        return instance

    def update(self, instance, validated_data):
        # Snapshot old values before the update
        old_values = {}
        for field in FindingHistory.TRACKED_FIELDS:
            val = getattr(instance, field)
            old_values[field] = val
        instance = super().update(instance, validated_data)
        FindingHistory.log_update(instance, old_values, self.context["request"].user)
        return instance


# ── Finding History Serializer ──
class FindingHistorySerializer(serializers.ModelSerializer):
    """Read-only serializer for the finding audit log."""

    changed_by_username = serializers.CharField(
        source="changed_by.username", read_only=True, default=None
    )

    class Meta:
        model = FindingHistory
        fields = [
            "id",
            "finding",
            "action",
            "changes",
            "changed_by",
            "changed_by_username",
            "timestamp",
        ]


# ── Report Template Serializers ──
class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ReportTemplate CRUD."""

    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True, default=None
    )
    file = RelativeFileField()

    class Meta:
        model = ReportTemplate
        fields = [
            "id",
            "name",
            "description",
            "file",
            "uploaded_by",
            "uploaded_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "uploaded_by", "created_at", "updated_at"]


class GeneratedReportSerializer(serializers.ModelSerializer):
    """Serializer for generated reports (read-only list)."""

    generated_by_username = serializers.CharField(
        source="generated_by.username", read_only=True, default=None
    )
    template_name = serializers.CharField(
        source="template.name", read_only=True, default=None
    )
    file = RelativeFileField(read_only=True)

    class Meta:
        model = GeneratedReport
        fields = [
            "id",
            "name",
            "template",
            "template_name",
            "file",
            "finding_count",
            "generated_by",
            "generated_by_username",
            "created_at",
        ]


class GenerateReportRequestSerializer(serializers.Serializer):
    """Input serializer for the PDF report-generation endpoint."""

    finding_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1
    )
    client_name = serializers.CharField(required=False, default="", allow_blank=True)
    asset_name = serializers.CharField(required=False, default="", allow_blank=True)
    date_from = serializers.DateField(required=False, default=None)
    date_to = serializers.DateField(required=False, default=None)
