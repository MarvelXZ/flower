# Flower Project App Map

Ovaj dokument opisuje glavne delove projekta i odgovornost svake aplikacije.
Pregled je zasnovan na trenutnom stanju repozitorijuma, posebno na
`backend/config/settings/base.py`, `backend/config/urls.py`, modelima i
postojecoj arhitektonskoj dokumentaciji.

## Kratak Pregled

Flower je modularni monolit u Django-u. Koristi `django-tenants`, pa isti
deployment opsluzuje vise tenant schema. Public schema drzi podatke koji moraju
biti dostupni pre ulaska u konkretan tenant, dok tenant schema drzi operativne
podatke za vlasnike, providere i hibridne tenante.

Glavna ideja:

- Owner tenant je izvor istine za lokacije, biljke, saksije, uredjaje,
  telemetriju i care state.
- Provider tenant dobija dozvoljene kopije podataka preko B2B API-ja,
  outbox-a i sync engine-a.
- Marketplace zivi u public kontekstu da bi provideri mogli biti otkriveni
  izvan pojedinacnog tenant schema.
- Mobile provider app radi protiv provider B2B/provider ops API-ja i koristi
  offline/realtime sync pattern.

## Runtime Slojevi

| Sloj | Folder | Uloga |
| --- | --- | --- |
| Django backend | `backend/` | Glavni modularni monolit, API, admin, dashboard, B2B, Celery taskovi |
| React frontend | `frontend/` | Vite/React UI kit i buduci React ekrani |
| Django templates | `backend/templates/`, `backend/static/` | Server-rendered dashboard, UI kit, HTMX fragmenti i zajednicki CSS |
| Mobile app | `mobile/provider_app/` | Flutter provider operator aplikacija |
| Infra | `infra/`, `docker-compose.yml` | Docker, nginx, Mosquitto MQTT, Prometheus, Grafana placeholderi |
| Docs/governance | `docs/` | Arhitektura, pravila, audit checkliste i frontend dokumentacija |

## Django App Status

### Public Schema Apps

Ove aplikacije su u `SHARED_APPS` i zive u public schema.

| App | Zaduzenje |
| --- | --- |
| `apps.tenancy` | Tenant registracija i domeni. Modeli `Client` i `Domain` su osnova za `django-tenants`; definisu schema, slug, tip tenanta i domen mapiranje. |
| `apps.marketplace` | Public marketplace za provider profile, listinge, service areas, ponude i order-e. Omogucava discovery providera i komercijalni tok izmedju owner i provider tenant-a. |
| `apps.core` | Zajednicka infrastruktura: bazni modeli, health/ready/live endpointi, metrics endpoint, request context middleware, Celery tenant task base, shared dashboard i UI kit view-ovi. |

### Tenant Schema Apps

Ove aplikacije su u `TENANT_APPS` i predstavljaju aktivan runtime domen u
tenant schema.

| App | Zaduzenje |
| --- | --- |
| `apps.identity` | Tenant-scoped korisnici, role i mobile sesije. Model `User` je tenant korisnik; `MobileSession` prati refresh token sesije za provider/mobile runtime. |
| `apps.locations` | Fizicke ili servisne lokacije tenanta. Drzi naziv, tip lokacije, adresu, geo koordinate i timezone. |
| `apps.plants` | Konkretne biljke u owner tenant-u. Povezuje biljku sa vrstom iz `care_engine.PlantSpecies` i prati status biljke. |
| `apps.pots` | Kontekst za posude/saksije u canonical DDD strukturi. Trenutno deluje kao scaffold sa API/services/selectors paketima, ali bez aktivnih model fajlova u trenutnom pregledu. |
| `apps.devices` | IoT device control plane. Drzi uredjaje, kredencijale, heartbeats, shadow state, domain events i provisioning audit. Servisi pokrivaju provisioning, aktivaciju, MQTT ACL i event subscriber-e. |
| `apps.telemetry` | Ingest i skladistenje senzorskih ocitavanja. Model `SensorReading` cuva time-series-friendly podatke; servisi obradjuju MQTT payload i kreiraju outbox/evaluaciju pravila. |
| `apps.alerts` | Noviji alert bounded context za pravila upozorenja, alert instance i alert evente. Modeli `AlertRule`, `Alert`, `AlertEvent` izgledaju kao nova generacija alert domena. |
| `apps.care_engine` | Pravila nege i evaluacija metrika. Drzi `PlantSpecies`, `Rule`, operatore, metric evaluatore i rule evaluation service koji od telemetrije pravi care/alert odluke. |
| `apps.integrations` | Owner-side B2B integracije, outbox pipeline, provider konekcije, HMAC kljucevi, engagement lifecycle, sync run/checkpoint/item i payload mapping ka providerima. |
| `apps.provider_ops` | Provider-side operativni sistem. Drzi spoljne kopije owner lokacija/uredjaja/telemetrije, provider taskove, SLA, escalation, realtime evente, inbound HMAC kljuceve, idempotency i B2B API. |
| `apps.notifications` | Alert lifecycle i delivery outbox za notifikacije. Drzi alert, alert event log, notification outbox, delivery attempts, preferences, email destinations i push tokene. |
| `apps.billing` | Subscription, planovi, invoice-i i billing event log. Predvidjeno za Stripe i tenant billing lifecycle. |
| `apps.audit` | Append-only audit log za tenant akcije. Cuva actor, akciju, target type/id i metadata. |

## Scaffold / Neaktivne Django Aplikacije

Sledeci folderi postoje pod `backend/apps`, ali nisu trenutno navedeni u
`SHARED_APPS` ili `TENANT_APPS` u `backend/config/settings/base.py`. To znaci da
ih Django runtime trenutno ne migrira/ucitava kao aktivne app-ove, osim ako se
settings ne prosire.

| App | Sta predstavlja | Napomena |
| --- | --- | --- |
| `apps.planters` | Fizicka zardinjera/kontejner koji moze imati biljku i uredjaj. Model `Planter` ima material, status, lokaciju, device i inventory code. | Korisno kao novi jasniji domen izmedju `plants`, `pots` i `devices`, ali jos nije aktiviran u settings. |
| `apps.tasks` | Opsti taskovi za negu: zalivanje, provera uredjaja, baterija, rezidba, presadjivanje itd. | Preklapa se delimicno sa `provider_ops.ProviderTask`; treba odluciti da li je ovo owner/internal task domen. |
| `apps.automation` | Automation rules i execution log za trigger/action tokove. | Predvidjeno za pravila tipa alert-created, telemetry-threshold i schedule, ali nije aktivno u tenant apps. |
| `apps.firmware` | Firmware versioning, OTA deployment tracking i legacy firmware update model. | Logicno pripada device control plane-u, ali trenutno nije u `TENANT_APPS`. |
| `apps.users` | Alternativni custom user model sa ulogama admin/gardener/expert. | Potencijalno stariji ili alternativni identity model; aktivni runtime koristi `apps.identity.User`. |

## Glavni Backend Tokovi

### Owner IoT Tok

1. `devices` registruje i aktivira uredjaj.
2. Uredjaj salje MQTT/HTTP telemetriju.
3. `telemetry` validira payload i cuva `SensorReading`.
4. `care_engine` evaluira pravila nad ocitavanjem.
5. `notifications` i/ili `alerts` kreiraju alert/event zapise.
6. `integrations` moze da napravi outbox event za provider sync.

### Owner To Provider B2B Tok

1. Owner konfigurise `ProviderConnection`, `ProviderKey` i `ProviderEngagement`.
2. Owner-side promene proizvode `IntegrationOutbox` zapise.
3. Celery taskovi iz `integrations.tasks` isporucuju evente ili pokrecu sync.
4. Provider prima podatke preko `provider_ops` B2B API-ja.
5. Provider cuva kopije u `ExternalLocation`, `ExternalDevice`, `TelemetryIngest`.
6. Provider task workflow i SLA engine rade nad provider-side kopijama.

### Provider Operator Tok

1. `provider_ops` drzi `ProviderTask`, evente, note i SLA.
2. `provider_ops.api` daje list/detail/action/delta/replay endpoint-e.
3. ASGI websocket routing ide kroz `apps.provider_ops.realtime`.
4. Mobile app koristi REST + WebSocket + lokalni offline storage.

### Notification Tok

1. Alert service otvara ili menja alert.
2. `NotificationOutbox` dobija pending delivery zapis.
3. Celery notification taskovi salju kroz routing/delivery provider.
4. `NotificationDelivery` cuva attempt i provider response.

## API Povrsina

Glavni URL-ovi se nalaze u `backend/config/urls.py`.

| Prefix | App |
| --- | --- |
| `/health/`, `/health/live/`, `/health/ready/`, `/metrics/` | `core` observability |
| `/admin/` | Django admin |
| `/ui-kit/` | Django UI kit |
| `/api/schema/`, `/api/docs/`, `/api/redoc/` | OpenAPI/DRF Spectacular |
| `/api/b2b/v1/` | `provider_ops` B2B API |
| `/api/v1/tenancy/` | `tenancy` |
| `/api/v1/identity/` | `identity` |
| `/api/v1/locations/` | `locations` |
| `/api/v1/plants/` | `plants` |
| `/api/v1/pots/` | `pots` |
| `/api/v1/devices/` | `devices` |
| `/api/v1/telemetry/` | `telemetry` |
| `/api/v1/care-engine/` | `care_engine` |
| `/api/v1/integrations/` | `integrations` |
| `/api/v1/provider-ops/` | `provider_ops` |
| `/api/v1/marketplace/` | `marketplace` |
| `/api/v1/notifications/` | `notifications` |
| `/api/v1/billing/` | `billing` |
| `/api/v1/audit/` | `audit` |

## Frontend

`frontend/` je Vite + React projekat. Trenutno je najvise UI kit / design
system shell, ne puna poslovna aplikacija.

| Deo | Zaduzenje |
| --- | --- |
| `frontend/src/App.tsx` | Ulaz u React UI kit. |
| `frontend/src/ui-kit/UIKit.tsx` | Demo/pregled komponenti, layout, KPI kartice, tokeni, forme, tabele i statusi. |
| `frontend/src/components/ui/` | Shared React UI komponente: `Button`, `Badge`, `StatusBadge`, `KpiCard`, `Alert`, `Meter`. |
| `frontend/src/styles/flower-ui.css` | React entrypoint koji importuje canonical CSS iz `backend/static/css/flower-ui.css`. |
| `frontend/src/i18n/` | i18next setup i prevodi za `sr-Latn`, `sr-Cyrl`, `sr`, `en`. |
| `frontend/src/modules/` | Placeholder moduli za buduce ekrane: dashboard, expert, realtime. |

## Django UI Templates

| Deo | Zaduzenje |
| --- | --- |
| `backend/templates/base.html` | Osnovni HTML shell za Django-rendered strane. |
| `backend/templates/app_base.html` | App shell sa topbar/sidebar layout-om. |
| `backend/templates/dashboard/index.html` | Operativni dashboard. |
| `backend/templates/ui_kit/index.html` | Django/HTMX UI kit pregled. |
| `backend/templates/partials/` | Reusable partials: sidebar, topbar, status badge, UI feedback. |
| `backend/static/css/flower-ui.css` | Canonical design system CSS koji dele Django templates i React frontend. |

## Mobile

`mobile/provider_app/` je Flutter provider operations app. Dokumentacija opisuje
Clean Architecture raspored:

| Sloj | Zaduzenje |
| --- | --- |
| `presentation` | Ekrani, widgeti i Riverpod provider-i. |
| `application` | Use case-ovi i state orchestration. |
| `domain` | Entiteti, repository interfejsi i value objects. |
| `infrastructure` | API clients, local DB, realtime, sync i auth implementacije. |
| `core` | Network, storage i error handling. |

Mobile app je namenjen provider operaterima: task list/detail, assign/start/
complete/cancel, notes, delta sync, offline UX i WebSocket realtime updates.

## Infra

| Deo | Zaduzenje |
| --- | --- |
| `docker-compose.yml` | Lokalni stack: Redis, MQTT, backend, Celery worker, nginx. |
| `infra/docker/backend/Dockerfile` | Backend image za development/production targete. |
| `infra/docker/frontend/Dockerfile` | Frontend build/runtime image. |
| `infra/mosquitto/mosquitto.conf` | MQTT broker konfiguracija. |
| `infra/nginx/nginx.conf` | Backend/static/media reverse proxy config. |
| `infra/nginx/frontend.conf` | Frontend nginx config. |
| `infra/prometheus/prometheus.yml` | Prometheus scraping konfiguracija. |
| `infra/grafana/` | Placeholder za dashboard provisioning. |
| `infra/postgres/init/` | Placeholder za Postgres init skripte. |

## Granice Odgovornosti

- `devices` ne treba da cuva poslovna pravila nege; to pripada `care_engine`.
- `telemetry` treba da cuva i validira ocitavanja, ali evaluaciju alert/care
  pravila treba delegirati u `care_engine`.
- `integrations` je owner/outbound strana B2B price; `provider_ops` je
  provider/inbound i operator workflow strana.
- `notifications` je delivery i alert lifecycle sistem; ako `alerts` ostaje kao
  novi domen, treba jasno odluciti da li zamenjuje ili dopunjuje
  `notifications.Alert`.
- `marketplace` je public discovery/commerce domen, ne provider task runtime.
- `billing` je tenant subscription i invoice domen, ne marketplace order domen.
- `audit` je append-only forenzicki log; ne treba ga koristiti kao generalni
  event bus.

## Otvorena Arhitektonska Pitanja

1. Da li `apps.alerts` treba da zameni alert modele u `apps.notifications`, ili
   su to dva razlicita nivoa: alert rules u `alerts`, delivery/lifecycle u
   `notifications`?
2. Da li `apps.planters`, `apps.tasks`, `apps.automation`, `apps.firmware` i
   `apps.users` treba aktivirati u `TENANT_APPS`, ili su ostaci/scaffold za
   kasniju fazu?
3. Da li `pots` ostaje canonical naziv za fizicku posudu, ili se prelazi na
   `planters` kao jasniji domen?
4. Da li opsti `tasks.Task` treba da postoji paralelno sa
   `provider_ops.ProviderTask`, ili owner/internal taskovi treba da imaju
   sopstven bounded context sa eksplicitnom integracijom ka provider taskovima?
5. Da li frontend treba da ostane UI kit dok Django templates nose app shell,
   ili React preuzima konkretne dashboard/module ekrane?
