# Generated migration for ReportTemplate and GeneratedReport models

import uuid
import findings.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("findings", "0004_alter_evidence_file"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportTemplate",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Display name for this template.",
                        max_length=300,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="What this template is for.",
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        help_text="DOCX template file.",
                        upload_to=findings.models.template_upload_path,
                        validators=[findings.models.validate_docx_file],
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="templates_uploaded",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="GeneratedReport",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=300)),
                (
                    "file",
                    models.FileField(
                        upload_to=findings.models.report_output_path,
                    ),
                ),
                (
                    "finding_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "template",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reports",
                        to="findings.reporttemplate",
                    ),
                ),
                (
                    "generated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reports_generated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
