# Flower — React Frontend Guide

## When to use React

Use React only where it genuinely adds value over Django templates:

| Feature | Why React |
|---|---|
| Public landing page | Marketing UX, animations, performance |
| Telemetry dashboards | Real-time charts via WebSocket/SSE |
| Provider marketplace | Complex filtering, infinite scroll, optimistic UI |
| Care calendar | Drag-and-drop scheduling (react-dnd or dnd-kit) |
| Device maps | Leaflet/MapLibre interactive maps |

Everything else: use Django templates + HTMX.

---

## Folder structure

```
frontend/src/
├── main.tsx                    ← Bootstrap: React, i18n, Router
├── App.tsx                     ← Root component, route definitions
├── vite-env.d.ts
│
├── styles/
│   └── flower-ui.css           ← @import from backend/static/css/flower-ui.css
│
├── i18n/
│   ├── index.ts                ← i18next config
│   └── locales/
│       ├── en.json
│       ├── sr.json             ← sr-Latn fallback
│       ├── sr-Latn.json
│       └── sr-Cyrl.json
│
├── components/
│   └── ui/                     ← Design system React components
│       ├── Button.tsx
│       ├── Badge.tsx           ← Badge + StatusBadge
│       ├── KpiCard.tsx
│       ├── Alert.tsx
│       ├── Meter.tsx
│       └── index.ts            ← Barrel export
│
├── modules/
│   ├── dashboard/              ← Operator dashboard (if React version needed)
│   ├── expert/                 ← Advanced analytics
│   ├── realtime/               ← WebSocket/SSE telemetry
│   ├── landing/                ← Public marketing page
│   └── marketplace/            ← Provider marketplace
│
└── ui-kit/
    └── UIKit.tsx               ← React version of the design system showcase
```

---

## Design system in React

Import once at the app root:
```tsx
import "@/styles/flower-ui.css";
```

Use `fw-*` classes directly or via the typed component wrappers:

```tsx
import { Button, Badge, StatusBadge, KpiCard, Alert, Meter } from "@/components/ui";

<Button variant="primary">Save</Button>
<StatusBadge tone="ok">Online</StatusBadge>
<KpiCard label="Active planters" value="428" />
<Meter value={82} tone="ok" />
<Alert variant="warning" title="Low moisture">3 planters below threshold.</Alert>
```

---

## Component conventions

- Props are typed with TypeScript — no `any`
- Variant strings use union types: `"primary" | "secondary" | "ghost" | "danger"`
- Forward refs on interactive elements (`Button`)
- `className` prop always accepted for extension; never override via inline styles
- i18n via `useTranslation()` — no hardcoded strings in component files

---

## i18n in React

```tsx
import { useTranslation } from "react-i18next";

function MyComponent() {
  const { t } = useTranslation();
  return <h1>{t("dashboard.title")}</h1>;
}
```

Language files: `frontend/src/i18n/locales/{en,sr,sr-Latn,sr-Cyrl}.json`

The `sr.json` file is the Latin script fallback. `sr-Latn.json` and `sr-Cyrl.json` can override specific strings.

---

## API integration

All API calls go through `/api/` — proxied to Django in development by Vite:

```ts
const response = await fetch("/api/v1/planters/", {
  headers: { "X-CSRFToken": getCsrfToken() },
});
```

Authentication is Django session cookies — same as templates.

For typed API clients, use `openapi-typescript` to generate types from the DRF Spectacular schema:
```bash
npx openapi-typescript http://localhost:8000/api/docs/?format=json -o src/api/types.ts
```

---

## State management

| Scope | Tool |
|---|---|
| Local UI state | `useState` / `useReducer` |
| Server data / caching | React Query (`@tanstack/react-query`) |
| Global auth/tenant | React Context |
| Complex cross-module | Zustand (if needed later) |

Avoid Redux — it is unnecessary for this scale.

---

## Real-time data

For telemetry screens, use the browser `EventSource` API (SSE from Django) or a WebSocket hook:

```ts
useEffect(() => {
  const es = new EventSource("/api/v1/sensors/stream/");
  es.onmessage = (e) => setReadings(JSON.parse(e.data));
  return () => es.close();
}, []);
```

---

## Shared token system

React and Django templates use **identical** CSS tokens. The `--color-concrete-*`, `--color-leaf-*`, `--fw-primary`, etc. work in both:

```tsx
// inline style using a token (rare — prefer fw-* classes)
<div style={{ background: "var(--fw-bg)" }} />
```

This guarantees visual consistency without duplicating the design system.

---

## Development

```bash
cd frontend
npm run dev      # starts Vite on :5173, proxies /api to Django
npm run build    # outputs to dist/
npm run lint     # TypeScript + ESLint
```
