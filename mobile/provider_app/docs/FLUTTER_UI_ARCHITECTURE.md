# Flutter UI Architecture (Phase 20)

## Navigation & App Shell

```
SplashScreen → LoginScreen → AppShell (auth guard)
                                │
                    ┌───────────┼───────────┬───────────┐
                    ▼           ▼           ▼           ▼
               Tasks(/tasks)  SLA(/sla)  Alerts      Settings
                    │                      (/notif.)  (/settings)
                    ▼
               TaskDetail(/tasks/:id)
```

- **AppShell**: `Scaffold` + `NavigationBar` with 4 tabs
- **Bottom nav**: Tasks, SLA, Alerts, Settings
- **Tablet**: responsive split view (planned)
- **Auth guard**: splash screen checks token → login or home

## Screen Architecture

| Screen | Purpose | Data source |
|--------|---------|-------------|
| SplashScreen | Auth check, loading | Secure storage |
| LoginScreen | JWT login | AuthRepository |
| TaskDashboardScreen | Task list + filters + sort | TaskRepository + WS events |
| TaskDetailScreen | Full task view + actions | TaskRepository + WS events |
| SLAAlertsScreen | Breach summary + overdue list | SLA selector |
| NotificationsScreen | In-app notification list | Local cache |
| SettingsScreen | User info, theme, diagnostics, logout | Local + storage |

## State Management (Riverpod)

| Provider | Type | Purpose |
|----------|------|---------|
| `authControllerProvider` | StateNotifier | Login/logout/token |
| `taskListControllerProvider` | StateNotifier | Task list + filters + pagination |
| `taskDetailControllerProvider` | StateNotifier | Single task + actions |
| `slaDashboardProvider` | FutureProvider | SLA summary |
| `syncStatusProvider` | StateProvider | Sync status (idle/syncing/error) |
| `realtimeStatusProvider` | StateProvider | WS connection state |
| `settingsProvider` | StateProvider | Dark mode, compact mode |

## Offline UX

| UI Element | When | Behavior |
|------------|------|----------|
| Offline banner | No connectivity | Persistent banner at top |
| Sync indicator | Syncing | Subtle spinner in app bar |
| Pending badge | Queue > 0 | Badge on settings icon |
| Stale data | Offline > 5min | Subtle warning on cards |
| Error banner | Sync failed | Dismissible error |

## Realtime UI Integration

```
WebSocket event
  │
  ├── RealtimeEventService.parse(event)
  │     ├── task_created    → taskListController.add()
  │     ├── task_updated    → taskListController.update()
  │     ├── task_completed  → taskListController.remove() or update()
  │     ├── sla_breached    → slaDashboardProvider.refresh()
  │     └── notification    → notificationListController.add()
  │
  └── Update local Drift DB → persist for offline
```
