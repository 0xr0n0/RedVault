"""
Finding model — the core entity for pentest report findings.

Each finding has markdown-based description/recommendations, CVSS scoring,
affected assets, status tracking, references, and evidence attachments.
"""

import os
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# ── File upload validators ──
ALLOWED_EVIDENCE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp',  # images
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',          # documents
    '.txt', '.csv', '.json', '.xml', '.html',           # text
    '.zip', '.7z', '.tar', '.gz',                       # archives
    '.pcap', '.pcapng', '.cap',                         # network captures
    '.mp4', '.webm', '.mov',                            # video
}

MAX_EVIDENCE_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def validate_evidence_file(file):
    """Validate evidence file extension and size."""
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EVIDENCE_EXTENSIONS:
        raise ValidationError(
            f"File type '{ext}' is not allowed. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EVIDENCE_EXTENSIONS))}"
        )
    # Block dangerous double extensions (e.g. shell.php.png)
    DANGEROUS_EXTENSIONS = {'.php', '.jsp', '.aspx', '.exe', '.sh', '.bat', '.cmd', '.py', '.rb', '.pl'}
    name_without_final_ext = os.path.splitext(file.name)[0]
    inner_ext = os.path.splitext(name_without_final_ext)[1].lower()
    if inner_ext in DANGEROUS_EXTENSIONS:
        raise ValidationError(
            f"File contains a dangerous inner extension '{inner_ext}'. "
            f"Double extensions like '{inner_ext}{ext}' are not allowed."
        )
    if file.size > MAX_EVIDENCE_FILE_SIZE:
        raise ValidationError(
            f"File size {file.size / (1024*1024):.1f}MB exceeds the "
            f"{MAX_EVIDENCE_FILE_SIZE / (1024*1024):.0f}MB limit."
        )


class Client(models.Model):
    """A client organization that owns one or more assets."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=300,
        help_text="Client / organization name.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Additional notes about this client.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="clients_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Asset(models.Model):
    """An asset (host, application, network device, etc.) targeted during a pentest."""

    class AssetType(models.TextChoices):
        HOST = "host", "Host"
        WEB_APP = "web_app", "Web Application"
        API = "api", "API"
        NETWORK = "network", "Network"
        CLOUD = "cloud", "Cloud Resource"
        MOBILE = "mobile", "Mobile App"
        DATABASE = "database", "Database"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=300,
        help_text="Hostname, URL, IP address, or descriptive name.",
    )
    asset_type = models.CharField(
        max_length=15,
        choices=AssetType.choices,
        default=AssetType.HOST,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    hostname = models.CharField(max_length=300, blank=True, default="")
    url = models.URLField(max_length=500, blank=True, default="")
    os = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Operating system or platform.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Additional notes about this asset.",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
        help_text="The client this asset belongs to.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assets_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"[{self.get_asset_type_display()}] {self.name}"


class Finding(models.Model):
    """A single pentest finding."""

    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        INFORMATIONAL = "informational", "Informational"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        REMEDIATED = "remediated", "Remediated"
        CLOSED = "closed", "Closed"
        ACCEPTED = "accepted", "Risk Accepted"

    # Identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)

    # Content (markdown)
    description = models.TextField(
        help_text="Detailed description of the finding (Markdown)."
    )
    impact = models.TextField(
        blank=True,
        default="",
        help_text="Impact analysis of the finding (Markdown).",
    )
    recommendations = models.TextField(
        blank=True,
        default="",
        help_text="Recommended remediation steps (Markdown).",
    )

    # Scoring
    severity = models.CharField(
        max_length=15,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    cvss_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.0')), MaxValueValidator(Decimal('10.0'))],
        help_text="CVSS 3.1 base score (0.0 – 10.0).",
    )
    cvss_vector = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="CVSS 3.1 vector string.",
    )

    # Asset link
    asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="findings",
        help_text="The asset this finding affects.",
    )

    # Affected assets (legacy free-text field)
    affected_assets = models.TextField(
        blank=True,
        default="",
        help_text="Affected hosts, IPs, URLs — one per line.",
    )

    # References
    references = models.TextField(
        blank=True,
        default="",
        help_text="External references, CVE IDs — one per line.",
    )

    # Status tracking
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.OPEN,
    )

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="findings_created",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="findings_assigned",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"


class FindingHistory(models.Model):
    """Audit log entry recording a change to a Finding."""

    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finding = models.ForeignKey(
        Finding,
        on_delete=models.CASCADE,
        related_name="history",
    )
    action = models.CharField(
        max_length=10,
        choices=Action.choices,
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dict of changed fields: {"field": {"old": ..., "new": ...}}',
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="finding_changes",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "finding histories"

    def __str__(self):
        return f"{self.get_action_display()} by {self.changed_by} at {self.timestamp}"

    # ── Fields tracked for change detection ──
    TRACKED_FIELDS = [
        "title",
        "description",
        "impact",
        "recommendations",
        "severity",
        "cvss_score",
        "cvss_vector",
        "asset",
        "affected_assets",
        "references",
        "status",
        "assigned_to",
    ]

    @classmethod
    def log_create(cls, finding, user):
        """Record a 'created' event with initial field values."""
        initial = {}
        for field in cls.TRACKED_FIELDS:
            val = getattr(finding, field)
            # Convert FK objects to their PK string
            if hasattr(val, "pk"):
                val = str(val.pk) if val else None
            elif isinstance(val, Decimal):
                val = str(val)
            initial[field] = {"old": None, "new": val}
        return cls.objects.create(
            finding=finding,
            action=cls.Action.CREATED,
            changes=initial,
            changed_by=user,
        )

    @classmethod
    def log_update(cls, finding, old_values, user):
        """
        Compare old_values dict against current finding fields.
        Only record fields that actually changed.
        """
        changes = {}
        for field in cls.TRACKED_FIELDS:
            new_val = getattr(finding, field)
            old_val = old_values.get(field)
            # Normalise FK to pk
            if hasattr(new_val, "pk"):
                new_val = str(new_val.pk) if new_val else None
            if hasattr(old_val, "pk"):
                old_val = str(old_val.pk) if old_val else None
            # Normalise Decimal
            if isinstance(new_val, Decimal):
                new_val = str(new_val)
            if isinstance(old_val, Decimal):
                old_val = str(old_val)
            # Compare stringified to avoid type mismatches
            if str(new_val) != str(old_val):
                changes[field] = {"old": old_val, "new": new_val}
        if changes:
            return cls.objects.create(
                finding=finding,
                action=cls.Action.UPDATED,
                changes=changes,
                changed_by=user,
            )
        return None


def evidence_upload_path(instance, filename):
    """Upload evidence to: media/evidence/<finding_id>/<uuid>.<ext>"""
    ext = os.path.splitext(filename)[1].lower()
    return f"evidence/{instance.finding.id}/{uuid.uuid4()}{ext}"


class Evidence(models.Model):
    """Attachments (screenshots, PoC files) linked to a finding."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finding = models.ForeignKey(
        Finding,
        on_delete=models.CASCADE,
        related_name="evidences",
    )
    file = models.FileField(
        upload_to=evidence_upload_path,
        max_length=500,
        validators=[validate_evidence_file],
    )
    caption = models.CharField(max_length=300, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"Evidence: {self.caption or self.file.name}"


# ── Report Templates ──
def template_upload_path(instance, filename):
    """Upload templates to: media/templates/<uuid>_<filename>"""
    return f"templates/{uuid.uuid4().hex}_{filename}"


def validate_docx_file(file):
    """Validate that the uploaded file is a DOCX."""
    ext = os.path.splitext(file.name)[1].lower()
    if ext != ".docx":
        raise ValidationError("Only .docx files are allowed for templates.")
    if file.size > 10 * 1024 * 1024:  # 10 MB
        raise ValidationError("Template file must be under 10 MB.")


class ReportTemplate(models.Model):
    """A DOCX template that can be used to generate reports."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300, help_text="Display name for this template.")
    description = models.TextField(
        blank=True,
        default="",
        help_text="What this template is for.",
    )
    file = models.FileField(
        upload_to=template_upload_path,
        validators=[validate_docx_file],
        help_text="DOCX template file.",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="templates_uploaded",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


def report_output_path(instance, filename):
    """Upload generated reports to: media/reports/<filename>"""
    return f"reports/{filename}"


class GeneratedReport(models.Model):
    """A generated DOCX report — keeps track of what was generated."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reports",
    )
    file = models.FileField(upload_to=report_output_path)
    finding_count = models.PositiveIntegerField(default=0)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reports_generated",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
