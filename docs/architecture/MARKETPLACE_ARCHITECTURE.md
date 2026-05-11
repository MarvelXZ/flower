# Marketplace Architecture

Phase 21 adds the marketplace foundation that allows provider tenants to
offer services/subscriptions/products to owner tenants.

## Models

| Model | Schema | Purpose |
|-------|--------|---------|
| `ProviderListing` | Public | A service/product offered by a provider |
| `ProviderServiceArea` | Public | Geographic coverage for a listing |
| `ProviderListingMedia` | Public | Images/documents for a listing |
| `MarketplaceOffer` | Public | An owner's offer on a listing |
| `ServiceOrder` | Public | An order placed for a service |

## Listing Lifecycle

```
DRAFT ──→ ACTIVE ──→ PAUSED ──→ ACTIVE (resume)
  │         │
  └──→ ARCHIVED (terminal)
  │
  ACTIVE ──→ ARCHIVED (terminal)
  PAUSED  ──→ ARCHIVED (terminal)
```

## Offer Lifecycle

```
PENDING ──→ ACCEPTED (terminal)
  │
  ├──→ REJECTED (terminal)
  ├──→ CANCELLED (terminal)
  └──→ EXPIRED (terminal)
```

## Service Order Lifecycle

```
PENDING ──→ CONFIRMED ──→ IN_PROGRESS ──→ COMPLETED (terminal)
  │
  └──→ CANCELLED (terminal)
```
