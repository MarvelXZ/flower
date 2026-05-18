# Tenant Onboarding

Tenant onboarding je pocetni business flow za firmu koja ulazi u Flower.

## Osnovno Pravilo

Svaka firma koja koristi Flower kao vlasnik podataka je zaseban tenant.

Primeri:

- hotel koji je kupio pametne saksije je `owner` tenant,
- servisna firma koja odrzava tudje biljke je `provider` tenant,
- firma koja ima svoje biljke i odrzava tudje biljke je `hybrid` tenant,
- Flower interna/platform firma moze biti `marketplace_admin` ili `hybrid`,
  zavisno od uloge.

Kupac koji je samo lead/prospect moze biti CRM record u buducnosti, ali firma
koja ima korisnike, uredjaje, lokacije ili telemetriju mora biti tenant.

## Prvi Implementirani Slice

HTML views:

```text
GET  /tenants/
GET  /tenants/new/
POST /tenants/new/
GET  /tenants/<id>/edit/
POST /tenants/<id>/edit/
```

Ovi Django template ekrani su namenjeni staff/platform korisnicima. Koriste
server-rendered CRUD pristup, jer je tenant onboarding interni operativni flow.

Endpoint:

```text
GET  /api/v1/tenancy/tenants/
POST /api/v1/tenancy/tenants/
```

`POST` kreira:

- `tenancy.Client`
- primary `tenancy.Domain`
- tenant schema kroz `django-tenants` `auto_create_schema`

Minimalni payload:

```json
{
  "name": "Hotel Magnolia",
  "slug": "hotel-magnolia",
  "schema_name": "hotel_magnolia",
  "domain": "hotel-magnolia.localhost",
  "kind": "owner"
}
```

Dozvoljeni `kind`:

- `owner`
- `provider`
- `hybrid`
- `marketplace_admin`

## Sledece Faze

### Phase 2: Initial Admin User

Onboarding treba da kreira prvog korisnika u tenant schema:

- ime/prezime,
- email,
- role,
- temporary password ili invite token,
- language/timezone.

### Phase 3: Billing

Onboarding treba da poveze tenant sa billing modelima:

- `billing.SubscriptionPlan`,
- `billing.TenantSubscription`,
- Stripe customer/subscription kada provider nije mock.

### Phase 4: Provider Engagement

Ako tenant odmah dobija servisnog providera:

- kreirati `integrations.ProviderEngagement`,
- kreirati owner-side `ProviderConnection`,
- pripremiti HMAC key lifecycle,
- na provider strani registrovati inbound key.

### Phase 5: Starter Configuration

Za owner tenant:

- pocetna lokacija,
- prvi device batch,
- default care rules,
- default notification preferences.

Za provider tenant:

- service areas,
- marketplace profile,
- task/SLA policy defaults.

## Granica Odgovornosti

`tenancy` je zaduzen za identitet tenant-a i domain/schema lifecycle.

`tenancy` ne treba da zna detalje:

- invoice-a,
- marketplace order-a,
- device provisioning-a,
- provider taskova,
- telemetry-ja.

Umesto toga, onboarding orchestration moze pozvati druge bounded context service
funkcije nakon sto je osnovni tenant kreiran.
