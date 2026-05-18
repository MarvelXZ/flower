# Flower — Django Templates Guide

## Template hierarchy

```
backend/templates/
├── base.html               ← HTML shell: CSS, HTMX, meter init script
├── app_base.html           ← Authenticated shell: fw-app, sidebar, topbar
├── partials/
│   ├── sidebar.html        ← Main nav sidebar (include in app_base)
│   ├── topbar.html         ← Sticky top header bar
│   ├── status_badge.html   ← Reusable status chip partial
│   └── ui_feedback.html    ← HTMX swap target partial
├── dashboard/
│   └── index.html          ← Operator dashboard
└── ui_kit/
    └── index.html          ← Component showcase (developer tool)
```

---

## Creating a new page

Extend `app_base.html`:

```django
{% extends "app_base.html" %}
{% load i18n %}

{% block page_title %}{% translate "Locations" %}{% endblock %}

{% block topbar %}
    {% with topbar_title=_("Locations") topbar_parent=_("Assets") topbar_parent_url="/app/" %}
        {% include "partials/topbar.html" %}
    {% endwith %}
{% endblock %}

{% block page_content %}
    <div class="fw-page-header">
        <div class="fw-title-block">
            <span class="fw-eyebrow">{% translate "Assets" %}</span>
            <h1 class="fw-title">{% translate "Locations" %}</h1>
        </div>
        <div class="fw-actions">
            <a class="fw-btn fw-btn-primary" href="{% url 'locations:create' %}">
                {% translate "Add location" %}
            </a>
        </div>
    </div>

    {# Content here #}
{% endblock %}
```

---

## Context variables for partials

### `sidebar.html`
| Variable | Type | Description |
|---|---|---|
| `sidebar_active` | `str` | Key of the active nav item (e.g. `"dashboard"`, `"alerts"`) |
| `alert_count` | `int` | Unread alert count shown as badge in nav |

Pass via view context or Django template tag:
```python
def dashboard_view(request):
    return render(request, "dashboard/index.html", {
        "sidebar_active": "dashboard",
        "alert_count": Alert.objects.filter(tenant=..., resolved=False).count(),
    })
```

### `topbar.html`
| Variable | Type | Description |
|---|---|---|
| `topbar_title` | `str` | Current page title (shown in breadcrumb) |
| `topbar_parent` | `str` | Parent section label |
| `topbar_parent_url` | `str` | URL for parent breadcrumb link |
| `notification_count` | `int` | Unread notification count for bell icon |

### `status_badge.html`
| Variable | Required | Values |
|---|---|---|
| `status` | yes | `ok`, `warning`, `danger`, `info`, `muted` |
| `label` | yes | Translated string |

---

## i18n rules

**All static template text** must use gettext:
```django
{% translate "Save" %}
{% blocktranslate count n=item_count %}{{ n }} item{% plural %}{{ n }} items{% endblocktranslate %}
```

**Python strings** use `gettext_lazy`:
```python
from django.utils.translation import gettext_lazy as _

class MyView(View):
    title = _("Locations")
```

**Dynamic model fields** (names, descriptions) that need translation per locale must use `django-modeltranslation`.

---

## HTMX patterns

### Swap a partial into a target
```html
<button class="fw-btn fw-btn-primary"
        hx-post="{% url 'planters:toggle' planter.id %}"
        hx-target="#planter-status-{{ planter.id }}"
        hx-swap="outerHTML">
    {% translate "Toggle" %}
</button>

<span id="planter-status-{{ planter.id }}">
    {% include "partials/status_badge.html" with status=planter.status_tone label=planter.status_label %}
</span>
```

### Lazy-load a section
```html
<div hx-get="{% url 'telemetry:summary' %}"
     hx-trigger="load"
     hx-swap="innerHTML">
    <div class="fw-skeleton fw-skeleton-block" style="height:200px"></div>
</div>
```

### Form with feedback
```html
<form hx-post="{% url 'planters:create' %}"
      hx-target="#form-result"
      hx-swap="outerHTML">
    {% csrf_token %}
    …
</form>
<div id="form-result"></div>
```

The view returns `{% include "partials/ui_feedback.html" %}` on success.

---

## fw-meter initialization

Meters use a data attribute — no inline style with template variables:

```html
<div class="fw-meter" aria-label="{{ value }}%" data-value="{{ value }}">
    <span class="fw-meter-fill"></span>
</div>
```

`base.html` includes a global script that reads `data-value` (or `data-moisture`) and sets `fill.style.width` on `DOMContentLoaded` and after each `htmx:afterSwap`.

---

## Anti-patterns to avoid

| Bad | Good |
|---|---|
| `style="color: #246b45"` | `class="fw-status fw-status-ok"` |
| `style="width:{{ val }}%"` in templates | `data-value="{{ val }}"` + JS |
| Hardcoded English strings | `{% translate "…" %}` |
| `po-*` classes | `fw-*` classes |
