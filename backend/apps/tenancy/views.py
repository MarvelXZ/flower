from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import FormView, UpdateView

from apps.tenancy.forms import TenantCreateForm, TenantUpdateForm
from apps.tenancy.models import Client, Domain
from apps.tenancy.services import create_tenant


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Limit platform tenant management screens to staff users."""

    login_url = "/admin/login/"

    def test_func(self):
        return self.request.user.is_staff


class TenantListView(StaffRequiredMixin, ListView):
    """Render platform tenants for onboarding and management."""

    model = Client
    template_name = "tenancy/tenant_list.html"
    context_object_name = "tenants"

    def get_queryset(self):
        return Client.objects.prefetch_related("domains").order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sidebar_active"] = "tenants"
        return context


class TenantCreateView(StaffRequiredMixin, FormView):
    """Create a tenant company and primary domain."""

    template_name = "tenancy/tenant_form.html"
    form_class = TenantCreateForm
    success_url = reverse_lazy("tenancy_ui:tenant-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": _("Add tenant company"),
                "form_subtitle": _("Create the company tenant, schema, and primary domain."),
                "submit_label": _("Create tenant"),
                "sidebar_active": "tenants",
                "mode": "create",
            }
        )
        return context

    def form_valid(self, form):
        tenant = create_tenant(**form.cleaned_data)
        messages.success(self.request, _("Tenant %(name)s was created.") % {"name": tenant.name})
        return redirect("tenancy_ui:tenant-edit", pk=tenant.pk)


class TenantUpdateView(StaffRequiredMixin, UpdateView):
    """Edit tenant metadata and primary domain."""

    model = Client
    form_class = TenantUpdateForm
    template_name = "tenancy/tenant_form.html"
    success_url = reverse_lazy("tenancy_ui:tenant-list")

    def get_object(self, queryset=None):
        return get_object_or_404(Client, pk=self.kwargs["pk"])

    def get_primary_domain(self):
        return self.object.domains.filter(is_primary=True).first()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["primary_domain"] = self.get_primary_domain()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": _("Edit tenant company"),
                "form_subtitle": _("Update company metadata and primary domain."),
                "submit_label": _("Save changes"),
                "sidebar_active": "tenants",
                "mode": "edit",
            }
        )
        return context

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            domain_value = form.cleaned_data["primary_domain"]
            primary_domain = self.get_primary_domain()
            if primary_domain:
                primary_domain.domain = domain_value
                primary_domain.is_primary = True
                primary_domain.save(update_fields=["domain", "is_primary"])
            else:
                Domain.objects.create(tenant=self.object, domain=domain_value, is_primary=True)

        messages.success(self.request, _("Tenant %(name)s was updated.") % {"name": self.object.name})
        return redirect("tenancy_ui:tenant-edit", pk=self.object.pk)
