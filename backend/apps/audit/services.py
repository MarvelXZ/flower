"""
Audit write operations (services layer).

All mutations to audit data MUST go through this module.
Direct model writes outside of services are prohibited.

NOTE: Audit logs are append-only. There are no updates or deletes.
"""
