"""Abstract billing provider interface — Stripe is behind this abstraction."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class BillingProviderResult:
    success: bool = True
    error: str = ""
    provider_id: str = ""
    provider_data: dict = field(default_factory=dict)


class BillingProvider(Protocol):
    def create_customer(self, *, tenant_id: str, email: str = "") -> BillingProviderResult:
        ...

    def create_subscription(self, *, customer_id: str, price_id: str) -> BillingProviderResult:
        ...

    def cancel_subscription(self, *, subscription_id: str) -> BillingProviderResult:
        ...

    def create_checkout_session(self, *, customer_id: str, price_id: str, success_url: str, cancel_url: str) -> BillingProviderResult:
        ...

    def fetch_invoice(self, *, invoice_id: str) -> BillingProviderResult:
        ...

    def handle_webhook(self, *, payload: bytes, signature: str) -> BillingProviderResult:
        ...
