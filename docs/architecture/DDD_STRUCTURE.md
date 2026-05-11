# DDD Structure

Flower is a modular monolith with DDD-lite boundaries. Each bounded context is a Django app with a consistent internal layout.

`models/` owns persistence models for the context. `services/` owns write operations. `selectors/` owns read/query operations. `domain/` contains enums, constants, and policies. `events/` and `tasks/` provide integration points for domain events and Celery workers. `api/` contains DRF serializers, views, and URL registration.

API views do not perform direct write operations on models. They validate input and call services. Services enforce tenant boundaries and create any required events or outbox records. Selectors centralize read/query behavior so views and services do not spread query rules across the codebase.

Cross-context references should be explicit and minimal. If a workflow crosses tenant boundaries, it must use a B2B contract, outbox event, or dedicated synchronization service.
