from django.contrib import admin

from .models import Asset, Client, Evidence, Finding, FindingHistory, GeneratedReport


class AssetInline(admin.TabularInline):
    model = Asset
    extra = 0
    fields = ["name", "asset_type", "ip_address", "hostname", "created_by"]
    readonly_fields = ["name", "asset_type", "ip_address", "hostname", "created_by"]
    show_change_link = True


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "created_at"]
    search_fields = ["name", "description"]
    inlines = [AssetInline]


class FindingInline(admin.TabularInline):
    model = Finding
    extra = 0
    fields = ["title", "severity", "status", "cvss_score", "created_by"]
    readonly_fields = ["title", "severity", "status", "cvss_score", "created_by"]
    show_change_link = True


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ["name", "asset_type", "ip_address", "hostname", "created_at"]
    list_filter = ["asset_type"]
    search_fields = ["name", "ip_address", "hostname", "url", "description"]
    inlines = [FindingInline]


class EvidenceInline(admin.TabularInline):
    model = Evidence
    extra = 0
    readonly_fields = ["uploaded_by", "uploaded_at"]


class FindingHistoryInline(admin.TabularInline):
    model = FindingHistory
    extra = 0
    fields = ["action", "changes", "changed_by", "timestamp"]
    readonly_fields = ["action", "changes", "changed_by", "timestamp"]
    ordering = ["-timestamp"]


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ["title", "severity", "status", "cvss_score", "created_by", "created_at"]
    list_filter = ["severity", "status"]
    search_fields = ["title", "description", "affected_assets"]
    inlines = [EvidenceInline, FindingHistoryInline]


@admin.register(FindingHistory)
class FindingHistoryAdmin(admin.ModelAdmin):
    list_display = ["finding", "action", "changed_by", "timestamp"]
    list_filter = ["action", "timestamp"]
    search_fields = ["finding__title"]
    readonly_fields = ["finding", "action", "changes", "changed_by", "timestamp"]


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ["caption", "finding", "uploaded_by", "uploaded_at"]
    list_filter = ["uploaded_at"]
