# Frontend Documentation — RedVault

This document explains how the RedVault frontend works. It is intended for developers who want to understand, modify, or extend the web interface.

---

## Overview

The frontend is a single-page application (SPA) built with **Vue.js 3** and **TypeScript**. It runs in the browser and communicates with the Django backend via HTTP requests. All data rendering, routing, and user interaction happen client-side.

The frontend provides:

- A login page with JWT authentication
- A dashboard with statistics and charts
- CRUD interfaces for clients, assets, and findings
- A split-pane Markdown editor for writing finding descriptions
- Evidence upload with drag-and-drop and image previews
- A chronology sidebar showing the complete audit trail of each finding
- Report generation with finding selection
- User management (admin only)

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Vue.js 3.5 | UI framework (Composition API with `<script setup>`) |
| TypeScript 5.9 | Static typing |
| Vite 7.3 | Development server and build tool |
| Pinia 3.0 | State management (auth store) |
| Vue Router 4.6 | Client-side routing with navigation guards |
| Axios 1.13 | HTTP client with JWT token interceptors |
| marked 17.0 | Converts Markdown to HTML for the live preview |
| DOMPurify 3.3 | Sanitises rendered HTML to prevent XSS attacks |

---

## File Structure

```
frontend/
├── Dockerfile              # Container: Node.js 20 + npm
├── index.html              # SPA entry point (single HTML file)
├── package.json            # Dependencies and scripts
├── vite.config.ts          # Vite dev server configuration
├── tsconfig.json           # TypeScript configuration
└── src/
    ├── main.ts             # App bootstrap (creates Vue app, registers router + Pinia)
    ├── App.vue             # Root component (just a <RouterView>)
    ├── style.css           # Global styles (dark theme)
    ├── api/
    │   └── client.ts       # Axios HTTP client with JWT interceptors
    ├── layouts/
    │   └── AppLayout.vue   # Main layout: sidebar navigation + content area
    ├── router/
    │   └── index.ts        # Route definitions and authentication guards
    ├── stores/
    │   └── auth.ts         # Pinia store for authentication state
    ├── types/
    │   └── index.ts        # TypeScript interfaces (match backend API responses)
    └── views/
        ├── LoginView.vue           # Login form
        ├── DashboardView.vue       # Statistics cards, severity chart, timeline
        ├── ClientsView.vue         # Client list + create modal
        ├── ClientDetailView.vue    # Client detail/edit page
        ├── AssetsView.vue          # Asset list + create modal
        ├── AssetDetailView.vue     # Asset detail/edit page
        ├── FindingsView.vue        # Finding list with filters
        ├── FindingDetailView.vue   # Finding editor + evidence + chronology
        ├── TemplatesView.vue       # Generated reports list
        └── UsersView.vue           # User management (admin only)
```

---

## Pages and What They Do

### Login Page (`LoginView.vue`)

Simple username/password form. On successful login, JWT tokens are stored in `localStorage` and the user is redirected to the dashboard.

### Dashboard (`DashboardView.vue`)

Shows an overview of the current state:

- **Stats cards:** Total findings, open findings, critical findings, total assets
- **Severity distribution:** Horizontal bar chart showing how many findings exist at each severity level (built with CSS, no chart library)
- **Timeline:** Monthly bar chart showing when findings were created over time
- **Recent findings:** Table of the most recently created findings with quick links

### Clients Page (`ClientsView.vue`)

- Searchable list of all clients in a table (name, description, asset count, creation date)
- "New Client" button opens a modal to create a client (admin only)
- Click a row to go to the client detail page

### Client Detail (`ClientDetailView.vue`)

- Shows client name, description, who created it, and when
- "Edit" button switches to inline editing mode (admin only)
- "Delete" button with confirmation dialog (admin only)
- Table of assets that belong to this client

### Assets Page (`AssetsView.vue`)

- Searchable, filterable list of all assets
- Filter by asset type (host, web app, API, etc.)
- "New Asset" button opens a modal with all asset fields including a client dropdown
- Click a row to go to the asset detail page

### Asset Detail (`AssetDetailView.vue`)

- All asset fields displayed, with edit mode for analysts and admins
- Client selector dropdown in edit mode
- Table of findings linked to this asset
- Delete button (admin only)

### Findings Page (`FindingsView.vue`)

- Searchable, filterable list of all findings
- Filter by severity and status
- Quick stats bar showing counts per severity
- Colour-coded severity and status badges
- Click a row to go to the finding detail page

### Finding Detail (`FindingDetailView.vue`)

This is the most complex page, with a two-column layout:

**Left column (main content):**

- **View mode:** Finding title, severity badge, CVSS score, status, assigned user, linked asset. Description and recommendations rendered as formatted Markdown.
- **Edit mode:** Split-pane editor — Markdown textarea on the left, live preview on the right. All fields are editable. Severity and status dropdowns. Asset and assignee dropdowns.
- **Evidence section:** Upload zone (drag-and-drop), gallery of uploaded evidence. Images are shown inline as thumbnails, other files as download links. Each evidence item can be deleted.

**Right column (chronology sidebar):**

- Sticky sidebar showing the complete history of the finding
- Timeline with coloured dots: green for "created", blue for "updated"
- Each entry shows who made the change and when
- Updated entries expand to show which fields changed (old value → new value)
- Automatically updates when the page loads

### Reports Page (`TemplatesView.vue`)

Table of all previously generated reports with report name, finding count, who generated it, and when. Download any report again or delete it (admin only).

### Users Page (`UsersView.vue`)

- Admin-only page (redirects non-admins to dashboard)
- Table of all users with role, active status, and creation date
- Create user form: username, password, role selection
- Edit user: change role or deactivate/reactivate
- Users are deactivated (not deleted) to preserve audit trails

---

## Authentication Flow

1. User enters username and password on the login page
2. Frontend sends POST to `/api/v1/auth/login/`
3. Backend returns an access token (60 min lifetime) and refresh token (24 hr lifetime)
4. Tokens are stored in `localStorage`
5. Every subsequent API request includes the access token in the `Authorization` header
6. When the access token expires, the Axios interceptor automatically sends the refresh token to `/api/v1/auth/refresh/` to get a new access token
7. If the refresh token is also expired, the user is logged out and redirected to the login page

### Token Refresh Queue

When multiple API requests fail simultaneously due to an expired token, only one refresh request is sent. Other requests are queued and retried after the new token is received. This prevents race conditions.

---

## Routing and Navigation Guards

All authenticated pages are children of `AppLayout.vue` (which provides the sidebar and top bar).

| Path | Page | Access |
|---|---|---|
| `/login` | Login | Guest only (redirects to `/` if already logged in) |
| `/` | Dashboard | Any logged-in user |
| `/findings` | Findings list | Any logged-in user |
| `/findings/:id` | Finding detail | Any logged-in user |
| `/assets` | Assets list | Any logged-in user |
| `/assets/:id` | Asset detail | Any logged-in user |
| `/clients` | Clients list | Any logged-in user |
| `/clients/:id` | Client detail | Any logged-in user |
| `/reports` | Generated reports | Any logged-in user |
| `/users` | User management | Admin only |

Navigation guards (`router/index.ts`):

- **`requiresAuth`**: If no token is present, redirect to `/login`
- **`guest`**: If a token is present, redirect to `/` (prevents logged-in users from seeing the login page)
- **`requiresAdmin`**: If the user is not an admin, redirect to `/`

---

## API Client (`api/client.ts`)

The Axios instance:

- **Base URL:** Configured via `VITE_API_URL` environment variable (default: `http://localhost:8000/api/v1`)
- **Request interceptor:** Automatically attaches `Authorization: Bearer <token>` to every request
- **Response interceptor:** On 401 errors, attempts token refresh. Uses a subscriber queue for concurrent requests.

---

## State Management (`stores/auth.ts`)

The Pinia auth store manages:

| Property | What it holds |
|---|---|
| `user` | Current user's profile (id, username, role) or null |
| `accessToken` | JWT access token or null |
| `refreshToken` | JWT refresh token or null |
| `isAuthenticated` | Whether a valid token exists |
| `isAdmin` | Whether the user's role is "admin" |
| `isAnalyst` | Whether the user's role is "admin" or "analyst" |

| Method | What it does |
|---|---|
| `login(credentials)` | Sends login request, stores tokens, fetches profile |
| `fetchProfile()` | Gets current user info from `/auth/profile/` |
| `logout()` | Clears all tokens and user data |
| `init()` | Called on app startup — if a token exists, fetches profile |

---

## TypeScript Types (`types/index.ts`)

All interfaces match the backend API response shapes:

- `User`, `UserCreate`, `UserUpdate` — User management
- `Client`, `ClientCreate` — Client CRUD
- `Asset`, `AssetCreate`, `AssetMinimal` — Asset management
- `Finding`, `FindingCreate` — Findings with CVSS and Markdown content
- `Evidence` — File attachment metadata
- `FindingHistoryEntry`, `FindingHistoryChange` — Audit trail entries
- `ReportTemplate`, `GeneratedReport` — Report management
- `PaginatedResponse<T>` — Generic wrapper for paginated API responses
- `LoginRequest`, `TokenPair` — Authentication types
- `Severity`, `FindingStatus`, `AssetType` — String union types

---

## Security Considerations

- **XSS prevention:** All Markdown content is rendered via `marked` and then sanitised with `DOMPurify` before being inserted into the DOM. This strips any malicious `<script>` tags or event handlers.
- **Token storage:** JWT tokens are stored in `localStorage`. This is standard for SPAs but means tokens are accessible to JavaScript. The short access token lifetime (60 min) and refresh rotation limit the risk.
- **CORS:** The backend only accepts requests from the configured frontend origin. The frontend does not need any CORS configuration.

---

## Development

### Running Locally (without Docker)

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173` with hot module replacement.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Backend API base URL. Change this if the backend runs on a different port or host. |

Set this in `docker-compose.yml` (under the `frontend` service's `environment` section) or in a `.env` file in the `frontend/` directory.

### Building for Production

```bash
npm run build
```

Output goes to `dist/`. The contents can be served by any static file server (nginx, Caddy, etc.).

---

## Extending the Frontend

### Adding a new page

1. Create a new `.vue` file in `src/views/`
2. Add a route in `src/router/index.ts` under the `AppLayout` children
3. Add a navigation link in `src/layouts/AppLayout.vue`
4. Set the appropriate `meta` (e.g. `requiresAuth: true`, `requiresAdmin: true`)

### Adding a new API call

1. Import `api` from `@/api/client`
2. Use `api.get()`, `api.post()`, etc. — authentication headers are added automatically
3. Add TypeScript interfaces in `src/types/index.ts` to match the response shape

### Changing the theme

Edit `src/style.css`. The app uses a dark theme with CSS custom properties. Key colour variables are defined at the top of the file.
