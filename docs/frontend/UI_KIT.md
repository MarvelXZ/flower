# Flower — UI Kit Reference

Live preview: `/ui-kit/` (Django) and the React `UIKit` component.

All components use `fw-*` CSS classes defined in `backend/static/css/flower-ui.css`.

---

## Layout

### Two-column app shell
```html
<div class="fw-app">
  <aside class="fw-sidebar">…</aside>
  <section class="fw-page">
    <header class="fw-topbar">…</header>
    <div class="fw-page-body">…</div>
  </section>
</div>
```

### Page header
```html
<div class="fw-page-header">
  <div class="fw-title-block">
    <span class="fw-eyebrow">Context</span>
    <h1 class="fw-title">Page title</h1>
    <p class="fw-subtitle">Brief description of this screen.</p>
  </div>
  <div class="fw-actions">
    <button class="fw-btn fw-btn-primary">Primary action</button>
  </div>
</div>
```

### Grid
```html
<div class="fw-grid fw-grid-2">…</div>  <!-- 2 col -->
<div class="fw-grid fw-grid-3">…</div>  <!-- 3 col -->
<div class="fw-grid fw-grid-4">…</div>  <!-- 4 col, collapses to 2 at 1024px, 1 at 768px -->
```

---

## Cards

### Basic card
```html
<div class="fw-card">…content…</div>
<div class="fw-panel">…larger padded content…</div>
```

### KPI card
```html
<article class="fw-card fw-kpi">
  <span class="fw-kpi-label">Active planters</span>
  <strong class="fw-kpi-value">428</strong>
  <span class="fw-kpi-meta">
    <span class="fw-status fw-status-ok">Healthy</span>
  </span>
</article>
```

---

## Buttons

```html
<button class="fw-btn fw-btn-primary">Primary</button>
<button class="fw-btn fw-btn-secondary">Secondary</button>
<button class="fw-btn fw-btn-ghost">Ghost</button>
<button class="fw-btn fw-btn-danger">Danger</button>

<!-- Sizes -->
<button class="fw-btn fw-btn-secondary fw-btn-sm">Small</button>
<button class="fw-btn fw-btn-primary fw-btn-lg">Large</button>

<!-- Icon only -->
<button class="fw-btn fw-btn-secondary fw-icon-btn" aria-label="Refresh">↺</button>
```

---

## Badges & Status

```html
<!-- Static badge (pill) -->
<span class="fw-badge">Tenant ready</span>
<span class="fw-badge fw-badge-neutral">Draft</span>
<span class="fw-badge fw-badge-accent">Provider</span>

<!-- Status indicator (with dot) -->
<span class="fw-status fw-status-ok">Online</span>
<span class="fw-status fw-status-warning">Delayed</span>
<span class="fw-status fw-status-danger">Offline</span>
<span class="fw-status fw-status-info">Pending</span>
<span class="fw-status fw-status-muted">Unknown</span>
```

Django partial shorthand:
```django
{% include "partials/status_badge.html" with status="ok" label=_("Online") %}
```

---

## Forms

```html
<form class="fw-form">
  <label class="fw-field-group">
    <span class="fw-label">Field label <span class="fw-required">*</span></span>
    <input class="fw-field" name="field" placeholder="Placeholder">
    <span class="fw-help">Helper text below the field.</span>
  </label>

  <label class="fw-field-group">
    <span class="fw-label">Select</span>
    <select class="fw-select" name="select">
      <option>Option 1</option>
    </select>
  </label>

  <label class="fw-field-group">
    <span class="fw-label">Textarea</span>
    <textarea class="fw-textarea" name="note"></textarea>
  </label>

  <label class="fw-check-row">
    <input type="checkbox">
    <span>Checkbox label</span>
  </label>

  <div class="fw-actions">
    <button class="fw-btn fw-btn-ghost" type="reset">Reset</button>
    <button class="fw-btn fw-btn-primary" type="submit">Save</button>
  </div>
</form>
```

---

## Tables

```html
<div class="fw-table-wrap">
  <table class="fw-table">
    <thead>
      <tr>
        <th>Name</th>
        <th>Status</th>
        <th class="fw-table-action-col"></th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Basil line 03</strong></td>
        <td><span class="fw-status fw-status-ok">Healthy</span></td>
        <td><button class="fw-btn fw-btn-secondary fw-btn-sm">Open</button></td>
      </tr>
    </tbody>
  </table>
</div>
```

---

## Alerts

```html
<div class="fw-alert">              <!-- info (default) -->
<div class="fw-alert fw-alert-success">
<div class="fw-alert fw-alert-warning">
<div class="fw-alert fw-alert-danger">
```

Structure:
```html
<div class="fw-alert fw-alert-warning">
  <span class="fw-alert-title">Moisture warning</span>
  <span class="fw-alert-body">3 planters below threshold.</span>
</div>
```

---

## Progress meter

```html
<!-- Use data-value or data-moisture; JS in base.html sets width -->
<div class="fw-meter" aria-label="82%" data-value="82">
  <span class="fw-meter-fill"></span>
</div>

<!-- Tone variants -->
<span class="fw-meter-fill is-warning"></span>
<span class="fw-meter-fill is-danger"></span>
```

---

## Empty state

```html
<div class="fw-empty">
  <div class="fw-empty-icon">🌿</div>
  <p class="fw-empty-title">No planters configured</p>
  <p class="fw-dimmed">Add your first planter to start monitoring.</p>
</div>
```

---

## Skeleton loading

```html
<div class="fw-skeleton fw-skeleton-text" style="width:60%;height:0.9em"></div>
<div class="fw-skeleton fw-skeleton-block" style="height:120px;margin-top:0.5rem"></div>
```

---

## Segmented control

```html
<div class="fw-segmented" aria-label="Time range">
  <button class="is-active" type="button">24h</button>
  <button type="button">7d</button>
  <button type="button">30d</button>
</div>
```

---

## Layout utilities

```html
<div class="fw-stack">…</div>      <!-- vertical stack, gap-3 -->
<div class="fw-inline">…</div>     <!-- horizontal wrap, gap-2 -->
<div class="fw-cluster">…</div>    <!-- flex wrap, align start -->
<div class="fw-toolbar">…</div>    <!-- space-between toolbar row -->
```
