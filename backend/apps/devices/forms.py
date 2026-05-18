from django import forms
from django.utils.translation import gettext_lazy as _
from django_tenants.utils import tenant_context

from apps.devices.models import Device
from apps.tenancy.domain.enums import TenantKind
from apps.tenancy.models import Client


class PlatformDeviceProvisionForm(forms.Form):
    """Provision a physical device into a selected owner tenant schema."""

    owner_tenant = forms.ModelChoiceField(
        label=_("Owner tenant"),
        queryset=Client.objects.none(),
        help_text=_("Company that bought or owns this sensor/pot."),
    )
    name = forms.CharField(label=_("Device name"), max_length=160)
    serial_number = forms.CharField(label=_("Serial number"), max_length=120)
    hardware_revision = forms.CharField(
        label=_("Hardware revision"),
        max_length=50,
        required=False,
    )
    firmware_version = forms.CharField(
        label=_("Firmware version"),
        max_length=50,
        required=False,
    )
    mqtt_client_id = forms.CharField(
        label=_("MQTT client ID"),
        max_length=160,
        required=False,
        help_text=_("Leave empty to use dev_<serial number>."),
    )
    heartbeat_interval_seconds = forms.IntegerField(
        label=_("Heartbeat interval"),
        min_value=10,
        max_value=86400,
        initial=60,
    )
    capabilities = forms.CharField(
        label=_("Capabilities"),
        required=False,
        help_text=_("Comma-separated, for example temperature, humidity, soil_moisture."),
    )
    create_credentials = forms.BooleanField(
        label=_("Create device API credentials"),
        required=False,
        initial=True,
    )
    activate_now = forms.BooleanField(
        label=_("Activate device now"),
        required=False,
        initial=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner_tenant"].queryset = Client.objects.filter(
            is_active=True,
            kind__in=[TenantKind.OWNER, TenantKind.HYBRID],
        ).order_by("name")

    def clean_serial_number(self) -> str:
        return self.cleaned_data["serial_number"].strip()

    def clean_mqtt_client_id(self) -> str:
        return self.cleaned_data["mqtt_client_id"].strip()

    def clean_capabilities(self) -> list[str]:
        raw_value = self.cleaned_data.get("capabilities", "")
        if isinstance(raw_value, list):
            return raw_value
        return [item.strip() for item in raw_value.split(",") if item.strip()]

    def clean(self):
        cleaned_data = super().clean()
        owner_tenant = cleaned_data.get("owner_tenant")
        serial_number = cleaned_data.get("serial_number")

        if cleaned_data.get("activate_now") and not cleaned_data.get("create_credentials"):
            raise forms.ValidationError(
                _("A device must have credentials before it can be activated."),
            )

        if owner_tenant and serial_number:
            with tenant_context(owner_tenant):
                if Device.objects.filter(serial_number=serial_number).exists():
                    self.add_error(
                        "serial_number",
                        _("A device with this serial number already exists in this tenant."),
                    )

        return cleaned_data
