# Frontend Boundaries

PlantOps uses two frontend technologies with clear boundaries.

## HTMX + Django Templates

**Use for:**
- Admin interface
- CRUD operations for locations, planters, plants, devices
- Task lists and forms
- User management
- Any page that is primarily forms and tables

**Why HTMX:**
- Simpler for non-technical users (gardeners, facility managers).
- Faster to develop for standard CRUD.
- No build step required.
- Works naturally with Django's form system and CSRF protection.

**Location:** `backend/templates/`

**Base template:** `backend/templates/base.html`

**Blocks:**
- `title`
- `extra_css`
- `content`
- `extra_js`

## React + Vite

**Use for:**
- Realtime dashboard
- Expert analytics
- Charts and visualizations
- Interactive maps
- Any page requiring heavy client-side interactivity

**Why React:**
- Better for complex, interactive UIs.
- Excellent ecosystem for charts (Recharts, D3).
- TypeScript support for large codebases.

**Location:** `frontend/src/`

**Entry point:** `frontend/src/main.tsx`

**Modules:**
- `dashboard/` — Overview, KPIs, charts
- `expert/` — Advanced analytics, data exploration
- `realtime/` — Live sensor data, WebSocket feeds

## Rules

1. **Do NOT mix HTMX and React on the same page randomly.**
   - HTMX pages may embed small React widgets via mounting points.
   - React pages may fetch HTML partials from HTMX endpoints for simple forms.
   - But the PRIMARY technology of a page must be clear.

2. **API is shared.**
   - Both HTMX and React consume the same DRF API.
   - HTMX uses `hx-get`, `hx-post` against API endpoints.
   - React uses `fetch` / `axios` against API endpoints.

3. **Authentication is shared.**
   - Both use Django session authentication.
   - CSRF tokens are handled automatically.

4. **Routing:**
   - Django handles server-side routing for HTMX pages.
   - React Router handles client-side routing for React pages.
   - Nginx routes `/api/*` and `/admin/*` to Django.
   - Nginx routes all other paths to the React dev server (local) or static build (production).
