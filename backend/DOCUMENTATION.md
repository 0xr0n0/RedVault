# Backend Documentation — RedVault

This document explains how the RedVault backend works. It is intended for developers who want to understand, modify, or extend the backend code.

---

## Overview

The backend is a REST API built with **Django 5.1** and **Django REST Framework (DRF)**. It uses **PostgreSQL 16** as the database and runs inside a Docker container with **Gunicorn** as the production web server.

The backend handles:

- User authentication (JWT tokens) and role-based access control
- CRUD operations for clients, assets, findings, and evidence
- PDF report generation using Typst (a typesetting engine) and Pandoc (for Markdown conversion)
- Dashboard statistics and finding timeline data
- Audit logging of all security-relevant actions
- File upload handling and validated media serving

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Programming language |
| Django 5.1 | Web framework |
| Django REST Framework | API framework (serializers, views, permissions) |
| SimpleJWT | JWT token authentication |
| PostgreSQL 16 | Database |
| Gunicorn | Production WSGI server |
| Pandoc | Converts Markdown to Typst markup |
| Typst | Compiles report templates into PDF files |
| Pillow | Image processing for uploaded evidence |
| django-cors-headers | Cross-origin request handling |
| django-filter | API query filtering |
| python-decouple | Environment variable management |

---

## File Structure

```
backend/
├── Dockerfile                  # Container build (Python 3.12 + Pandoc + Typst)
├── entrypoint.sh               # Startup: migrations → seed admin → start server
├── gunicorn.conf.py            # Gunicorn config (hides server identity)
├── manage.py                   # Django CLI
├── requirements.txt            # Python dependencies
├── config/                     # Project-level configuration
│   ├── settings.py             # All Django settings
│   ├── urls.py                 # Root URL routing + authenticated media serving
│   ├── middleware.py           # Security headers + audit logging
│   ├── logging_formatter.py   # JSON log formatter (for SIEM integration)
│   ├── wsgi.py / asgi.py      # WSGI/ASGI entry points
│   └── __init__.py
├── findings/                   # Main app: clients, assets, findings, evidence, reports
│   ├── models.py               # Database models
│   ├── serializers.py          # API input/output serializers
│   ├── views.py                # API views and report generation logic
│   ├── urls.py                 # Finding + evidence + history routes
│   ├── urls_clients.py         # Client routes
│   ├── urls_assets.py          # Asset routes
│   ├── urls_reports.py         # Report generation route
│   └── migrations/             # Database schema migrations
├── users/                      # User management and authentication
│   ├── models.py               # Custom User model with roles
│   ├── permissions.py          # RBAC permission classes
│   ├── serializers.py          # User serializers
│   ├── views.py                # Auth views (login, refresh, profile, password)
│   ├── urls.py                 # Auth routes
│   ├── urls_users.py           # User CRUD routes
│   └── management/commands/
│       └── seed_admin.py       # Creates initial admin user on first startup
├── report_templates/           # PDF report template + cover images
│   ├── report.typ              # Typst template (editable)
│   ├── banner.png              # Cover page decorative image (replaceable)
│   └── logo.png                # Company logo (replaceable)
├── media/                      # Uploaded files (evidence, generated reports) — bind-mounted to data/media/
└── logs/                       # Audit log output — bind-mounted to data/logs/
```

---

## Data Models

The backend has seven database models. Here is what each one stores and how they relate to each other.

### Relationships

```
Client (company being tested)
  └── Asset (server, app, API, etc.)
        └── Finding (vulnerability found)
              ├── Evidence (screenshots, proof files)
              └── FindingHistory (audit log of changes)

ReportTemplate ──→ GeneratedReport (PDF output)
```

### Client

Represents a company or organisation that owns the assets being tested.

| Field | Description |
|---|---|
| `id` | Auto-generated UUID |
| `name` | Company name (up to 300 characters) |
| `description` | Optional notes about the client |
| `created_by` | The user who created this client |
| `created_at` / `updated_at` | Automatic timestamps |

### Asset

A system, application, or resource belonging to a client that is being tested.

| Field | Description |
|---|---|
| `id` | Auto-generated UUID |
| `name` | Hostname, URL, IP, or descriptive name |
| `asset_type` | One of: `host`, `web_app`, `api`, `network`, `cloud`, `mobile`, `database`, `other` |
| `ip_address` | IP address (optional) |
| `hostname` | Hostname (optional) |
| `url` | URL (optional) |
| `os` | Operating system or platform (optional) |
| `description` | Additional notes (optional) |
| `client` | Which client owns this asset (optional) |
| `created_by` | The user who created this asset |

### Finding

A security vulnerability discovered during testing.

| Field | Description |
|---|---|
| `id` | Auto-generated UUID |
| `title` | Vulnerability name (e.g. "SQL Injection in login form") |
| `description` | Detailed write-up in Markdown format |
| `impact` | Business impact description (optional, Markdown) |
| `recommendations` | How to fix it (Markdown) |
| `severity` | `critical`, `high`, `medium`, `low`, or `informational` |
| `cvss_score` | Numeric CVSS score, 0.0–10.0 (optional) |
| `cvss_vector` | CVSS 3.1 vector string (optional) |
| `asset` | Which asset this finding applies to (optional) |
| `affected_assets` | Free-text list of affected hosts/IPs/URLs |
| `references` | CVE IDs, external links, articles |
| `status` | `open`, `in_progress`, `remediated`, `closed`, or `accepted` |
| `created_by` | Who created this finding |
| `assigned_to` | Who is assigned to work on it (optional) |

### FindingHistory

Automatic audit trail. Every time a finding is created or modified, a history entry is recorded.

| Field | Description |
|---|---|
| `finding` | Which finding this entry belongs to |
| `action` | `created`, `updated`, or `deleted` |
| `changes` | JSON object listing each changed field with its old and new value |
| `changed_by` | Who made the change |
| `timestamp` | When the change happened |

**Tracked fields:** title, description, recommendations, severity, cvss_score, cvss_vector, asset, affected_assets, references, status, assigned_to.

### Evidence

File attachments linked to a finding (screenshots, network captures, proof-of-concept files).

| Field | Description |
|---|---|
| `finding` | Which finding this evidence belongs to |
| `file` | The uploaded file (stored in `media/evidence/<finding_id>/`) |
| `caption` | Optional description of the evidence |
| `uploaded_by` | Who uploaded the file |

**Upload restrictions:**
- Maximum file size: 20 MB
- Allowed extensions: images (png, jpg, gif, bmp, svg, webp), documents (pdf, doc, docx, xls, xlsx, ppt, pptx, odt, ods, odp), text (txt, csv, json, xml, yaml, yml, md, log), archives (zip, tar, gz, 7z), network captures (pcap, pcapng, cap), and video (mp4, webm, avi, mkv)
- Double-extension files are blocked (e.g. `exploit.php.png`)

### ReportTemplate

Stored in the database for internal tracking. Templates are managed on disk in `report_templates/` — there is no API for uploading or deleting templates.

| Field | Description |
|---|---|
| `name` | Display name |
| `file` | The DOCX template file (max 10 MB) |
| `uploaded_by` | Who uploaded it |

### GeneratedReport

A PDF report that was generated from selected findings.

| Field | Description |
|---|---|
| `name` | Report name |
| `file` | The generated PDF file |
| `finding_count` | Number of findings included |
| `generated_by` | Who generated it |

---

## API Endpoints

All endpoints are prefixed with `/api/v1/`. Authentication is required for all endpoints except login and token refresh.

### Authentication (`/api/v1/auth/`)

| Method | Path | What it does | Who can use it |
|---|---|---|---|
| POST | `/login/` | Log in with username/password, returns JWT tokens | Anyone (rate-limited: 5 attempts per minute) |
| POST | `/refresh/` | Get a new access token using a refresh token | Anyone |
| GET | `/profile/` | Get current user's profile | Logged-in user |
| POST | `/change-password/` | Change your own password (requires old password) | Logged-in user |

### Users (`/api/v1/users/`) — Admin only

| Method | Path | What it does |
|---|---|---|
| GET | `/` | List all users |
| POST | `/` | Create a new user (set username, password, role) |
| GET | `/<id>/` | Get user details |
| PATCH | `/<id>/` | Update user (role, active status) |
| DELETE | `/<id>/` | Deactivate user (soft delete — preserves audit trail) |

### Clients (`/api/v1/clients/`)

| Method | Path | What it does | Who can use it |
|---|---|---|---|
| GET | `/` | List all clients | Viewer, Analyst, Admin |
| POST | `/` | Create a new client | Admin only |
| GET | `/<uuid>/` | Get client details | Viewer+ |
| PUT/PATCH | `/<uuid>/` | Update client | Admin only |
| DELETE | `/<uuid>/` | Delete client | Admin only |

### Assets (`/api/v1/assets/`)

| Method | Path | What it does | Who can use it |
|---|---|---|---|
| GET | `/` | List assets (filterable by type, client) | Viewer+ |
| POST | `/` | Create a new asset | Analyst+ |
| GET | `/<uuid>/` | Get asset details | Viewer+ |
| PUT/PATCH | `/<uuid>/` | Update asset | Analyst+ |
| DELETE | `/<uuid>/` | Delete asset | Admin only |

### Findings (`/api/v1/findings/`)

| Method | Path | What it does | Who can use it |
|---|---|---|---|
| GET | `/` | List findings (filterable by severity, status, asset) | Viewer+ |
| POST | `/` | Create a finding | Analyst+ |
| GET | `/<uuid>/` | Get finding details (includes evidences) | Viewer+ |
| PUT/PATCH | `/<uuid>/` | Update finding | Analyst+ |
| DELETE | `/<uuid>/` | Delete finding | Admin only |
| GET | `/stats/` | Dashboard statistics (counts, averages) | Viewer+ |
| GET | `/timeline/` | Monthly finding counts for chart | Viewer+ |

### Evidence (`/api/v1/findings/<uuid>/evidence/`)

| Method | Path | What it does | Who can use it |
|---|---|---|---|
| GET | `/` | List evidence for a finding | Viewer+ |
| POST | `/` | Upload evidence (multipart form) | Analyst+ |
| GET | `/<uuid>/` | Get evidence detail | Viewer+ |
| DELETE | `/<uuid>/` | Delete evidence | Analyst+ |

### Finding History (`/api/v1/findings/<uuid>/history/`)

| Method | Path | What it does | Who can use it |
|---|---|---|---|
| GET | `/` | View the complete audit trail of a finding | Viewer+ |

### Reports (`/api/v1/reports/`)

| Method | Path | What it does | Who can use it |
|---|---|---|---|
| GET | `/` | List generated reports | Viewer+ |
| GET | `/<uuid>/` | Get report details | Viewer+ |
| DELETE | `/<uuid>/` | Delete a generated report | Admin only |
| POST | `/generate/` | Generate a PDF report from selected findings | Analyst+ |

Report templates are managed on disk in `report_templates/` rather than through the API. See the "Customising the Report Template" section in the main README.md.

---

## Report Generation — How It Works

When a user clicks "Generate Report" in the web interface, the following happens:

1. The frontend sends a POST to `/api/v1/reports/generate/` with a list of finding IDs and optional metadata (client name, asset name, date range).

2. The backend fetches all requested findings from the database, sorted by severity (critical first).

3. For each finding, a combined Markdown document is built from its description, impact, recommendations, affected assets, and references sections.

4. Any image URLs in the Markdown (e.g. `http://localhost:8000/media/evidence/...`) are automatically converted to local file paths so Typst can resolve them.

5. The Markdown is converted to Typst markup using **Pandoc** (`pandoc -f markdown -t typst`).

6. All finding data is assembled into a JSON file and passed as input to the **Typst** template (`report_templates/report.typ`).

7. Typst compiles the template + data into a PDF file.

8. The PDF is saved and a download URL is returned to the frontend.

### Customising Reports

See the "Customising the Report Template" section in the main README.md for instructions on changing logos, colours, fonts, and report structure.

---

## User Roles (RBAC)

Three roles control access across the entire application:

| Role | What they can do |
|---|---|
| **Admin** | Everything. Create users, manage clients, CRUD all entities, delete anything. |
| **Analyst** | Create and edit findings, assets, and evidence. Generate reports. Cannot manage users or delete clients. |
| **Viewer** | Read-only access to everything. Cannot create, edit, or delete anything. |

These roles are enforced by three permission classes in `users/permissions.py`:

- `IsAdminRole` — Only allows admin users
- `IsAnalystOrAbove` — Allows admin and analyst users
- `IsViewerOrAbove` — Allows any authenticated user (admin, analyst, or viewer)

Each API view explicitly declares which permission class it uses.

---

## Security Features

| Feature | How it works |
|---|---|
| JWT Authentication | Access tokens expire after 60 minutes, refresh tokens after 24 hours. Token rotation and blacklisting are enabled. |
| Login Rate Limiting | Maximum 5 login attempts per minute per IP address. Returns 429 after that. |
| Password Hashing | Passwords are hashed using Django's PBKDF2 algorithm. Never stored in plain text. |
| Role-Based Access Control | Every endpoint checks the user's role before allowing access. |
| Security Headers | CSP, X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Referrer-Policy, Permissions-Policy. |
| Server Identity Hidden | The HTTP `Server` header shows "RedTeam-Platform" instead of the real server software. |
| Authenticated Media Access | Evidence files and reports are only accessible with a valid JWT token. Path traversal is blocked. |
| File Upload Validation | Whitelist of allowed extensions, 20 MB size limit, double-extension blocking. |
| Soft User Deletion | Users are deactivated instead of deleted, preserving the audit trail. |
| Audit Logging | All authentication events, user management, and finding/evidence changes are logged in JSON format for SIEM ingestion. |
| CORS | Only explicitly configured origins can make cross-origin requests. No wildcard. |
| Admin Panel Disabled | Django's admin panel is off by default. Only enabled when `ENABLE_ADMIN=True`. |
| Typst Injection Prevention | Finding content passes through Pandoc which escapes special characters, preventing code execution in the report template. |

---

## Environment Variables

These are configured in the `.env` file at the project root and passed to the container via `docker-compose.yml`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | Cryptographic key for Django. Must be unique per installation. |
| `DB_PASSWORD` | Yes | — | PostgreSQL password. |
| `DEBUG` | No | `False` | Debug mode. Set to `True` only during development. |
| `DB_USER` | No | `postgres` | PostgreSQL username. |
| `DB_NAME` | No | `redteam_findings` | PostgreSQL database name. |
| `DB_HOST` | No | `db` | PostgreSQL host (use `db` for Docker). |
| `DB_PORT` | No | `5432` | PostgreSQL port. |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated hostnames the backend accepts. |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5173` | Comma-separated frontend URLs allowed for CORS. |
| `ENABLE_ADMIN` | No | `False` | Set to `True` to enable Django's admin panel at `/admin/`. |

---

## Startup Process

When the backend container starts, `entrypoint.sh` runs these steps in order:

1. Creates the log directory (`/app/logs`)
2. Runs database migrations (`python manage.py migrate`)
3. Runs the admin seeder (`python manage.py seed_admin`) — creates an admin user with a random password on first run, prints it to the console
4. Starts Gunicorn with 4 workers on port 8000

---

## Extending the Backend

### Adding a new field to Finding

1. Add the field to the `Finding` model in `findings/models.py`
2. Add the field to `TRACKED_FIELDS` if you want it in the audit trail
3. Add the field to the serializer in `findings/serializers.py`
4. Run `python manage.py makemigrations` and `python manage.py migrate`
5. If it should appear in reports, add it to `_build_report_content()` in `findings/views.py`

### Adding a new API endpoint

1. Create the view in the appropriate `views.py`
2. Add the URL pattern to the appropriate `urls*.py` file
3. Set the correct permission class (`IsAdminRole`, `IsAnalystOrAbove`, or `IsViewerOrAbove`)

### Modifying the report template

See `report_templates/report.typ`. The template uses Typst syntax. Finding data is passed as JSON. Refer to the [Typst documentation](https://typst.app/docs/) for the template language.
