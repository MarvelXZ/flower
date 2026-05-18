# Flower — Frontend Architecture

## Overview

Flower uses a **hybrid rendering** strategy: Django templates + HTMX for operational screens, and React (Vite) for interactive-heavy surfaces. Both sides share a single CSS design system via `flower-ui.css`.

---

## Boundaries

```text
┌──────────────────────────────────────────────────────────┐
│                    FLOWER FRONTEND                        │
│                                                           │
│  ┌───────────────────────┐  ┌─────────────────────────┐  │
│  │  Django + HTMX        │  │  React (Vite)           │  │
│  │  (operator / admin)   │  │  (public / interactive) │  │
│  │                       │  │                         │  │
│  │  /app/**              │  │  / (landing page)       │  │
│  │  /admin/**            │  │  /login  /register      │  │
│  │  /dashboard/**        │  │  /telemetry/**          │  │
│  │  /locations/**        │  │  /marketplace/**        │  │
│  │  /planters/**         │  │  /care-calendar/**      │  │
│  │  /devices/**          │  │                         │  │
│  │  /alerts/**           │  │  Reason: SSE/WS charts, │  │
│  │  /tasks/**            │  │  maps, drag-and-drop,   │  │
│  │  /providers/**        │  │  complex SPA UX         │  │
│  │  /billing/**          │  │                         │  │
│  └───────────────────────┘  └─────────────────────────┘  │
│                                                           │
│  ┌───────────────────────────────────────────────────┐    │
│  │           Shared: flower-ui.css                   │    │
│  │  Loaded by Django via {% static %} and by React   │    │
│  │  via @import. Same tokens, same component classes.│    │
│  └───────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

## Django + HTMX (Operator UI)

**When to use**: CRUD screens, tables, forms, dashboards with server-side data, admin tools, settings, scheduling.

**Template hierarchy**:

```text
base.html                  ← HTML shell, CSS, HTMX, global scripts
└── app_base.html          ← Authenticated shell (fw-app layout)
    ├── partials/sidebar.html
    ├── partials/topbar.html
    └── {feature}/index.html, detail.html, form.html …
```

**Rules**:

- All static text uses `{% translate "..." %}` or `gettext_lazy(...)` in Python
- Dynamic model fields use `django-modeltranslation`
- Only `fw-*` CSS classes — no hardcoded colors or sizes in templates
- HTMX fragments use `{% include "partials/..." %}` for reusable partial renders
- Context variable `sidebar_active` drives active nav state (e.g. `"dashboard"`, `"alerts"`)

---

## React + Vite (Public / Interactive UI)

**When to use**: public landing/marketing, real-time telemetry charts (WebSocket/SSE), interactive provider marketplace, care calendar with drag-and-drop, device maps.

**Why not Next.js now**: existing Vite scaffold is functional; SSR is not needed for authenticated app screens. Migrate to Next.js when SEO on public landing becomes a priority.

**Entry**: `frontend/src/main.tsx` → `App.tsx`

**Build output**: `frontend/dist/` — served by Nginx for React routes; Django handles `/api/**` and operator routes.

---

## Nginx Routing (production)

```nginx
location /api/       { proxy_pass http://django:8000; }
location /admin/     { proxy_pass http://django:8000; }
location /app/       { proxy_pass http://django:8000; }
location /           { try_files $uri $uri/ /index.html; }
```

Django also serves operator routes (`/dashboard/`, `/planters/`, etc.).

---

## Shared Design System

`backend/static/css/flower-ui.css` is the **single source of truth** for:

- CSS custom property tokens (`--color-concrete-*`, `--color-leaf-*`, etc.)
- Semantic tokens (`--fw-bg`, `--fw-primary`, `--fw-danger`, etc.)
- All `fw-*` component classes

Django loads it via `{% static 'css/flower-ui.css' %}`.
React imports it via `frontend/src/styles/flower-ui.css` which re-exports the same file.

**Never** define colors or spacing outside this file.

---

## i18n Strategy

| Layer | Tool | When |
| --- | --- | --- |
| Django static text | `gettext_lazy`, `{% translate %}` | All template strings |
| Django model fields | `django-modeltranslation` | Translatable model content |
| React static text | `react-i18next` | All React UI strings |
| React API content | Served from API with correct locale | Dynamic data |

Supported locales: `en`, `sr-Latn`, `sr-Cyrl`.
