# Billing Architecture

Phase 21 adds subscription billing, invoice management, Stripe integration,
and feature-gated tenant limits.

## Models

| Model | Purpose |
|-------|---------|
| `SubscriptionPlan` | System-defined plan (code, price, features, limits) |
| `TenantSubscription` | A tenant's active or past subscription |
| `Invoice` | Billing invoice for a tenant |
| `BillingEvent` | Audit log for billing events |

## Subscription Lifecycle

```
TRIALING ──→ ACTIVE ──→ PAST_DUE ──→ EXPIRED (terminal)
  │            │
  └──→ ACTIVE  └──→ CANCELLED (terminal)
  (trial end)
```

## Invoice Lifecycle

```
DRAFT ──→ OPEN ──→ PAID (terminal)
  │           │
  │           ├──→ VOID (terminal)
  │           └──→ UNCOLLECTIBLE ──→ OPEN (retry)
  └──→ VOID (direct)
```

## Stripe Abstraction

All Stripe calls go through `BillingProvider` protocol:

| Method | Stripe API |
|--------|------------|
| `create_customer()` | `stripe.Customer.create` |
| `create_subscription()` | `stripe.Subscription.create` |
| `cancel_subscription()` | `stripe.Subscription.delete` |
| `create_checkout_session()` | `stripe.checkout.Session.create` |
| `fetch_invoice()` | `stripe.Invoice.retrieve` |
| `handle_webhook()` | `stripe.Webhook.construct_event` |

## Feature Gating

Limits enforced via `SubscriptionPlan` fields:

| Limit | Enforced on |
|-------|-------------|
| `max_devices` | Device creation |
| `max_users` | User creation |
| `max_locations` | Location creation |

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/billing/v1/plans/` | List subscription plans |
| GET | `/api/billing/v1/subscription/` | Get tenant subscription |
| POST | `/api/billing/v1/checkout/` | Create Stripe checkout session |
| POST | `/api/billing/v1/subscription/cancel/` | Cancel subscription |
| GET | `/api/billing/v1/invoices/` | List tenant invoices |
| POST | `/api/billing/v1/webhooks/stripe/` | Stripe webhook receiver |
