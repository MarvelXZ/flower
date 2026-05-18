# Flower Frontend Rendering Strategy

Ovaj dokument definise kada Flower koristi Django templates, HTMX, Alpine.js i
React islands. Cilj je da se spreci frontend drift, dupliranje auth/state logike
i nepotreban prelazak na full SPA.

## Odluka

Flower koristi hybrid enterprise frontend:

- Django templates su glavni app shell.
- `backend/static/css/flower-ui.css` je single source of truth za dizajn sistem.
- HTMX se koristi za server-side partial updates.
- Alpine.js se moze koristiti za mali lokalni UI state.
- React se koristi selektivno, kao island layer za kompleksne interaktivne
  module.

Full React SPA nije default pravac za Flower.

## Zasto Ne Full SPA

Za trenutnu fazu Flower-a full SPA bi doneo vise troska nego vrednosti:

- duplira auth/session i permission handling,
- uvodi zaseban global frontend state za workflow-e koje server vec zna,
- komplikuje multi-tenant rendering i context propagation,
- povecava frontend maintenance,
- usporava isporuku CRUD/operator ekrana,
- povecava rizik da Django templates, React i API ugovori odu u razlicite
  smerove.

React ostaje vazan, ali samo tamo gde stvarno resava problem koji templates i
HTMX ne resavaju elegantno.

## Rendering Matrix

| UI tip | Primarna tehnologija | Razlog |
| --- | --- | --- |
| App shell, navigacija, layout | Django templates | Server vec zna tenant, user, permissions i locale. |
| Operator/admin dashboard | Django templates | Brz razvoj, prirodan auth/session flow, dobar server-side context. |
| CRUD forme | Django templates | Validacija i permission checks ostaju blizu Django form/API logike. |
| Tables, filters, pagination | Django templates + HTMX | Server-side query pravila i parcijalno osvezavanje bez SPA kompleksnosti. |
| Modal forme, inline edits | HTMX | Mali response fragmenti, jednostavan UX, bez globalnog JS state-a. |
| Dropdowns, toggles, drawers | Alpine.js | Lokalno stanje bez React mount-a. |
| Telemetry charts | React island | Chart lifecycle, realtime stream i interakcije su prirodniji u React-u. |
| Realtime dashboards | React island | WebSocket/SSE state, buffering i rich UI kontrole. |
| Device maps | React island | Mape, zoom/pan, clustering i live updates. |
| Marketplace public UX | React island ili kasnije Next.js | Bogatiji public discovery/search; SSR tek kada SEO postane prioritet. |
| Onboarding wizard | React island | Multi-step client state i kompleksna validacija. |
| Drag/drop planters | React island | Direktna manipulacija i optimistic UI. |
| Mobile-like interactive screens | React island | Offline/realtime-like UX na webu. |
| Django admin | Django/admin templates | Interni admin tooling, ne praviti paralelni SPA. |

## Backend UI Stack

Default stack za authenticated operator UI:

```text
Django templates
HTMX partials
Alpine.js for small local state
flower-ui.css
```

Koristi za:

- tenant management,
- provider ops,
- forms,
- CRUD,
- settings,
- audit pregled,
- billing management,
- internal workflow ekrane,
- server-rendered dashboarde.

## React Island Stack

Default stack za React islands:

```text
React + TypeScript
Vite
react-i18next
TanStack Query or a small fetch abstraction
Zustand only when local module state becomes non-trivial
Recharts or ECharts for charts
flower-ui.css
```

React island mora imati jasno vlasnistvo:

- jedan mount point,
- jedan API contract,
- svoj loading/empty/error state,
- fallback ako JS ne uspe,
- bez dupliciranja globalne navigacije i app shell-a.

## Single Source Of Truth

`backend/static/css/flower-ui.css` je canonical design system.

To znaci:

- Django templates koriste `{% static 'css/flower-ui.css' %}`.
- React koristi `frontend/src/styles/flower-ui.css`, koji importuje canonical
  CSS.
- Novi tokeni prvo idu u `backend/static/css/flower-ui.css`.
- React komponenta ne sme definisati sopstvenu paletu.
- Django template ne sme hardcodovati boje, spacing ili shadow vrednosti.
- Mobile app treba da mapira iste semantic token role u Flutter theme.

## Design Direction

Flower treba da izgleda kao premium smart plant infrastructure platform.

Vizuelni pravac:

- concrete gray,
- warm white,
- sand/beige,
- leaf green,
- graphite,
- muted earth tones,
- premium minimal,
- organic enterprise,
- green infrastructure,
- clean whitespace,
- soft shadows,
- textured but restrained surfaces.

Izbegavati:

- generic Bootstrap admin izgled,
- genericki SaaS dashboard,
- neon/cyber palete,
- preterano tamne crypto dashboard obrasce,
- dekorativne gradiente bez informacione svrhe.

## Design System Phase

Pre vecih novih ekrana, stabilizovati design system:

- typography scale,
- spacing scale,
- color tokens,
- semantic status tokens,
- elevation/shadow system,
- responsive breakpoints,
- focus/accessibility states,
- button states,
- form system,
- table system,
- notification/alert system,
- empty/loading states,
- KPI/card widgets,
- chart styling,
- optional dark mode strategy.

## Pravila Za Nove Ekrane

1. Ako je ekran CRUD, tabela, forma ili interni workflow, pocni sa Django
   templates.
2. Ako ekran treba samo parcijalni refresh, koristi HTMX.
3. Ako ekran ima samo lokalni UI toggle/dropdown/drawer state, koristi Alpine.js.
4. Ako ekran ima realtime data, charting, maps, drag/drop ili kompleksan
   client-side state, koristi React island.
5. Ne praviti full SPA rutu dok ne postoji eksplicitan razlog i vlasnik.
6. Ne duplirati app shell u React-u ako Django vec renderuje auth shell.
7. Svaki novi UI mora koristiti `fw-*` klase ili tokene iz `flower-ui.css`.
8. Svaki novi React tekst ide kroz `react-i18next`.
9. Svaki Django template tekst ide kroz `{% translate %}`.
10. Ako se uvodi nova komponenta, prvo proveriti da li treba da postoji u
    shared UI kit-u.

## AI Koder Handoff Pravilo

Kada AI koder radi frontend, mora na kraju da napise:

- koje rendering odluke je doneo,
- koje foldere/fajlove je dirao,
- da li je koristio Django, HTMX, Alpine ili React i zasto,
- koje komande je pokrenuo,
- da li je promenio `flower-ui.css`,
- da li je dodao ili promenio i18n kljuceve.

Integrator zatim proverava:

```powershell
python -m uv run --env-file ../.env python manage.py check
cd frontend
npm.cmd run build
```

Ako postoji local browser target, integrator radi i smoke test u browseru.
