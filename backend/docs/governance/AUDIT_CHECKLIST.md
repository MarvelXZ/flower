# Audit Checklist

Use this checklist before every release and during security audits.

## Tenant Isolation

- [ ] Tenant middleware is active and first in `MIDDLEWARE`.
- [ ] `DATABASE_ROUTERS` includes `TenantSyncRouter`.
- [ ] No hardcoded schema names in application code.
- [ ] Background jobs use `tenant_context()`.
- [ ] No cross-tenant queries in views or selectors.

## Data Integrity

- [ ] All writes go through `services.py`.
- [ ] All reads go through `selectors.py`.
- [ ] `RawReading` is append-only (no updates/deletes).
- [ ] `Alert` is append-only (no updates/deletes).
- [ ] `AuditLog` is append-only (no updates/deletes).

## Security

- [ ] `DEBUG=False` in production settings.
- [ ] `SECRET_KEY` is loaded from environment.
- [ ] `ALLOWED_HOSTS` is explicitly configured.
- [ ] `CSRF_TRUSTED_ORIGINS` is explicitly configured.
- [ ] `SECURE_SSL_REDIRECT=True` in production.
- [ ] `SECURE_HSTS_SECONDS` is set.
- [ ] CORS origins are whitelisted.
- [ ] No secrets committed to version control.

## API

- [ ] DRF is configured with authentication.
- [ ] drf-spectacular schema is generated.
- [ ] API endpoints require authentication by default.
- [ ] No open endpoints expose sensitive data.

## Frontend

- [ ] HTMX and React boundaries are respected.
- [ ] No random mixing of technologies on the same page.
- [ ] API is the single source of truth for both frontends.

## Infrastructure

- [ ] Docker images run as non-root user.
- [ ] Health checks are configured for all services.
- [ ] PostgreSQL is version 16+.
- [ ] Redis is configured with persistence.
- [ ] RabbitMQ credentials are from environment.
- [ ] Celery worker and beat are running.

## Testing

- [ ] All bounded contexts have at least one test.
- [ ] Tenant model tests pass.
- [ ] Pytest configuration is valid.
- [ ] Coverage is above 70% for services and selectors.

## Documentation

- [ ] README is up to date.
- [ ] Architecture docs reflect current state.
- [ ] Governance rules are known to the team.
