"""
Alerts write operations (services layer).

All mutations to alert data MUST go through this module.
Direct model writes outside of services are prohibited.

NOTE: Alert events are append-only. There are no updates or deletes.
"""
