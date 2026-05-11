# Audit Checklist

- Does the change preserve tenant isolation?
- Are all writes routed through the relevant service layer?
- Are reads centralized in selectors when query behavior is non-trivial?
- Does provider-facing behavior avoid direct owner-schema reads?
- Are integration secrets stored tenant-locally and encrypted when implemented?
- Are outbox records created for cross-tenant/provider delivery?
- Are idempotency keys used for external delivery?
- Are user-facing labels and choices wrapped with `gettext_lazy`?
- Are new models imported from `models/__init__.py`?
- Are tests placed in the owning bounded context or top-level startup suite?
