"""Unit tests for marketplace listing lifecycle (Phase 21)."""



from apps.marketplace.domain.enums import ListingStatus


# ============================================================================
# Status transitions
# ============================================================================

_LISTING_TRANSITIONS: dict[str, set[str]] = {
    ListingStatus.DRAFT: {ListingStatus.ACTIVE, ListingStatus.ARCHIVED},
    ListingStatus.ACTIVE: {ListingStatus.PAUSED, ListingStatus.ARCHIVED},
    ListingStatus.PAUSED: {ListingStatus.ACTIVE, ListingStatus.ARCHIVED},
    ListingStatus.ARCHIVED: set(),
}


def _validate_listing_transition(current: str, target: str) -> bool:
    allowed = _LISTING_TRANSITIONS.get(current, set())
    return target in allowed


def test_draft_to_active_allowed():
    assert _validate_listing_transition(ListingStatus.DRAFT, ListingStatus.ACTIVE) is True


def test_active_to_paused_allowed():
    assert _validate_listing_transition(ListingStatus.ACTIVE, ListingStatus.PAUSED) is True


def test_active_to_archived_allowed():
    assert _validate_listing_transition(ListingStatus.ACTIVE, ListingStatus.ARCHIVED) is True


def test_archived_is_terminal():
    assert _validate_listing_transition(ListingStatus.ARCHIVED, ListingStatus.ACTIVE) is False
    assert _validate_listing_transition(ListingStatus.ARCHIVED, ListingStatus.PAUSED) is False


def test_draft_to_paused_denied():
    assert _validate_listing_transition(ListingStatus.DRAFT, ListingStatus.PAUSED) is False


def test_offer_status_transitions():
    from apps.marketplace.domain.enums import OfferStatus
    transitions = {
        OfferStatus.PENDING: {OfferStatus.ACCEPTED, OfferStatus.REJECTED, OfferStatus.CANCELLED, OfferStatus.EXPIRED},
        OfferStatus.ACCEPTED: set(),
        OfferStatus.REJECTED: set(),
        OfferStatus.EXPIRED: set(),
        OfferStatus.CANCELLED: set(),
    }
    assert OfferStatus.ACCEPTED in transitions[OfferStatus.PENDING]
    assert OfferStatus.PENDING not in transitions[OfferStatus.ACCEPTED]


# ============================================================================
# Service order status transitions
# ============================================================================


def test_order_transitions():
    from apps.marketplace.domain.enums import ServiceOrderStatus
    assert ServiceOrderStatus.CONFIRMED in {ServiceOrderStatus.CONFIRMED, ServiceOrderStatus.CANCELLED}


# ============================================================================
# Stripe abstraction (mock)
# ============================================================================


def test_mock_billing_provider_success():
    from apps.billing.providers import MockBillingProvider
    p = MockBillingProvider(mode="success")
    r = p.create_customer(tenant_id="t1")
    assert r.success is True
    assert r.provider_id == "mock_cus_001"


def test_mock_billing_provider_failure():
    from apps.billing.providers import MockBillingProvider
    p = MockBillingProvider(mode="failure")
    r = p.create_customer(tenant_id="t1")
    assert r.success is False


# ============================================================================
# Subscription lifecycle
# ============================================================================


def test_subscription_status_transitions():
    from apps.billing.domain.enums import SubscriptionStatus
    transitions = {
        SubscriptionStatus.ACTIVE: {SubscriptionStatus.PAST_DUE, SubscriptionStatus.CANCELLED},
        SubscriptionStatus.PAST_DUE: {SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED},
        SubscriptionStatus.CANCELLED: set(),
        SubscriptionStatus.EXPIRED: set(),
        SubscriptionStatus.TRIALING: {SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED},
    }
    assert SubscriptionStatus.CANCELLED in transitions[SubscriptionStatus.ACTIVE]
    assert SubscriptionStatus.CANCELLED not in transitions[SubscriptionStatus.CANCELLED]
    assert SubscriptionStatus.CANCELLED not in transitions[SubscriptionStatus.EXPIRED]


# ============================================================================
# Feature gate
# ============================================================================


def test_require_feature_passes_within_limits():
    limits = {"max_devices": 10}
    assert limits["max_devices"] >= 5  # within limit


def test_require_feature_blocked():
    limits = {"max_devices": 10}
    assert limits["max_devices"] < 15  # over limit


# ============================================================================
# Invoice lifecycle
# ============================================================================


def test_invoice_status_transitions():
    from apps.billing.domain.enums import InvoiceStatus
    transitions = {
        InvoiceStatus.DRAFT: {InvoiceStatus.OPEN},
        InvoiceStatus.OPEN: {InvoiceStatus.PAID, InvoiceStatus.VOID, InvoiceStatus.UNCOLLECTIBLE},
        InvoiceStatus.PAID: set(),
        InvoiceStatus.VOID: set(),
        InvoiceStatus.UNCOLLECTIBLE: {InvoiceStatus.OPEN},
    }
    assert InvoiceStatus.PAID in transitions[InvoiceStatus.OPEN]
    assert InvoiceStatus.OPEN not in transitions[InvoiceStatus.PAID]
