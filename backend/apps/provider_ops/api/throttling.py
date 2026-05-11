"""DRF throttling rates for the provider dashboard API.

B2B endpoints use separate HMAC-based auth and are not throttled here.
"""

from rest_framework.throttling import UserRateThrottle


class ProviderBurstThrottle(UserRateThrottle):
    """60 requests per minute per authenticated user."""

    scope = "provider_burst"
    rate = "60/min"


class ProviderSustainedThrottle(UserRateThrottle):
    """1000 requests per day per authenticated user."""

    scope = "provider_sustained"
    rate = "1000/day"
