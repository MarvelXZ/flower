"""Mock billing provider for testing."""

from apps.billing.providers.base import BillingProviderResult


class MockBillingProvider:
    """Mock provider that always succeeds."""

    def __init__(self, mode: str = "success"):
        self.mode = mode

    def create_customer(self, *, tenant_id: str, email: str = "") -> BillingProviderResult:
        if self.mode == "failure":
            return BillingProviderResult(success=False, error="Mock failure")
        return BillingProviderResult(success=True, provider_id="mock_cus_001")

    def create_subscription(self, *, customer_id: str, price_id: str) -> BillingProviderResult:
        if self.mode == "failure":
            return BillingProviderResult(success=False, error="Mock failure")
        return BillingProviderResult(success=True, provider_id="mock_sub_001")

    def cancel_subscription(self, *, subscription_id: str) -> BillingProviderResult:
        return BillingProviderResult(success=True)

    def create_checkout_session(self, *, customer_id: str, price_id: str, success_url: str, cancel_url: str) -> BillingProviderResult:
        return BillingProviderResult(success=True, provider_data={"url": "https://checkout.example.com"})

    def fetch_invoice(self, *, invoice_id: str) -> BillingProviderResult:
        return BillingProviderResult(success=True, provider_data={"amount_due": 2999})

    def handle_webhook(self, *, payload: bytes, signature: str) -> BillingProviderResult:
        return BillingProviderResult(success=True, provider_data={"type": "invoice.paid"})
