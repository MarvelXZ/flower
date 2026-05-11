from apps.tenancy.models import Client


def active_tenants():
    return Client.objects.filter(is_active=True)
