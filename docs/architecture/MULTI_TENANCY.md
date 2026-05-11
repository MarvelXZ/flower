# Multi-Tenancy

Flower uses django-tenants with PostgreSQL schemas.

The public schema contains tenant bootstrap data, tenant domains, and marketplace discovery records. It must not store sensitive integration secrets unless there is no safe tenant-local alternative.

Owner schemas contain canonical operational data: locations, plants, pots, devices, telemetry, care evaluations, alerts, and integration configuration. MQTT ingest is routed into the owner schema.

Provider schemas contain provider-owned workflows and synchronized external copies of permitted owner data. Providers do not read owner schemas directly. All provider access is mediated by B2B APIs, outbox delivery, and explicit synchronization checkpoints.

Hybrid tenants can act as both owner and provider. They still use the same isolation rules: owner-side data is canonical for assets they own, and provider-side data is a copy for assets they service.

Marketplace admin tenants operate shared discovery and governance workflows without becoming a backdoor into tenant schemas.
