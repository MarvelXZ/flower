# Stripe Integration

## Architecture

```
Flower Backend                    Stripe
     │                              │
     ├── BillingProvider (protocol) │
     │     ├── MockBillingProvider  │  (no external API)
     │     └── StripeBillingProvider│──→ stripe.com
     │                                │
     │  create_customer()            │──→ Customer.create
     │  create_subscription()        │──→ Subscription.create
     │  cancel_subscription()        │──→ Subscription.delete
     │  create_checkout_session()    │──→ Checkout.Session.create
     │  fetch_invoice()              │──→ Invoice.retrieve
     ├── Webhook endpoint            │
     │  POST /api/billing/v1/webhooks/stripe/
     │                                │←── stripe.Webhook.construct_event
```

## Settings

| Setting | Purpose |
|---------|---------|
| `STRIPE_ENABLED` | Enable/disable Stripe integration |
| `STRIPE_SECRET_KEY` | Stripe API secret key |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret |

When `STRIPE_ENABLED=False`, all billing operations fall back to
`MockBillingProvider` which returns success without external API calls.

## Webhook Events

| Event | Action |
|-------|--------|
| `invoice.paid` | Mark invoice as paid, update subscription |
| `invoice.payment_failed` | Mark invoice as uncollectible, move to past_due |
| `customer.subscription.deleted` | Cancel local subscription record |
| `checkout.session.completed` | Activate subscription after first payment |

## Security

- Webhook endpoint validates `stripe-signature` header
- API keys never logged
- External event IDs stored for reconciliation
- All Stripe calls go through `BillingProvider` abstraction — business layer
  never depends on Stripe SDK directly
