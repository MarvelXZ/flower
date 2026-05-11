# Mobile Release Checklist

## Pre-release

- [ ] `flutter analyze` — no warnings
- [ ] `flutter test` — all pass
- [ ] All backend migrations generated (`makemigrations --check --dry-run`)
- [ ] All backend tests pass (`pytest`)
- [ ] API contract verified against backend error codes
- [ ] JWT auth flow tested (login → token refresh → logout)
- [ ] WebSocket connect/reconnect tested
- [ ] Delta sync fallback tested
- [ ] Offline mode tested (airplane mode → queue → reconnect)

## Build

- [ ] Flutter flavor configured (dev/staging/production)
- [ ] API base URL per flavor
- [ ] App signing configured
- [ ] Version bump (`pubspec.yaml`)
- [ ] Android: app bundle / APK
- [ ] iOS: archive / TestFlight

## Deployment

- [ ] Backend deployed with latest migrations
- [ ] Redis channel layer configured
- [ ] Prometheus + Grafana live
- [ ] Sentry DSN configured
- [ ] FCM credentials for push

## Production Verification

- [ ] Healthcheck endpoints respond
- [ ] Metrics endpoint protected
- [ ] Logging pipeline live
- [ ] First operator login works
- [ ] Task create/assign/complete flow works
- [ ] SLA breach detected and visible
- [ ] Push notification received on mobile

## Known Gaps (Phase 20)

- Drift migrations not yet automated (manual schema version bump)
- FCM push notification setup not complete
- Firebase cloud messaging token registration not wired
- Tablet responsive layout not implemented
- Notification preferences sync not implemented
- Analytics/event tracking not implemented
- Crash reporting (Sentry) not wired on mobile side
