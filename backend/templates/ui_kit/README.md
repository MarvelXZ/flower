# Flower UI Kit

Shared interface language for backend Django templates, HTMX fragments, and the React frontend.

## Files

- `backend/static/css/flower-ui.css` contains design tokens and utility component classes.
- `backend/templates/ui_kit/index.html` shows the server-rendered kit and HTMX form swap.
- `backend/templates/partials/ui_feedback.html` is the sample HTMX partial.
- `frontend/src/ui-kit/UIKit.tsx` mirrors the same patterns in React.
- `frontend/src/styles/flower-ui.css` imports the backend CSS so the classes stay aligned.

## Core Classes

- Layout: `fw-app`, `fw-sidebar`, `fw-page`, `fw-topbar`, `fw-grid`.
- Content: `fw-panel`, `fw-card`, `fw-section`, `fw-alert`, `fw-empty`.
- Controls: `fw-btn`, `fw-btn-primary`, `fw-btn-secondary`, `fw-segmented`.
- Forms: `fw-form`, `fw-field-group`, `fw-label`, `fw-field`, `fw-select`, `fw-textarea`.
- Data: `fw-kpi`, `fw-badge`, `fw-status`, `fw-table`, `fw-meter`.

## Routes

- `/` renders the platform presentation page.
- `/dashboard/` renders the platform operations dashboard using the kit.
- `/ui-kit/` renders the full Django/HTMX kit.
- `/ui-kit/sample/` accepts the sample HTMX form POST and returns a partial.
