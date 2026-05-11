"""Management command to run provider synchronisation.

Usage::

    python manage.py sync_provider --engagement=<id> --mode=full
    python manage.py sync_provider --engagement=<id> --mode=delta
    python manage.py sync_provider --engagement=<id> --mode=resync --stream=locations
    python manage.py sync_provider --engagement=<id> --mode=full --dry-run
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.integrations.models import ProviderEngagement
from apps.integrations.services.sync_engine_service import run_delta_sync, run_full_sync, run_resync
from apps.integrations.services.sync_health_service import get_engagement_sync_health
from apps.integrations.services.sync_locking import SyncLockError, acquire_sync_lock, has_running_sync
from apps.integrations.services.sync_service import SyncNotAllowed

logger = logging.getLogger(__name__)

VALID_MODES = ("full", "delta", "resync")


class Command(BaseCommand):
    help = "Run provider synchronisation for an engagement."

    def add_arguments(self, parser):
        parser.add_argument("--engagement", type=int, required=True, help="Engagement ID")
        parser.add_argument(
            "--mode",
            type=str,
            required=True,
            choices=VALID_MODES,
            help="Sync mode: full, delta, or resync",
        )
        parser.add_argument("--stream", type=str, default="", help="Stream name (required for resync)")
        parser.add_argument("--dry-run", action="store_true", help="Preview without delivery")
        parser.add_argument("--limit", type=int, default=0, help="Max events to process (0 = unlimited)")
        parser.add_argument("--verbose", action="store_true", help="Detailed output")

    def handle(self, *args, **options):
        engagement_id = options["engagement"]
        mode = options["mode"]
        stream = options["stream"]
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        try:
            engagement = ProviderEngagement.objects.get(pk=engagement_id)
        except ProviderEngagement.DoesNotExist:
            raise CommandError(f"Engagement '{engagement_id}' not found.")

        if mode == "resync" and not stream:
            raise CommandError("--stream is required for resync mode.")

        if dry_run:
            self._handle_dry_run(engagement, mode, stream, verbose)
            return

        self._execute_sync(engagement, mode, stream, verbose)

    def _handle_dry_run(self, engagement, mode, stream, verbose):
        self.stdout.write(f"[dry-run] Engagement: {engagement}")
        self.stdout.write(f"[dry-run] Mode: {mode}")
        if stream:
            self.stdout.write(f"[dry-run] Stream: {stream}")
        self.stdout.write(f"[dry-run] Status: {engagement.status}")
        self.stdout.write(f"[dry-run] Owner: {engagement.owner_tenant_id}")
        self.stdout.write(f"[dry-run] Provider: {engagement.provider_tenant_id}")

        if engagement.status != "active":
            self.stdout.write(self.style.WARNING("[dry-run] WARNING: Engagement is not active — sync would be rejected."))

        if has_running_sync(engagement=engagement):
            self.stdout.write(self.style.WARNING("[dry-run] WARNING: Engagement already has a running sync."))

        health = get_engagement_sync_health(engagement=engagement)
        self.stdout.write(f"[dry-run] Health: last_successful={health.last_successful_sync}")
        self.stdout.write(f"[dry-run] Health: running_sync_count={health.running_sync_count}")
        self.stdout.write(f"[dry-run] Health: failed_sync_count={health.failed_sync_count}")
        self.stdout.write(f"[dry-run] Health: checkpoint_age={health.checkpoint_age_seconds}s")
        self.stdout.write(f"[dry-run] Health: retry_queue={health.retry_queue_size}")
        self.stdout.write(f"[dry-run] Health: dead_letter_queue={health.dead_letter_count}")

        if engagement.status == "active":
            self.stdout.write(self.style.SUCCESS("[dry-run] Engagement is active — sync would proceed."))
        else:
            self.stdout.write(self.style.ERROR("[dry-run] Engagement is NOT active — sync would be rejected."))

    def _execute_sync(self, engagement, mode, stream, verbose):
        try:
            acquire_sync_lock(engagement=engagement)
        except SyncLockError as exc:
            raise CommandError(str(exc))

        try:
            if mode == "full":
                self.stdout.write(f"Starting full sync for engagement {engagement.pk}...")
                sync_run = run_full_sync(engagement=engagement)
            elif mode == "delta":
                self.stdout.write(f"Starting delta sync for engagement {engagement.pk}...")
                sync_run = run_delta_sync(engagement=engagement)
            elif mode == "resync":
                self.stdout.write(f"Starting resync for engagement {engagement.pk}, stream={stream}...")
                sync_run = run_resync(engagement=engagement, stream_name=stream)
            else:
                raise CommandError(f"Unknown mode: {mode}")
        except SyncNotAllowed as exc:
            raise CommandError(str(exc))

        self._print_summary(sync_run, verbose)

    def _print_summary(self, sync_run, verbose):
        status_style = self.style.SUCCESS if sync_run.status == "completed" else self.style.ERROR
        self.stdout.write(status_style(f"Sync run #{sync_run.pk}: {sync_run.status}"))
        self.stdout.write(f"  Run type: {sync_run.run_type}")
        self.stdout.write(f"  Status: {sync_run.status}")
        self.stdout.write(f"  Started: {sync_run.started_at}")
        if sync_run.completed_at:
            self.stdout.write(f"  Completed: {sync_run.completed_at}")
        if sync_run.failed_at:
            self.stdout.write(f"  Failed: {sync_run.failed_at}")
        if sync_run.error:
            self.stdout.write(f"  Error: {sync_run.error}")
        if sync_run.stats:
            self.stdout.write(f"  Stats: {sync_run.stats}")

        if verbose:
            items = sync_run.sync_items.all()
            self.stdout.write(f"  Items: {items.count()}")
            for item in items[:10]:
                self.stdout.write(f"    [{item.status}] {item.event_type} ({item.aggregate_id})")
            if items.count() > 10:
                self.stdout.write(f"    ... and {items.count() - 10} more")
