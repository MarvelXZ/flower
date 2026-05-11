# Mobile Apps

Flower will support owner and provider mobile applications with React Native and Expo.

The owner app focuses on asset overview, plant health, device state, alerts, and care recommendations. The provider app focuses on assigned external assets, field-service tasks, interventions, and synchronized telemetry.

Push notifications will use FCM/APNs through the notifications bounded context. Device push tokens and user notification preferences should remain tenant-scoped.

Mobile APIs must follow the same service-layer write rule and tenant isolation guarantees as the web/API backend.
