"""WebSocket consumer for the provider dashboard.

Handles:
- Tenant-scoped connection (validated via JWT in query string)
- Real-time task/SLA/notification events
- Reconnect/resume via ``last_event_id``
- Heartbeat (ping/pong)
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.provider_ops.services.realtime_event_service import replay_events

logger = logging.getLogger(__name__)


class DashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time provider dashboard updates.

    Connect:  ``ws://host/ws/provider/v1/dashboard/?token=<JWT>``
    Reconnect: ``ws://host/ws/provider/v1/dashboard/?token=<JWT>&last_event_id=<id>``
    """

    async def connect(self):
        self.tenant_schema = self._validate_token()
        if not self.tenant_schema:
            await self.close(code=4001)
            return

        self.group_name = f"tenant_{self.tenant_schema}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("ws_connected", extra={"tenant": self.tenant_schema})

        # Replay missed events on reconnect
        last_event_id = self._get_last_event_id()
        if last_event_id is not None:
            events = await self._replay(last_event_id)
            if events:
                await self.send(text_data=json.dumps({
                    "type": "replay",
                    "count": len(events),
                    "events": events,
                }))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info("ws_disconnected", extra={"tenant": getattr(self, "tenant_schema", "?")})

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            return

        msg_type = data.get("type", "")

        if msg_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
        elif msg_type == "replay":
            events = await self._replay(data.get("after_event_id"))
            await self.send(text_data=json.dumps({
                "type": "replay",
                "count": len(events),
                "events": events,
            }))
        elif msg_type == "subscribe":
            # Placeholder: future subscription management
            pass

    async def realtime_event(self, event):
        """Receive a real-time event from the channel layer and forward to WS."""
        payload = {
            "event_id": event.get("event_id"),
            "event_type": event.get("event_type"),
            "entity_type": event.get("entity_type"),
            "entity_id": event.get("entity_id"),
            "version": event.get("version"),
            "timestamp": event.get("timestamp"),
            "payload": event.get("payload"),
        }
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def _replay(self, after_event_id: int) -> list[dict]:
        return replay_events(tenant_schema=self.tenant_schema, after_event_id=after_event_id)

    def _validate_token(self) -> str | None:
        """Extract and validate JWT from query string.

        Returns the tenant schema if valid, None otherwise.
        """
        try:
            from django.conf import settings
            from jwt import decode as jwt_decode

            token = self.scope["query_string"].decode().split("token=")[-1].split("&")[0]
            payload = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            return payload.get("tenant_schema")
        except Exception:
            return None

    def _get_last_event_id(self) -> int | None:
        try:
            qs = self.scope["query_string"].decode()
            for part in qs.split("&"):
                if part.startswith("last_event_id="):
                    return int(part.split("=")[1])
        except (ValueError, IndexError):
            pass
        return None
