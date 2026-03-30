# Generated manually — adds Asset model and Finding.asset FK

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("findings", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create the Asset table
        migrations.CreateModel(
            name="Asset",
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
                        help_text="Hostname, URL, IP address, or descriptive name.",
                        max_length=300,
                    ),
                ),
                (
                    "asset_type",
                    models.CharField(
                        choices=[
                            ("host", "Host"),
                            ("web_app", "Web Application"),
                            ("api", "API"),
                            ("network", "Network"),
                            ("cloud", "Cloud Resource"),
                            ("mobile", "Mobile App"),
                            ("database", "Database"),
                            ("other", "Other"),
                        ],
                        default="host",
                        max_length=15,
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(blank=True, null=True),
                ),
                (
                    "hostname",
                    models.CharField(blank=True, default="", max_length=300),
                ),
                (
                    "url",
                    models.URLField(blank=True, default="", max_length=500),
                ),
                (
                    "os",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Operating system or platform.",
                        max_length=200,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Additional notes about this asset.",
                    ),
                ),
                (
                    "is_in_scope",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the asset is in-scope.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assets_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        # 2. Add the asset FK to Finding
        migrations.AddField(
            model_name="finding",
            name="asset",
            field=models.ForeignKey(
                blank=True,
                help_text="The asset this finding affects.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="findings",
                to="findings.asset",
            ),
        ),
    ]
