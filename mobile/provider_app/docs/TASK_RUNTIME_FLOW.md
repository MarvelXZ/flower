# Task Runtime Flow

## Complete Task Lifecycle (operator view)

```
         ┌──────────┐
         │   OPEN   │
         └────┬─────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌────────┐ ┌────────┐ ┌──────────┐
│ASSIGNED│ │IN_PROG.│ │CANCELLED │ (terminal)
└───┬────┘ └───┬────┘ └──────────┘
    │         │
    └────┬────┘
         ▼
   ┌──────────┐
   │IN_PROG.  │
   └────┬─────┘
        │
   ┌────┴────┐
   ▼         ▼
┌───────┐ ┌──────────┐
│COMPL. │ │CANCELLED │
│(term) │ │(terminal)│
└───────┘ └──────────┘
```

## UI Actions per Status

| Status | Available Actions |
|--------|-----------------|
| Open | Assign, Start, Cancel |
| Assigned | Start, Cancel |
| In Progress | Complete, Cancel |
| Completed | (none — terminal, view only) |
| Cancelled | (none — terminal, view only) |

## API Calls

| Action | Method | Endpoint |
|--------|--------|----------|
| Assign | POST | `/api/provider/v1/tasks/{id}/assign/` |
| Start | POST | `/api/provider/v1/tasks/{id}/start/` |
| Complete | POST | `/api/provider/v1/tasks/{id}/complete/` |
| Cancel | POST | `/api/provider/v1/tasks/{id}/cancel/` |
| Add note | POST | `/api/provider/v1/tasks/{id}/notes/` |
| Fetch list | GET | `/api/provider/v1/tasks/?status=&priority=&ordering=&limit=&offset=` |
| Fetch detail | GET | `/api/provider/v1/tasks/{id}/` |
| Delta sync | GET | `/api/provider/v1/dashboard/delta/?since=` |
