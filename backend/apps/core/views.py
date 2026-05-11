"""Core HTML views for shared PlantOps interface surfaces."""

from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView


class UIKitView(TemplateView):
    """Render the shared Django and HTMX UI kit."""

    template_name = "ui_kit/index.html"


class DashboardView(TemplateView):
    """Render the default operations dashboard."""

    template_name = "dashboard/index.html"


@require_POST
def ui_kit_sample(request):
    """Return a small HTMX fragment used by the UI kit demo form."""

    return render(request, "partials/ui_feedback.html")
