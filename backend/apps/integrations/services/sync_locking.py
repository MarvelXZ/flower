"""Transaction-safe sync locking for engagement-level mutual exclusion.

Ensures that at most one sync run can be active per engagement at any
time.  Uses a combination of a database query (no active running/pending
runs) and ``select_for_update`` for transaction safety.
"""


from django.db import transaction

from apps.integrations.domain.enums import SyncRunStatus
from apps.integrations.models import ProviderEngagement, SyncRun


class SyncLockError(RuntimeError):
    """Raised when a sync lock cannot be acquired."""


def has_running_sync(*, engagement: ProviderEngagement) -> bool:
    """Return ``True`` if the engagement already has a non-terminal sync run."""
    return SyncRun.objects.filter(
        engagement=engagement,
        status__in={SyncRunStatus.PENDING, SyncRunStatus.RUNNING},
    ).exists()


def acquire_sync_lock(*, engagement: ProviderEngagement, timeout_seconds: int = 30) -> None:
    """Acquire an engagement-level sync lock.

    Raises ``SyncLockError`` if a non-terminal sync run already exists for
    this engagement.

    Uses ``select_for_update`` on the engagement row inside a transaction
    to serialise concurrent lock attempts.
    """
    with transaction.atomic():
        # Lock the engagement row to serialise concurrent attempts.
        locked = ProviderEngagement.objects.select_for_update().get(pk=engagement.pk)

        active = SyncRun.objects.filter(
            engagement=locked,
            status__in={SyncRunStatus.PENDING, SyncRunStatus.RUNNING},
        ).exists()

        if active:
            raise SyncLockError(
                f"Engagement '{engagement}' already has a non-terminal sync run.",
            )


def release_sync_lock(*, engagement: ProviderEngagement) -> None:
    """Release the implicit sync lock.

    In this implementation the lock is held by the transaction boundary
    (``select_for_update``), so "release" is a no-op — the lock is freed
    when the transaction commits or rolls back.

    This function exists as a placeholder for future lock implementations
    (e.g. Redis-based advisory locks).
    """
    pass
