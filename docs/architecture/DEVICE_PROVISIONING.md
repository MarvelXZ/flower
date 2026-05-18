# Device Provisioning

Flower devices are tenant-local records.

The platform tenant is the control plane, but a device owned by a customer
company must be created inside that customer's tenant schema. This keeps
telemetry, credentials, and operational state isolated per tenant while still
allowing platform staff to onboard physical sensors and smart pots.

## Platform Flow

Platform staff use:

- `http://platform.localhost:8000/devices/`
- `http://platform.localhost:8000/devices/provision/`
- `http://platform.localhost:8000/admin/devices/device/fleet/`
- `http://platform.localhost:8000/admin/devices/device/provision/`

The provisioning form selects an active owner or hybrid tenant and then runs
the device provisioning service inside that tenant context.

The fleet view reads devices across active owner and hybrid tenants. It treats
a device as online when `last_seen_at` is within three configured heartbeat
intervals. Devices that have never reported, are stale, offline, or retired are
shown separately so platform staff can spot provisioning and connectivity
issues.

Created records:

- `Device` in the selected tenant schema
- optional `DeviceCredential` in the selected tenant schema
- provisioning audit transitions in the selected tenant schema

## Rule

Do not use the regular `DeviceAdmin` list as a cross-tenant inventory. It only
shows devices from the current request schema. Cross-tenant provisioning must
switch schema explicitly with `tenant_context(owner_tenant)` and call the
canonical provisioning service.
