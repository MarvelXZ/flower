from django import forms
from django.utils.translation import gettext_lazy as _

from apps.tenancy.domain.enums import TenantKind
from apps.tenancy.models import Client, Domain


class TenantCreateForm(forms.Form):
    """Form for the first tenant onboarding step."""

    name = forms.CharField(label=_("Company name"), max_length=150)
    slug = forms.SlugField(label=_("Slug"), max_length=80)
    schema_name = forms.RegexField(
        label=_("Schema name"),
        regex=r"^[a-z][a-z0-9_]*$",
        max_length=63,
        help_text=_("Lowercase letters, numbers, and underscores. Cannot be changed later."),
    )
    domain = forms.CharField(
        label=_("Primary domain"),
        max_length=253,
        help_text=_("Hostname only, for example hotel-magnolia.localhost."),
    )
    kind = forms.ChoiceField(label=_("Tenant type"), choices=TenantKind.choices)

    def clean_slug(self) -> str:
        value = self.cleaned_data["slug"]
        if Client.objects.filter(slug=value).exists():
            raise forms.ValidationError(_("Tenant slug already exists."))
        return value

    def clean_schema_name(self) -> str:
        value = self.cleaned_data["schema_name"]
        if value == "public":
            raise forms.ValidationError(_("The public schema is reserved."))
        if Client.objects.filter(schema_name=value).exists():
            raise forms.ValidationError(_("Tenant schema already exists."))
        return value

    def clean_domain(self) -> str:
        value = self.cleaned_data["domain"].strip().lower()
        if "/" in value or ":" in value:
            raise forms.ValidationError(_("Use a hostname only, without protocol or path."))
        if Domain.objects.filter(domain=value).exists():
            raise forms.ValidationError(_("Tenant domain already exists."))
        return value


class TenantUpdateForm(forms.ModelForm):
    """Edit tenant metadata and the primary domain."""

    primary_domain = forms.CharField(label=_("Primary domain"), max_length=253)

    class Meta:
        model = Client
        fields = ["name", "slug", "kind", "is_active"]
        labels = {
            "name": _("Company name"),
            "slug": _("Slug"),
            "kind": _("Tenant type"),
            "is_active": _("Active"),
        }

    def __init__(self, *args, **kwargs):
        self.primary_domain = kwargs.pop("primary_domain", None)
        super().__init__(*args, **kwargs)
        if self.primary_domain:
            self.fields["primary_domain"].initial = self.primary_domain.domain

    def clean_slug(self) -> str:
        value = self.cleaned_data["slug"]
        qs = Client.objects.filter(slug=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Tenant slug already exists."))
        return value

    def clean_primary_domain(self) -> str:
        value = self.cleaned_data["primary_domain"].strip().lower()
        if "/" in value or ":" in value:
            raise forms.ValidationError(_("Use a hostname only, without protocol or path."))
        qs = Domain.objects.filter(domain=value)
        if self.primary_domain:
            qs = qs.exclude(pk=self.primary_domain.pk)
        if qs.exists():
            raise forms.ValidationError(_("Tenant domain already exists."))
        return value
