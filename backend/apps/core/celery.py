"""
Tenant-aware Celery task base class.

All Celery tasks that touch tenant data MUST inherit from TenantTask
or explicitly wrap their work in tenant_context().
"""

from celery import Task


class TenantTask(Task):
    """
    Base Celery task that automatically switches into the correct
    tenant schema based on a `_tenant_id` keyword argument.

    Usage:
        @shared_task(base=TenantTask)
        def process_device_telemetry(device_id: str, _tenant_id: str):
            ...
    """

    def __call__(self, *args, **kwargs):
        tenant_id = kwargs.pop("_tenant_id", None)
        if tenant_id:
            from django_tenants.utils import tenant_context
            from apps.tenancy.models import Client

            try:
                tenant = Client.objects.get(id=tenant_id)
            except Client.DoesNotExist:
                raise RuntimeError(
                    f"TenantTask cannot find tenant with id={tenant_id}"
                ) from None
            with tenant_context(tenant):
                return self.run(*args, **kwargs)
        return self.run(*args, **kwargs)
