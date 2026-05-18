from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django_tenants.utils import tenant_context

from apps.devices.forms import PlatformDeviceProvisionForm
from apps.devices.models import Device
from apps.devices.services.provisioning_service import (
    activate_device,
    complete_provisioning,
    create_device_credentials,
    register_device,
)
from apps.tenancy.domain.enums import TenantKind
from apps.tenancy.models import Client


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Limit platform control-plane screens to staff users."""

    login_url = "/admin/login/"

    def test_func(self):
        return self.request.user.is_staff


class PlatformDeviceFleetView(StaffRequiredMixin, TemplateView):
    """Show platform staff a cross-tenant device health overview."""

    template_name = "devices/platform_fleet.html"
    max_missed_heartbeats = 3

    def get_tenants(self):
        return Client.objects.filter(
            is_active=True,
            kind__in=[TenantKind.OWNER, TenantKind.HYBRID],
        ).order_by("name")

    def build_device_row(self, *, tenant, device, now):
        last_seen_at = device.last_seen_at
        stale_after_seconds = device.heartbeat_interval_seconds * self.max_missed_heartbeats
        is_reporting = False
        health_status = "muted"
        health_label = _("Never seen")

        if device.status == "retired":
            health_status = "muted"
            health_label = _("Retired")
        elif device.status == "offline":
            health_status = "danger"
            health_label = _("Offline")
        elif last_seen_at:
            age_seconds = (now - last_seen_at).total_seconds()
            if age_seconds <= stale_after_seconds:
                is_reporting = True
                health_status = "ok"
                health_label = _("Online")
            else:
                health_status = "warning"
                health_label = _("Stale")

        return {
            "tenant_name": tenant.name,
            "tenant_schema": tenant.schema_name,
            "name": device.name,
            "serial_number": device.serial_number,
            "mqtt_client_id": device.mqtt_client_id,
            "status": device.get_status_display(),
            "provisioning_status": device.get_provisioning_status_display(),
            "last_seen_at": last_seen_at,
            "heartbeat_interval_seconds": device.heartbeat_interval_seconds,
            "health_status": health_status,
            "health_label": health_label,
            "is_reporting": is_reporting,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        rows = []

        for tenant in self.get_tenants():
            with tenant_context(tenant):
                devices = Device.objects.order_by("name", "serial_number")
                for device in devices:
                    rows.append(self.build_device_row(tenant=tenant, device=device, now=now))

        context.update(
            {
                "sidebar_active": "devices",
                "devices": rows,
                "total_devices": len(rows),
                "online_devices": sum(1 for row in rows if row["health_status"] == "ok"),
                "attention_devices": sum(
                    1 for row in rows if row["health_status"] in {"warning", "danger"}
                ),
                "never_seen_devices": sum(1 for row in rows if row["health_label"] == _("Never seen")),
            }
        )
        return context


class PlatformDeviceProvisionView(StaffRequiredMixin, FormView):
    """Provision a device from the platform tenant into a customer tenant."""

    template_name = "devices/platform_provision.html"
    form_class = PlatformDeviceProvisionForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sidebar_active"] = "devices"
        return context

    def form_valid(self, form):
        owner_tenant = form.cleaned_data["owner_tenant"]
        credential = None

        with tenant_context(owner_tenant):
            device = register_device(
                name=form.cleaned_data["name"],
                serial_number=form.cleaned_data["serial_number"],
                hardware_revision=form.cleaned_data["hardware_revision"],
                firmware_version=form.cleaned_data["firmware_version"],
                owner_tenant_schema=owner_tenant.schema_name,
                capabilities=form.cleaned_data["capabilities"],
                heartbeat_interval_seconds=form.cleaned_data["heartbeat_interval_seconds"],
                mqtt_client_id=form.cleaned_data["mqtt_client_id"],
            )

            if form.cleaned_data["create_credentials"]:
                credential = create_device_credentials(device=device)
                complete_provisioning(device=device)

            if form.cleaned_data["activate_now"]:
                activate_device(device=device)

        messages.success(
            self.request,
            _("Device %(serial)s was provisioned for %(tenant)s.")
            % {"serial": device.serial_number, "tenant": owner_tenant.name},
        )
        context = self.get_context_data(
            form=self.form_class(),
            provisioned_device=device,
            provisioned_tenant=owner_tenant,
            provisioned_credential=credential,
            plaintext_secret=getattr(credential, "_plaintext_secret", "") if credential else "",
        )
        return render(self.request, self.template_name, context)
