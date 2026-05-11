# Repository Cleanup & Architecture Alignment Audit

**Date:** 2026-05-11  
**Scope:** Full repository audit (backend, docs, infra, mobile)  
**Author:** Automated audit

## Executive Summary

The repository is in **good structural health**. One critical finding (duplicate `tenants` app), a handful of stale documentation references, and no orphan code of significance. No business logic was changed.

## App Map

| App | Status | Migrations | Notes |
|-----|--------|------------|-------|
| `tenancy` | ✅ Active | 0001 | Canonical tenant model (`TENANT_MODEL = "tenancy.Client"`) |
| `tenants` | ❌ Orphan | **None** | Duplicate; not in INSTALLED_APPS |
| `core` | ✅ Active | — | Shared utilities, middleware, metrics |
| `identity` | ✅ Active | Has migrations | Users, auth, mobile sessions |
| `devices` | ✅ Active | Has migrations | IoT device management |
| `telemetry` | ✅ Active | Has migrations | Sensor readings |
| `plants` | ✅ Active | Has migrations | Plant instances |
| `notifications` | ✅ Active | 0004 migrations | Alerts, notification outbox, push tokens |
| `provider_ops` | ✅ Active | 0005 migrations | Tasks, SLA, realtime, inbound keys |
| `integrations` | ✅ Active | 0008 migrations | Outbox, sync, engagement, HMAC |
| `care_engine` | ✅ Active | Has migrations | Rule evaluation, plant species |
| `marketplace` | ✅ Active | 0002 migrations | Listings, offers, orders |
| `billing` | ✅ Active | Has migrations | Plans, subscriptions, invoices |
| `audit` | ✅ Active | Has migrations | Audit logs |
| `locations` | ✅ Active | Has migrations | Location management |
| `pots` | ✅ Active | Has migrations | Pot management |
| `billing` (legacy) | ✅ Active | Has migrations | Invoice/subscription models |

## Tenancy vs Tenants — Final Verdict

| Check | `apps.tenancy` | `apps.tenants` |
|-------|----------------|----------------|
| In `SHARED_APPS` | ✅ Yes | ❌ No |
| `TENANT_MODEL` | ✅ `tenancy.Client` | ❌ Not referenced |
| Migrations | ✅ `0001_initial.py` | ❌ `__init__.py` only |
| External refs | 15+ | **0** (except internal) |
| Management commands | ✅ `create_demo_tenants` | ❌ None |
| Domain enums | ✅ `TenantKind` | ❌ None |
| Tests | ✅ `test_tenant_foundation.py` | ❌ None |
| Documentation | ✅ `TENANT_BOOTSTRAP.md` | ❌ Stale refs |

### Decision

**Keep:** `apps.tenancy` — this is the canonical tenant app.  
**Remove:** `apps.tenants` — safe to delete; no external references, no migrations, not in INSTALLED_APPS.

## Files Removed

| File | Reason |
|------|--------|
| `backend/apps/tenants/` (entire directory) | Duplicate of `tenancy`; zero external references |
| — 9 files total (models.py, services.py, selectors.py, admin.py, apps.py, events.py, \_\_init\_\_.py, tests/\_\_init\_\_.py, migrations/\_\_init\_\_.py) | |

## Files Kept (Intentional)

| File | Reason |
|------|--------|
| `backend/apps/tenancy/` | Canonical tenant implementation |
| Empty `__init__.py` in migration directories | Required by Django |
| `infra/grafana/.gitkeep` | Preserves folder structure |
| Placeholder files in test dirs | Reserved for future tests |

## Documentation Updated

| File | Change |
|------|--------|
| `backend/docs/architecture/MULTI_TENANCY.md` | Replaced `apps.tenants` references → `apps.tenancy` |

## Risks

None. The `tenants` app had zero external references and no migrations. Removal is safe.

## Follow-up Tasks (Manual)

| Task | Priority |
|------|----------|
| Verify no CI/CD pipeline references `apps.tenants` | Low |
| Verify no Docker/k8s config references `tenants` | Low |
| Add `apps.tenancy` → documentation link in MULTI_TENANCY.md | Done |
