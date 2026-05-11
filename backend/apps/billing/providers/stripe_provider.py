"""Real Stripe billing provider — isolated behind BillingProvider abstraction."""

import logging

from django.conf import settings

from apps.billing.providers.base import BillingProviderResult

logger = logging.getLogger(__name__)

try:
    import stripe
    _STRIPE_AVAILABLE = True
except ImportError:
    _STRIPE_AVAILABLE = False
    stripe = None


class StripeBillingProvider:
    """Stripe-backed billing provider.

    Requires ``stripe`` Python package and ``STRIPE_SECRET_KEY`` setting.
    Falls back to mock-like behavior when Stripe is not configured.
    """

    def __init__(self):
        self._enabled = getattr(settings, "STRIPE_ENABLED", False) and _STRIPE_AVAILABLE
        if self._enabled:
            stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")

    def create_customer(self, *, tenant_id: str, email: str = "") -> BillingProviderResult:
        if not self._enabled:
            return BillingProviderResult(success=False, error="Stripe not enabled.")
        try:
            customer = stripe.Customer.create(metadata={"tenant_id": tenant_id}, email=email)
            return BillingProviderResult(success=True, provider_id=customer.id)
        except Exception as exc:
            logger.warning("stripe_create_customer_failed", extra={"error": str(exc)[:200]})
            return BillingProviderResult(success=False, error=str(exc)[:500])

    def create_subscription(self, *, customer_id: str, price_id: str) -> BillingProviderResult:
        if not self._enabled:
            return BillingProviderResult(success=False, error="Stripe not enabled.")
        try:
            sub = stripe.Subscription.create(customer=customer_id, items=[{"price": price_id}])
            return BillingProviderResult(success=True, provider_id=sub.id)
        except Exception as exc:
            logger.warning("stripe_create_subscription_failed", extra={"error": str(exc)[:200]})
            return BillingProviderResult(success=False, error=str(exc)[:500])

    def cancel_subscription(self, *, subscription_id: str) -> BillingProviderResult:
        if not self._enabled:
            return BillingProviderResult(success=False, error="Stripe not enabled.")
        try:
            stripe.Subscription.delete(subscription_id)
            return BillingProviderResult(success=True)
        except Exception as exc:
            return BillingProviderResult(success=False, error=str(exc)[:500])

    def create_checkout_session(self, *, customer_id: str, price_id: str, success_url: str, cancel_url: str) -> BillingProviderResult:
        if not self._enabled:
            return BillingProviderResult(success=False, error="Stripe not enabled.")
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return BillingProviderResult(success=True, provider_data={"url": session.url, "id": session.id})
        except Exception as exc:
            return BillingProviderResult(success=False, error=str(exc)[:500])

    def fetch_invoice(self, *, invoice_id: str) -> BillingProviderResult:
        if not self._enabled:
            return BillingProviderResult(success=False, error="Stripe not enabled.")
        try:
            inv = stripe.Invoice.retrieve(invoice_id)
            return BillingProviderResult(success=True, provider_data=dict(inv))
        except Exception as exc:
            return BillingProviderResult(success=False, error=str(exc)[:500])

    def handle_webhook(self, *, payload: bytes, signature: str) -> BillingProviderResult:
        if not self._enabled:
            return BillingProviderResult(success=False, error="Stripe not enabled.")
        try:
            secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
            event = stripe.Webhook.construct_event(payload, signature, secret)
            return BillingProviderResult(success=True, provider_data={"type": event.type, "id": event.id})
        except Exception as exc:
            return BillingProviderResult(success=False, error=str(exc)[:500])
