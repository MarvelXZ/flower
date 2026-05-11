# Flutter Mobile App Architecture

## Clean Architecture Layers

```
presentation/        ← Widgets, screens, providers (Riverpod)
    │
application/         ← Use cases, state management
    │
domain/              ← Entities, repository interfaces, value objects
    │
infrastructure/      ← API clients, local DB, realtime, sync, auth
    │
core/                ← Network, storage, error handling
```

## Layer Rules

| Layer | Depends on | Never depends on |
|-------|-----------|------------------|
| `presentation` | `application`, `domain` | `infrastructure` (directly) |
| `application` | `domain` | `infrastructure`, Flutter |
| `domain` | Nothing | Flutter, Dio, Drift |
| `infrastructure` | `domain`, `core` | `presentation` |
| `core` | Nothing | Business logic |

## Feature Structure

lib/
├── core/
│   ├── network/          Dio client, interceptors
│   ├── storage/          Secure storage
│   └── error/            API error parsing
├── domain/
│   ├── entities/         TaskEntity, SLAAEntity, etc.
│   ├── repositories/     Abstract repository interfaces
│   └── value_objects/    Enums, constants
├── application/
│   ├── auth/             Auth use cases
│   └── tasks/            Task use cases
├── infrastructure/
│   ├── auth/             AuthRepository impl
│   ├── tasks/            TaskRepository impl
│   ├── database/         Drift schema & DAO
│   ├── realtime/         WebSocket client
│   └── sync/             Delta sync, replay service
└── presentation/
    ├── screens/          Splash, Login, Dashboard, Detail
    ├── widgets/          Reusable components
    └── providers/        Riverpod state providers
```
