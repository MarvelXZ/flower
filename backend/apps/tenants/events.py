"""
Tenant domain events.

Events are lightweight dataclasses representing something that happened
in the domain. They are NOT Django signals — they are meant for the
outbox pattern or event bus integration.

Example flow:
    1. Domain action occurs.
    2. Service emits an event.
    3. Event is persisted to an outbox table (same transaction).
    4. Background processor publishes to message bus.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TenantCreated:
    """Emitted when a new tenant is provisioned."""

    tenant_id: int
    slug: str
    schema_name: str
    occurred_at: datetime


@dataclass(frozen=True)
class TenantDeactivated:
    """Emitted when a tenant is soft-deactivated."""

    tenant_id: int
    slug: str
    occurred_at: datetime
