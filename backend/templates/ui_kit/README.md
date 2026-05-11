# PlantOps UI Kit

Shared interface language for backend Django templates, HTMX fragments, and the React frontend.

## Files

- `backend/static/css/plantops-ui.css` contains design tokens and utility component classes.
- `backend/templates/ui_kit/index.html` shows the server-rendered kit and HTMX form swap.
- `backend/templates/partials/ui_feedback.html` is the sample HTMX partial.
- `frontend/src/ui-kit/UIKit.tsx` mirrors the same patterns in React.
- `frontend/src/styles/plantops-ui.css` imports the backend CSS so the classes stay aligned.

## Core Classes

- Layout: `po-app`, `po-sidebar`, `po-page`, `po-topbar`, `po-grid`.
- Content: `po-panel`, `po-card`, `po-section`, `po-alert`, `po-empty`.
- Controls: `po-btn`, `po-btn-primary`, `po-btn-secondary`, `po-segmented`.
- Forms: `po-form`, `po-field-group`, `po-label`, `po-field`, `po-select`, `po-textarea`.
- Data: `po-kpi`, `po-badge`, `po-status`, `po-table`, `po-meter`.

## Routes

- `/` renders the dashboard using the kit.
- `/ui-kit/` renders the full Django/HTMX kit.
- `/ui-kit/sample/` accepts the sample HTMX form POST and returns a partial.
