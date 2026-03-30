"""
Custom security middleware for the RedTeam Findings platform.

- SecurityHeadersMiddleware: Adds CSP, hides server identity, strips tech info.
- AuditLoggingMiddleware: Logs authentication events and data-modifying requests.
"""

import json
import logging
import time

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

audit_logger = logging.getLogger("audit")
security_logger = logging.getLogger("django.security")


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Adds production security headers and hides server identity.
    """

    def process_response(self, request, response):
        # Content Security Policy
        csp_parts = []
        for directive, sources in [
            ("default-src", getattr(settings, "CSP_DEFAULT_SRC", ("'self'",))),
            ("script-src", getattr(settings, "CSP_SCRIPT_SRC", ("'self'",))),
            ("style-src", getattr(settings, "CSP_STYLE_SRC", ("'self'",))),
            ("img-src", getattr(settings, "CSP_IMG_SRC", ("'self'",))),
            ("font-src", getattr(settings, "CSP_FONT_SRC", ("'self'",))),
            ("connect-src", getattr(settings, "CSP_CONNECT_SRC", ("'self'",))),
        ]:
            csp_parts.append(f"{directive} {' '.join(sources)}")
        response["Content-Security-Policy"] = "; ".join(csp_parts)

        # Hide server identity
        response["Server"] = "RedTeam-Platform"

        # Additional security headers
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        return response


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Logs security-relevant events:
    - Failed authentication attempts (401 on /auth/login/)
    - User creation/modification (POST/PATCH/PUT/DELETE on /users/)
    - Finding changes (POST/PATCH/PUT/DELETE on /findings/)
    - Evidence uploads
    """

    # Paths and methods to audit
    AUDIT_PATHS = {
        "/api/v1/auth/login/": "AUTH_LOGIN",
        "/api/v1/auth/change-password/": "AUTH_PASSWORD_CHANGE",
    }
    AUDIT_PREFIXES = {
        "/api/v1/users/": "USER",
        "/api/v1/findings/": "FINDING",
    }
    AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def process_request(self, request):
        request._audit_start = time.time()

    def process_response(self, request, response):
        path = request.path
        method = request.method
        status = response.status_code

        # Determine event type
        event = None

        # Exact path match
        if path in self.AUDIT_PATHS:
            event = self.AUDIT_PATHS[path]
        # Prefix match for data-modifying operations
        elif method in self.AUDIT_METHODS:
            for prefix, prefix_event in self.AUDIT_PREFIXES.items():
                if path.startswith(prefix):
                    event = prefix_event
                    break

        if event is None:
            return response

        # Build log entry
        user = getattr(request, "user", None)
        user_id = getattr(user, "id", None) if user and user.is_authenticated else None
        username = getattr(user, "username", "anonymous") if user else "anonymous"
        duration = time.time() - getattr(request, "_audit_start", time.time())

        log_data = {
            "event": event,
            "method": method,
            "path": path,
            "status": status,
            "user_id": str(user_id) if user_id else None,
            "username": username,
            "ip": self._get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "duration_ms": round(duration * 1000, 2),
        }

        # Log at appropriate level
        if event == "AUTH_LOGIN" and status == 401:
            # Failed login — security event
            body = {}
            try:
                body = json.loads(request.body.decode())
            except Exception:
                pass
            log_data["attempted_username"] = body.get("username", "unknown")
            security_logger.warning(
                "Failed login attempt for user '%s' from %s",
                log_data["attempted_username"],
                log_data["ip"],
                extra={"audit": log_data},
            )
        elif event == "AUTH_LOGIN" and status == 200:
            audit_logger.info(
                "Successful login: %s from %s",
                username,
                log_data["ip"],
                extra={"audit": log_data},
            )
        elif method == "DELETE":
            audit_logger.warning(
                "DELETE %s by %s — status %s",
                path,
                username,
                status,
                extra={"audit": log_data},
            )
        elif method in self.AUDIT_METHODS:
            audit_logger.info(
                "%s %s by %s — status %s",
                method,
                path,
                username,
                status,
                extra={"audit": log_data},
            )

        return response

    @staticmethod
    def _get_client_ip(request):
        """Extract real client IP, accounting for proxies."""
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
