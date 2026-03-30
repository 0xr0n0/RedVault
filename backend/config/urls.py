"""
Root URL configuration.
"""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path


def serve_media(request, path_str):
    """Serve media files without authentication.

    Files are stored under UUID-based paths (122-bit entropy),
    making brute-force enumeration infeasible.  Path traversal
    is still blocked.
    """
    file_path = Path(settings.MEDIA_ROOT) / path_str
    # Prevent path traversal
    try:
        file_path = file_path.resolve()
        media_root = Path(settings.MEDIA_ROOT).resolve()
        if not str(file_path).startswith(str(media_root)):
            raise Http404
    except (ValueError, OSError):
        raise Http404
    if not file_path.is_file():
        raise Http404
    content_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(open(file_path, "rb"), content_type=content_type or "application/octet-stream")


# Restrict admin panel — only available when ENABLE_ADMIN=True
ADMIN_ENABLED = getattr(settings, "ENABLE_ADMIN", settings.DEBUG)

urlpatterns = [
    path("api/v1/auth/", include("users.urls")),
    path("api/v1/users/", include("users.urls_users")),
    path("api/v1/clients/", include("findings.urls_clients")),
    path("api/v1/findings/", include("findings.urls")),
    path("api/v1/assets/", include("findings.urls_assets")),
    path("api/v1/reports/", include("findings.urls_reports")),
    path("media/<path:path_str>", serve_media, name="serve-media"),
]

if ADMIN_ENABLED:
    urlpatterns.insert(0, path("admin/", admin.site.urls))
