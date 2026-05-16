# Governance Rules

These rules are non-negotiable. Violations must be caught in code review.

## 1. Tenant Isolation — Fail-Closed

- If a request cannot be resolved to a tenant, it MUST be rejected.
- Never default to the public schema for tenant-scoped data.
- Background jobs MUST use `tenant_context()` explicitly.
- No hardcoded tenant IDs in code.

## 2. Service-Only Writes

- All model mutations MUST go through `services.py`.
- No direct `Model.objects.create()`, `update()`, or `delete()` outside services.
- Services MUST use keyword-only arguments (`*`).
- Services MUST return the mutated entity or nothing.

## 3. Selector-Only Reads

- All queries MUST go through `selectors.py`.
- No direct `Model.objects.filter()` outside selectors.
- Selectors MUST use keyword-only arguments.
- Selectors MUST return QuerySets or single instances.

## 4. Append-Only Measurements

- `RawReading` records are NEVER updated or deleted.
- If data is bad, mark it with a `is_invalid` flag; do not remove it.
- This preserves the audit trail of what the device actually sent.

## 5. Append-Only Alert Events

- Alerts are facts. They happened.
- Do not update an alert to "resolve" it.
- Create a new `AlertResolution` record instead.

## 6. Audit for Manual Actions

- Every manual action by a user MUST be logged in `audit.AuditLog`.
- Automated system actions do NOT need audit logs.
- Audit logs are append-only.

## 7. No Cross-Tenant Lookups

- Queries MUST NEVER span tenant schemas.
- If you need data from another tenant, use a well-defined API or event.
- The `public` schema is the only shared space.

## 8. No Direct Writes Outside Service Layer

- Admin actions that mutate data MUST use services.
- DRF viewsets MUST use services for create/update/delete.
- Celery tasks MUST use services.
- Management commands MUST use services.

## 9. Model Translation

- All user-facing model fields MUST use `django-modeltranslation`.
- Translatable fields MUST be defined in `translation.py` per app.
- Default language is Serbian (`sr`).

## 10. Rule Operators Are Centrally Defined

- All comparison operators MUST be defined in `RuleOperator` (`care_engine/models/rule.py`).
- No ad-hoc operator strings in services or views.
- New operators MUST be added to both `RuleOperator.choices` and `_OPERATOR_FUNCTIONS`.
- Operator evaluation MUST go through `evaluate_operator()`.

## 11. Alert Lifecycle Is Immutable

- Alert status MUST NEVER be mutated directly outside `notifications.services.alert_service`.
- `RESOLVED` and `DISMISSED` are terminal — no outgoing transitions.
- `SUPPRESSED` alerts MUST NOT generate notifications.
- Duplicate OPEN alerts for the same `rule + device` MUST be prevented.

## 12. Alert Events Are Append-Only

- `AlertEvent` records MUST NEVER be updated or deleted.
- No `updated_at` field on `AlertEvent` — only `created_at`.
- Each status transition MUST record a corresponding `AlertEvent`.

## 13. Security

- No secrets in code.
- All configuration MUST come from environment variables.
- `DEBUG=False` in production.
- `SECURE_SSL_REDIRECT=True` in production.
- CORS origins MUST be explicitly whitelisted.
