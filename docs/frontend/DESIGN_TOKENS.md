# Flower — Design Tokens

All tokens are CSS custom properties defined in `backend/static/css/flower-ui.css`.

## Naming convention

```
--color-{palette}-{shade}   ← primitive / raw palette
--fw-{role}                 ← semantic / contextual alias
```

---

## Primitive Palette

### Concrete (beton)
| Token | Value | Use |
|---|---|---|
| `--color-concrete-50`  | `#F8F6F4` | Near-white tinted background |
| `--color-concrete-100` | `#EFEBe7` | |
| `--color-concrete-200` | `#E2DDD8` | |
| `--color-concrete-300` | `#CEC8C1` | |
| `--color-concrete-400` | `#B3ADA6` | |
| `--color-concrete-500` | `#918B84` | Muted text, borders |
| `--color-concrete-600` | `#726D68` | Soft text |
| `--color-concrete-700` | `#56524E` | Body text |
| `--color-concrete-800` | `#3B3835` | Dark text |
| `--color-concrete-900` | `#252220` | Near-black, sidebar background |

### Leaf (biljke)
| Token | Value | Use |
|---|---|---|
| `--color-leaf-50`  | `#EFF5F0` | Success/primary soft backgrounds |
| `--color-leaf-100` | `#D5E8C8` | |
| `--color-leaf-400` | `#6B9262` | |
| `--color-leaf-500` | `#4F7A48` | Success green |
| `--color-leaf-600` | `#3C5C44` | **Primary brand green** |
| `--color-leaf-700` | `#2D4535` | Hover/active primary |
| `--color-leaf-800` | `#1E3024` | |
| `--color-leaf-900` | `#111C15` | |

### Soil (zemlja)
| Token | Value | Use |
|---|---|---|
| `--color-soil-50`  | `#FAF5EF` | Accent soft backgrounds |
| `--color-soil-100` | `#EEDCC0` | |
| `--color-soil-300` | `#C69870` | |
| `--color-soil-500` | `#8D6038` | **Accent / terracotta** |
| `--color-soil-700` | `#513820` | |

### Sand (pesak)
| Token | Value | Use |
|---|---|---|
| `--color-sand-50`  | `#FAFAF7` | Page background |
| `--color-sand-100` | `#F4F0E8` | Strong background |
| `--color-sand-200` | `#EDE6D7` | Default border |
| `--color-sand-300` | `#E2D8C4` | Strong border |
| `--color-sand-400` | `#D4C6AC` | |

---

## Semantic Tokens

### Surfaces
| Token | Resolves to | Description |
|---|---|---|
| `--fw-bg` | `--color-sand-50` | Page background |
| `--fw-bg-strong` | `--color-sand-100` | Hover / section bg |
| `--fw-surface` | `#FFFFFF` | Card / panel background |
| `--fw-surface-muted` | `--color-sand-50` | Secondary surface |

### Text
| Token | Resolves to | Description |
|---|---|---|
| `--fw-ink` | `--color-concrete-900` | Primary text |
| `--fw-ink-soft` | `--color-concrete-700` | Secondary text |
| `--fw-ink-muted` | `--color-concrete-500` | Placeholder, captions |

### Borders
| Token | Resolves to | Description |
|---|---|---|
| `--fw-border` | `--color-sand-200` | Default border |
| `--fw-border-strong` | `--color-sand-300` | Input / focused border |

### Brand
| Token | Description |
|---|---|
| `--fw-primary` | Leaf-600 — main CTA green |
| `--fw-primary-strong` | Leaf-700 — hover state |
| `--fw-primary-soft` | Leaf-50 — badge/chip background |
| `--fw-accent` | Soil-500 — terracotta accent |
| `--fw-accent-soft` | Soil-100 — accent chip background |

### Status
| Token | Value | Description |
|---|---|---|
| `--fw-success` | leaf-500 | Success state |
| `--fw-success-soft` | leaf-50 | Success chip background |
| `--fw-warning` | `#8C5308` | Warning amber |
| `--fw-warning-soft` | `#FDF4E7` | Warning chip background |
| `--fw-danger` | `#A42E2E` | Error / danger |
| `--fw-danger-soft` | `#FDEAEA` | Danger chip background |
| `--fw-info` | `#3E6480` | Info slate-blue |
| `--fw-info-soft` | `#EAF1F7` | Info chip background |

### Effects
| Token | Value |
|---|---|
| `--fw-shadow-sm` | `0 1px 3px rgba(37,34,32,.07)` |
| `--fw-shadow` | `0 4px 18px rgba(37,34,32,.09)` |
| `--fw-shadow-lg` | `0 16px 48px rgba(37,34,32,.12)` |
| `--fw-focus` | `0 0 0 3px rgba(60,92,68,.30)` |

### Spacing
`--fw-space-1` (0.25rem) through `--fw-space-12` (3rem).

### Border radius
| Token | Value |
|---|---|
| `--fw-radius-xs` | 2px |
| `--fw-radius-sm` | 4px |
| `--fw-radius-md` | 6px |
| `--fw-radius-lg` | 10px |
| `--fw-radius-full` | 999px |

---

## Rules

1. **Never** use hardcoded hex values in templates or React components — always reference a token.
2. Primitive tokens (`--color-*`) are for the token file only. Component code uses semantic tokens (`--fw-*`).
3. Adding a new color = add it to both the primitive and semantic sections of `flower-ui.css`.
