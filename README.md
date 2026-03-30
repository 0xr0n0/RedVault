# RedVault — Penetration Testing Findings Manager

RedVault is a web application for managing penetration testing engagements. It lets security teams organise clients, track assets, document vulnerabilities with evidence screenshots, and generate professional PDF reports — all from a single platform.

---

## Disclaimer

I'm not a programmer, our red team had use cases and we needed a custom platform to submit findings and maintain their state, so I develop one using AI.
This platform should not be exposed since it contains sensitive information. You should only use it internally. Additionally, make the changes you need and build the images yourself.

---

## What does RedVault do?

RedVault replaces the spreadsheets, Word documents, and shared drives that security teams typically use to track findings during a pentest engagement. It provides:

- **Client & Asset Management** — Create clients (the companies you test) and register their assets (servers, web apps, APIs, networks, etc.).
- **Finding Documentation** — Write vulnerability descriptions and remediation recommendations using Markdown with a live preview editor. Attach evidence screenshots directly to findings.
- **Severity Scoring** — Assign CVSS scores and severity levels (Critical, High, Medium, Low, Informational) to each finding.
- **Status Tracking** — Track the lifecycle of each finding: Open → In Progress → Remediated → Closed (or Accepted).
- **Filtering and Search** — Filter for Findings status and severity. Search for a string in the Finding description, remediation and title.
- **Audit Trail** — Every change to a finding is recorded: who changed what, when, and what the old and new values were.
- **PDF Report Generation** — Select findings and generate a professional PDF report using a customisable template. Reports include an executive summary, vulnerability summary tables, and detailed findings with embedded screenshots.
- **User Roles** — Three roles control who can do what:
  - **Admin** — Full access. Can manage users, create clients, and delete anything.
  - **Analyst** — Can create and edit findings, assets, upload evidence, and generate reports. Cannot manage users or delete clients.
  - **Viewer** — Read-only access to everything. Useful for management or clients who need to review findings.
- **Dashboard** — A visual overview showing total findings, severity distribution, a monthly timeline chart, and recent activity.
- **Security** — JWT authentication, encrypted passwords, rate-limited login, security headers, audit logging, and authenticated media access.

---

## Architecture

RedVault runs as four Docker containers:

| Container   | What it does                                       | Port   |
|-------------|----------------------------------------------------|---------|
| **nginx**   | Reverse proxy — TLS termination, serves `/redvault/` | `443`  |
| **db**      | PostgreSQL 16 database — stores all data           | `5432`* |
| **backend** | Django REST API — handles all business logic       | `8000`* |
| **frontend**| Vue.js web interface — what users interact with    | `5173`* |

\* Bound to `127.0.0.1` only — not accessible from outside the VM. All external traffic goes through nginx.

The backend exposes a REST API. The frontend is a single-page application that communicates with the backend via HTTP requests. The database stores clients, assets, findings, evidence files, and user accounts.

---

## Requirements

To run RedVault you need:

- **Docker** (version 20.10 or later) and **Docker Compose** (v2)
- A machine with at least **2 GB of RAM** and **2 GB of free disk space**
- Port **443** available for the nginx reverse proxy (backend and frontend ports are internal only)

That's it. Everything else (Python, Node.js, PostgreSQL, Typst, Pandoc) is included inside the containers.

---

## Quick Start

### 1. Clone the repository

```bash
git clone <your-repo-url> redvault
cd redvault
```

### 2. Create a `.env` file

Create a file called `.env` in the project root with the following content:

```env
# REQUIRED — change these values
SECRET_KEY=your-random-secret-key-at-least-50-characters-long
DB_PASSWORD=a-strong-database-password

# OPTIONAL — defaults shown
DEBUG=False
DB_USER=postgres
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

> **How to generate a secret key:** Run `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` or any random string generator.

### 3. Start the services

```bash
docker compose up --build -d
```

This will build the containers and start everything. The first run takes a few minutes.

### 4. Get the admin password

On first startup, RedVault automatically creates an admin account and prints a random password to the console:

```bash
docker compose logs backend | grep "Admin user created"
```

You will see something like:

```
Admin user created — username: admin, password: xK9#mP2wLq7nBvZs
```

Save this password. You can change it later from the web interface.

### 5. Open the web interface

Go to **https://localhost/redvault/** in your browser (accept the self-signed certificate warning) and log in with:

- **Username:** `admin`
- **Password:** *(the password from step 4)*

---

## Configuration

### Environment Variables

These are set in the `.env` file at the project root. Docker Compose reads them automatically.

| Variable               | Required | Default                          | What it does                                                |
|------------------------|----------|----------------------------------|-------------------------------------------------------------|
| `SECRET_KEY`           | **Yes**  | —                                | Cryptographic key for JWT tokens and session security. Must be unique per installation. |
| `DB_PASSWORD`          | **Yes**  | —                                | PostgreSQL database password.                                |
| `DB_USER`              | No       | `postgres`                       | PostgreSQL username.                                         |
| `DEBUG`                | No       | `False`                          | Set to `True` only for development. Enables detailed error pages. |
| `ALLOWED_HOSTS`        | No       | `localhost,127.0.0.1`            | Comma-separated hostnames the backend will accept requests from. Add your domain if deploying publicly. |
| `CORS_ALLOWED_ORIGINS` | No       | `http://localhost:5173`          | Comma-separated URLs that the frontend runs on. Must match exactly (including port). |
| `ENABLE_ADMIN`         | No       | `False`                          | Enables the Django admin panel at `/admin/`. Not needed for normal use. |
| `HTTP_PROXY`           | No       | —                                | HTTP proxy URL for building behind a corporate firewall (e.g. `http://proxy.example.com:8080/`). |
| `HTTPS_PROXY`          | No       | —                                | HTTPS proxy URL. If not set, falls back to `HTTP_PROXY` where applicable. |

### Building Behind a Corporate Proxy

If your server cannot reach the internet directly (e.g. behind a corporate firewall), add the proxy to your `.env` file:

```env
HTTP_PROXY=http://proxy.example.com:8080/
HTTPS_PROXY=http://proxy.example.com:8080/
```

This is all you need. Docker Compose passes the proxy automatically to:

- **`apt-get`** in the backend Dockerfile (installs system packages)
- **`pip`** in the backend Dockerfile (installs Python dependencies)
- **`curl`** in the backend Dockerfile (downloads Typst)
- **`npm`** in the frontend Dockerfile (installs Node.js dependencies)
- **`apk`** in the nginx container (installs OpenSSL for self-signed certificate generation)

If your server has direct internet access, simply leave these variables out — everything works without them.

> **Note:** The proxy is only used during the build phase and at first startup (for the nginx certificate). It is not baked into the final container images.

### Changing Ports

If ports 5432, 8000, or 5173 are already in use on your machine, edit `docker-compose.yml`:

```yaml
services:
  db:
    ports:
      - "127.0.0.1:5433:5432"    # Change 5433 to your preferred port
  backend:
    ports:
      - "8001:8000"               # Change 8001 to your preferred port
  frontend:
    ports:
      - "3000:5173"               # Change 3000 to your preferred port
```

If you change the backend port, update `VITE_API_URL` in the frontend section of `docker-compose.yml`:

```yaml
  frontend:
    environment:
      VITE_API_URL: http://localhost:8001/api/v1    # Match new backend port
```

If you change the frontend port, update `CORS_ALLOWED_ORIGINS` in `.env`:

```env
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### Deploying Behind Nginx (Included)

RedVault includes an nginx reverse proxy container that serves everything under a `/redvault/` path on port 443 with a self-signed TLS certificate. This lets you run RedVault alongside other services on the same nginx or the same VM without port conflicts.

#### How it works

```
Client browser
  │
  ▼  https://<vm-ip>/redvault/
┌──────────────────────────────────────┐
│  nginx container (:443)              │
│                                      │
│  /redvault/api/*   → backend:8000    │
│  /redvault/media/* → backend:8000    │
│  /redvault/*       → frontend:5173   │
└──────────────────────────────────────┘
```

The backend and frontend ports are bound to `127.0.0.1` only — they are not accessible from outside the VM. All external traffic goes through nginx on port 443.

#### First-time setup

1. Make the nginx entrypoint script executable:

```bash
chmod +x nginx/entrypoint.sh
```

2. Create the SSL data directory:

```bash
mkdir -p data/ssl
```

3. Update your `.env` file:

```env
ALLOWED_HOSTS=localhost,127.0.0.1,backend,<your-vm-ip>
CORS_ALLOWED_ORIGINS=https://<your-vm-ip>
```

4. Start all services (including nginx):

```bash
docker compose up --build -d
```

On first start, the nginx container automatically generates a self-signed certificate at `data/ssl/`. Subsequent starts reuse the existing certificate.

5. Open **https://\<your-vm-ip\>/redvault/** in your browser. Accept the self-signed certificate warning.

#### Using your own certificate

Replace the auto-generated files in `data/ssl/`:

```bash
cp your-cert.crt data/ssl/selfsigned.crt
cp your-cert.key data/ssl/selfsigned.key
docker compose restart nginx
```

#### Running other services on the same nginx

The nginx config file at `nginx/nginx.conf` only handles the `/redvault/` path. You can add additional `location` blocks or separate `server` blocks in the same file for other services. For example:

```nginx
# Already included — RedVault
location /redvault/api/ { ... }
location /redvault/media/ { ... }
location /redvault/ { ... }

# Add your other services
location /other-app/ {
    proxy_pass http://other-service:3000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

If you prefer to use your own existing nginx instance instead of the included one:

1. Remove or comment out the `nginx` service from `docker-compose.yml`
2. Copy the `location` blocks from `nginx/nginx.conf` into your own nginx config
3. Point the `proxy_pass` directives to `127.0.0.1:8000` (backend) and `127.0.0.1:5173` (frontend) instead of `backend:8000` and `frontend:5173`, since your nginx is outside Docker

#### Changing the base path

If you want to serve RedVault under a path other than `/redvault/` (e.g. `/pentest/`), you need to change it in four places:

1. `nginx/nginx.conf` — change all `/redvault/` prefixes in the `location` blocks
2. `frontend/vite.config.ts` — change `base: '/redvault/'` to your path
3. `frontend/src/router/index.ts` — change `createWebHistory('/redvault/')` to your path
4. `frontend/src/api/client.ts` — change the default `VITE_API_URL` and the `/redvault/login` redirect

---

## Customising the Report Template

Reports are generated as PDF files using a template written in [Typst](https://typst.app/), a modern typesetting language. The template and its assets are in:

```
backend/report_templates/
├── report.typ       ← The report template (structure, layout, styling)
├── banner.png       ← Cover page decorative image (top-right)
└── logo.png         ← Company logo (bottom-left of cover page)
```

### Branding Your Reports

**Change the colours:**

Open `report.typ` and edit the "DESIGN TOKENS" section near the top:

```typst
#let brand-dark    = rgb("#1e293b")   // headings, cover title
#let brand-mid     = rgb("#334155")   // subtitles
#let brand-muted   = rgb("#64748b")   // metadata, page headers
#let brand-light   = rgb("#f1f5f9")   // table stripe colour
#let brand-bg      = rgb("#f8fafc")   // light backgrounds
```

Change the hex colour codes to match your company's brand.

**Change the content:**

The template has four sections: Cover Page, Executive Summary, Vulnerability Summary, and Detailed Findings. You can edit the text in any section. Finding data (titles, descriptions, severity, CVSS scores, images) is automatically inserted from the database.

**Change the font:**

Find this line in `report.typ` and change the font name:

```typst
#set text(font: "Libertinus Sans", size: 11pt, fill: black)
```

The container includes Liberation fonts. To use other fonts, add them to `/usr/share/fonts` in the backend Dockerfile.

### Image Sizing in Reports

Evidence screenshots embedded in finding descriptions are automatically sized to 60% of the page width. To change this, edit this line in `report.typ`:

```typst
#show figure.where(kind: image): set image(width: 60%)
```

---

## How Data Is Organised

```
Client (e.g. "Acme Corp")
  └── Asset (e.g. "api.acme.com", type: API)
        └── Finding (e.g. "SQL Injection in login endpoint")
              ├── Evidence (screenshot1.png, burp_request.png)
              └── History (created → updated severity → remediated)
```

- A **Client** is the company being tested.
- An **Asset** is something owned by the client that you're testing (a server, web app, API, etc.).
- A **Finding** is a vulnerability you discovered, linked to an asset.
- **Evidence** is screenshots or files attached to a finding.
- **History** is the automatic audit log of every change made to a finding.

---

## API Reference

All API endpoints are under `/api/v1/`. Authentication is via JWT tokens (obtained from the login endpoint).

### Authentication

| Method | Endpoint                 | Description                  | Who can use it |
|--------|--------------------------|------------------------------|----------------|
| POST   | `/auth/login/`           | Log in, get JWT tokens       | Anyone         |
| POST   | `/auth/refresh/`         | Refresh an expired token     | Anyone         |
| GET    | `/auth/profile/`         | Get current user details     | Logged in      |
| POST   | `/auth/change-password/` | Change your password         | Logged in      |

### Users (Admin only)

| Method          | Endpoint          | Description                    |
|-----------------|-------------------|--------------------------------|
| GET             | `/users/`         | List all users                 |
| POST            | `/users/`         | Create a new user              |
| GET/PATCH/DELETE| `/users/<id>/`    | View, update, or deactivate    |

### Clients

| Method              | Endpoint             | Description              | Who can use it |
|---------------------|----------------------|--------------------------|----------------|
| GET                 | `/clients/`          | List all clients         | Viewer+        |
| POST                | `/clients/`          | Create a new client      | Admin          |
| GET/PUT/PATCH/DELETE| `/clients/<uuid>/`   | View, edit, or delete    | View: Viewer+ / Edit: Admin |

### Assets

| Method              | Endpoint            | Description              | Who can use it |
|---------------------|---------------------|--------------------------|----------------|
| GET                 | `/assets/`          | List all assets          | Viewer+        |
| POST                | `/assets/`          | Create a new asset       | Analyst+       |
| GET/PUT/PATCH/DELETE| `/assets/<uuid>/`   | View, edit, or delete    | View: Viewer+ / Edit: Analyst+ / Delete: Admin |

### Findings

| Method              | Endpoint               | Description              | Who can use it |
|---------------------|------------------------|--------------------------|----------------|
| GET                 | `/findings/`           | List all findings        | Viewer+        |
| POST                | `/findings/`           | Create a new finding     | Analyst+       |
| GET/PUT/PATCH/DELETE| `/findings/<uuid>/`    | View, edit, or delete    | View: Viewer+ / Edit: Analyst+ / Delete: Admin |
| GET                 | `/findings/stats/`     | Dashboard statistics     | Viewer+        |
| GET                 | `/findings/timeline/`  | Monthly finding counts   | Viewer+        |

### Evidence

| Method      | Endpoint                              | Description              | Who can use it |
|-------------|---------------------------------------|--------------------------|----------------|
| GET         | `/findings/<uuid>/evidence/`          | List evidence            | Viewer+        |
| POST        | `/findings/<uuid>/evidence/`          | Upload evidence          | Analyst+       |
| GET/DELETE  | `/findings/<uuid>/evidence/<uuid>/`   | View or delete evidence  | View: Viewer+ / Delete: Analyst+ |

### Finding History

| Method | Endpoint                          | Description                    | Who can use it |
|--------|-----------------------------------|--------------------------------|----------------|
| GET    | `/findings/<uuid>/history/`       | View all changes to a finding  | Viewer+        |

### Reports

| Method | Endpoint                    | Description                    | Who can use it |
|--------|-----------------------------|--------------------------------|----------------|
| GET    | `/reports/`                 | List generated reports         | Viewer+        |
| GET    | `/reports/<uuid>/`          | Get report details             | Viewer+        |
| DELETE | `/reports/<uuid>/`          | Delete a generated report      | Admin          |
| POST   | `/reports/generate/`        | Generate a PDF report          | Analyst+       |

Report templates are managed on disk (see "Customising the Report Template" above) rather than through the API.

---

## Stopping and Restarting

```bash
# Stop all containers (data is preserved)
docker compose down

# Start again
docker compose up -d

# View logs
docker compose logs -f backend

# Restart just the backend (e.g. after config changes)
docker compose restart backend
```

### Resetting Everything

All persistent data is stored in host bind mounts under the `data/` directory:

| Directory | Contents |
|---|---|
| `data/postgres/` | PostgreSQL database files |
| `data/media/` | Uploaded evidence and generated reports |
| `data/logs/` | Application audit and security logs |

To completely reset (deletes all data, users, findings, and uploaded files):

```bash
docker compose down
rm -rf data/postgres data/media data/logs
docker compose up --build -d
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't connect to the web interface | Check that port 5173 is not blocked. Run `docker compose ps` to verify containers are running. |
| "Connection refused" on login | The backend may still be starting. Wait 10 seconds and try again. Check `docker compose logs backend` for errors. |
| Forgot the admin password | Reset the database: `docker compose down`, then delete `data/postgres/`, and start again. A new admin password will be generated. |
| Port already in use | Change the port in `docker-compose.yml` (see "Changing Ports" above). |
| Report generation fails | Check `docker compose logs backend` for Typst compilation errors. Ensure `banner.png` and `logo.png` exist in `backend/report_templates/`. |

---

## Project Structure

```
redvault/
├── docker-compose.yml          ← Container orchestration
├── .env                        ← Your configuration (create this)
├── README.md                   ← This file
├── nginx/                      ← Nginx reverse proxy config
│   ├── nginx.conf              ← Nginx site configuration
│   └── entrypoint.sh           ← Auto-generates self-signed TLS cert
├── data/                       ← Persistent data (bind-mounted into containers)
│   ├── postgres/               ← PostgreSQL database files
│   ├── media/                  ← Uploaded evidence and generated reports
│   ├── logs/                   ← Audit and security logs
│   └── ssl/                    ← TLS certificate and key (auto-generated)
├── backend/                    ← Django REST API
│   ├── DOCUMENTATION.md        ← Detailed backend documentation
│   ├── Dockerfile              ← Backend container recipe
│   ├── entrypoint.sh           ← Startup script (migrations + server)
│   ├── requirements.txt        ← Python dependencies
│   ├── config/                 ← Django settings, middleware, URL routing
│   ├── findings/               ← Findings, assets, clients, evidence, reports
│   ├── users/                  ← User accounts and authentication
│   └── report_templates/       ← PDF report template and images
└── frontend/                   ← Vue.js web interface
    ├── DOCUMENTATION.md        ← Detailed frontend documentation
    ├── Dockerfile              ← Frontend container recipe
    ├── package.json            ← JavaScript dependencies
    └── src/                    ← Application source code
```

For detailed technical documentation:
- **Backend:** see `backend/DOCUMENTATION.md`
- **Frontend:** see `frontend/DOCUMENTATION.md`
