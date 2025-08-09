# Real-Time Monitoring Dashboard (Event-Driven)

This document specifies requirements and an implementation plan for a global, real‑time monitoring dashboard across projects and tasks without frontend polling.

## Objectives

- Provide global visibility into live processing:
  - Overall queue health and throughput.
  - Workers online and their current jobs.
  - Per research task (parent task) live progress across phases.
  - Per subtask (job) lifecycle with status, retries, errors.
- Eliminate polling by using event-driven WebSocket streaming.
- Minimal overhead and safe under intermittent Redis/Postgres hiccups (see `plans/hardening.md`).

## Scope (Phase 0/1)

- Phase 0 (MVP):
  - Backend publishes task lifecycle events via Redis Pub/Sub.
  - FastAPI WebSocket endpoint streams filtered events to clients.
  - Frontend dashboard renders global stats, project filter, per-task progress bars, and recent failures.
- Phase 1:
  - Worker heartbeat and queue-depth metrics.
  - Aggregated periodic snapshots to reduce client work.
  - Basic reconnection/backoff and feature flagging.

Non-goals (Phase 2+): event replay/history, long-term metrics store, alerting, Grafana dashboards (tracked separately).

## Assumptions & Integration Points

- __Redis client__: Reuse the global `redis_client` initialized in root `api.py` (`redis.asyncio.Redis.from_url(...)`). Do not create a second client unless isolated process.
- __Knowledge Base__: Reuse `global_kb` (PostgreSQL) from `api.py` for optional `project_id` lookup via `get_research_task(task_id)`.
- __Coordinator__: `ParallelTaskCoordinator` is instantiated in `api.py` as `global_task_coordinator`; instrumentation lives inside `src/orchestration/parallel_task_coordinator.py`.
- __Key prefixes__: Source of truth is `ParallelTaskCoordinator` constants: `TASK_QUEUE_PREFIX = "nexus:tasks"`, `TASK_STATUS_PREFIX = "nexus:task"`.
- __Parent vs child IDs__: Orchestrator sets `payload['task_id']` to the parent research task; the queued child job id is `Task.id`.
- __Env__: Use `REDIS_URL` and `NEXUS_MONITORING_ENABLED` already loaded in `api.py` via `dotenv`.

## Configuration & Defaults

- ENV flags (add to `.env` as needed):
  - `NEXUS_MONITORING_ENABLED=true` (feature flag; if false, publishing is no-op)
  - `REDIS_URL` (already used by API; reuse for monitoring)
  - `MONITORING_EVENTS_CHANNEL=nexus:events`
  - `MONITORING_STATS_CHANNEL=nexus:events:stats`
  - `MONITORING_PROJECT_CHANNEL_PREFIX=nexus:events:project:`
  - `MONITORING_HEARTBEAT_INTERVAL_SEC=10` (worker heartbeat cadence)
  - `MONITORING_HEARTBEAT_TTL_SEC=30` (worker liveness TTL)
  - `MONITORING_MAX_EVENT_SIZE_BYTES=8192` (truncate large payloads)

- Key prefixes (standardize across services):
  - Queue keys: `nexus:tasks:{priority}` where `{priority}` ∈ `high_priority|normal_priority|low_priority`
  - Task status/data keys: `nexus:task:{task_id}:status`, `nexus:task:{task_id}:data`, `nexus:task:{task_id}:result`, `nexus:task:{task_id}:error`
  - Task grouping (new): `nexus:task_group:{parent_task_id}` (Redis Set of child task IDs)
  - Task meta (optional): `nexus:task_meta:{parent_task_id}` (Redis Hash; e.g., project_id)

Tip: add these to `.env.example` with comments to aid local setup.

## Key UI Requirements

- Global header:
  - Workers online, queue depth by priority, tasks in progress, error rate last 1–5m.
- Filters:
  - By project and/or parent `task_id` (research task).
- Per-task cards (in-progress):
  - Task title, type, domain, project, started_at, ETA (rough), current phase.
  - Progress bars per phase with counts (completed/failed/pending) and rate.
- Live event table (recent N=200):
  - Time, project, parent task, job id, worker id, type, status, retry, duration, message.
- Failure spotlight:
  - Most recent failures with errors and quick links.

## Event Model

Use JSON events on Redis Pub/Sub. One global channel plus optional project-specific channels for easy filtering.

- Channels:
  - Global: `nexus:events`
  - By project (optional): `nexus:events:project:{project_id}` (publish to both for convenience)
  - Aggregates: `nexus:events:stats` (periodic snapshots)

- Event types (enum `MonitoringEventType`):
  - `worker_started`, `worker_heartbeat`, `worker_stopped`
  - `task_enqueued`, `task_started`, `task_retry`, `task_completed`, `task_failed`
  - `phase_started`, `phase_completed` (orchestrator phases)
  - `queue_depth_update`, `stats_snapshot`

- Event schema (Pydantic `MonitoringEvent`):
  - `event_id: str` (uuid4)
  - `ts: str` (ISO8601 UTC)
  - `event_type: str`
  - `project_id: Optional[str]`
  - `parent_task_id: Optional[str]` (research task id)
  - `task_id: Optional[str]` (job id from queue)
  - `task_type: Optional[str]` (e.g., `data_aggregation_search`, `data_aggregation_extract`)
  - `phase: Optional[str]` (e.g., `enumeration`, `search`, `extraction`, `enrichment`, `resolution`, `persistence`, `csv_generation`)
  - `worker_id: Optional[int]`
  - `retry_count: Optional[int]`
  - `status: Optional[str]` (pending|processing|completed|failed|retrying)
  - `duration_ms: Optional[int]`
  - `counts: Optional[dict]` (e.g., `{completed, failed, pending, queued}`)
  - `queue: Optional[dict]` (depth by priority)
  - `message: Optional[str]`
  - `error: Optional[str]`
  - `meta: Optional[dict]` (provider, subspace id/name, domain_hint, etc.)

Example event:
```json
{
  "event_id": "7e1d...",
  "ts": "2025-08-09T16:05:00Z",
  "event_type": "task_started",
  "project_id": "proj_123",
  "parent_task_id": "6ba529d4-...",
  "task_id": "6ba529d4_search_42",
  "task_type": "data_aggregation_search",
  "phase": "search",
  "worker_id": 3,
  "status": "processing",
  "retry_count": 0,
  "meta": {"query": "private schools in Fulton County", "subspace_index": 42}
}
```

### TaskType and TaskStatus values (source of truth)

- From `src/orchestration/task_types.py`:
  - `TaskType`: `summarization`, `entity_extraction`, `dok_categorization`, `search_space_enum`, `data_aggregation_search`, `data_aggregation_extract`, `search`, `reasoning` (enum values are strings)
  - `TaskStatus`: `pending`, `processing`, `completed`, `failed`, `retrying`
  - `Task` fields used: `id`, `type`, `payload` (dict), `priority`, `status`, `created_at`, `started_at`, `completed_at`, `error`, `result`, `retry_count`, `max_retries`, `parent_task_id` (optional)

## Backend Design

### Event Bus Utility
- File: `src/monitoring/event_bus.py`
- Class: `EventBus` with `publish(event: MonitoringEvent, project_id: Optional[str]=None)`.
- Impl: uses `redis.asyncio` with JSON serialization, retries (exponential backoff + jitter), and short timeouts.
- Feature flag: `NEXUS_MONITORING_ENABLED` (env). If disabled, `publish()` is no-op.

### Instrumentation Points

- `src/orchestration/parallel_task_coordinator.py` (`ParallelTaskCoordinator`):
  - `submit_tasks(...)`: publish `task_enqueued` per task.
    - Include identifiers:
      - `parent_task_id`: prefer `task.parent_task_id` if set; else `task.payload.get('task_id')` (used by current orchestrator)
      - `project_id`: prefer `task.payload.get('project_id')`. If missing, do a one-time KB lookup by `parent_task_id` and cache in a Redis hash `nexus:task_meta:{parent_task_id}`; optionally update orchestrators to include `project_id` in task payloads at creation time.
    - Also add the child `task.id` to `nexus:task_group:{parent_task_id}` (Redis Set) when `parent_task_id` is known (Phase 0 is fine to include this; it simplifies snapshots).
  - `_worker(worker_id)`: publish `worker_started` on start and `worker_stopped` on exit; send `worker_heartbeat` every `MONITORING_HEARTBEAT_INTERVAL_SEC` (default 10s) with TTL `MONITORING_HEARTBEAT_TTL_SEC` (default 30s).
  - `_process_task(...)`:
    - Before execute: `task_started` (worker_id, task_type, `parent_task_id` as above).
    - On success: `_store_task_result` then `task_completed` (duration_ms, counts optional).
    - On exception:
      - If retry: `task_retry` with retry_count.
      - Else: `task_failed` with `error`.
  - Queue depth snapshot every 5–10s (single coordinator task): `queue_depth_update` for each priority key.

- `src/orchestration/data_aggregation_orchestrator.py` (`DataAggregationOrchestrator`):
  - On workflow start/end: `phase_started/phase_completed` for `enumeration`, `search`, `extraction`, `enrichment`, `resolution`, `persistence`, `csv_generation`.
  - After submitting batches (search, extraction): publish batch counts.
  - Periodic progress snapshot (every 5s while waiting): `stats_snapshot` with `{completed, failed, pending}` for that parent task. Use the `nexus:task_group:{parent_task_id}` set (child task IDs) and pipeline GET `nexus:task:{child_id}:status` for efficient counting.

  - Error isolation: Wrap all `publish()` calls in try/except and never block core processing. Truncate oversized `meta` fields to `MONITORING_MAX_EVENT_SIZE_BYTES`.

#### Key prefix standards and existing mismatch

- `ParallelTaskCoordinator` uses `nexus:task:{id}:status` and `nexus:tasks:{priority}`. Some verification code in `DataAggregationOrchestrator` currently checks `nexus:task_status:{id}:status` (note the extra `_status`). Standardize on `nexus:task:{id}:status` everywhere. Update verification code accordingly (low risk) rather than duplicating writes.

#### Task-group tracking (new)

- On `submit_tasks(...)`, when a task has `parent_task_id` (or payload `task_id`), add the child `task.id` to `nexus:task_group:{parent_task_id}` (Redis Set). This enables O(N) snapshot counting with a single pipeline.

### WebSocket Hub

- File: `src/api/monitoring_ws.py`
- Endpoint: `GET /ws/monitor`
  - Query params:
    - `project_id` (string, optional): if provided, subscribe to `nexus:events:project:{project_id}` and filter global stream accordingly.
    - `task_id` (string, optional): parent research task to filter events by.
    - `types` (csv, optional): subset of event types to forward, e.g. `task_started,task_completed,stats_snapshot`.
    - `stats_only` (bool, default false): if true, only subscribe to `nexus:events:stats`.
  - Behavior:
    - Accept WS, subscribe to channels, filter server-side, forward JSON lines (one event per message).
    - Send WS ping at interval (e.g., 25–30s). Close idle/slow clients without affecting publishers.
    - Graceful disconnect on client close or server shutdown.
  - Example URLs:
    - `ws://localhost:12000/ws/monitor`
    - `ws://localhost:12000/ws/monitor?project_id=default_project`
    - `ws://localhost:12000/ws/monitor?project_id=default_project&task_id=6ba5...&types=task_started,task_completed`
- Integration: mount router from root `api.py` (file path: `api.py`).

### Aggregates Producer (Phase 1)

- Background task in API process:
  - Every 2–5s compute global aggregates (workers online via heartbeats, queue depth per priority, in-progress counts by type) and publish `stats_snapshot` to `nexus:events:stats`.
  - Optionally per-project aggregates if low cost.

## Frontend Design (Next.js)

- New route: `nexus-frontend/app/monitoring/page.tsx` (or tab in existing UI).
- Hook: `nexus-frontend/lib/useMonitoringFeed.ts`:
  - Connect to `/ws/monitor` with optional `projectId`/`taskId`.
  - Auto-reconnect with expo backoff; buffer last N events; compute light aggregates client-side.
- Components:
  - `MonitoringDashboard.tsx` (layout + filters + summary header).
  - `GlobalStatsBar.tsx` (workers, queue depths, rates).
  - `InProgressTasks.tsx` (cards with per-phase progress bars).
  - `RecentEventsTable.tsx` (virtualized list, 200 rows).
  - `FailuresPanel.tsx`.
- UX:
  - Pause/resume stream toggle.
  - Filter by type (search/extract/enrich/resolve) and by status.

## Performance & Resilience

- Event rate: target < 200 events/sec under peak; aggregate/batch where possible (e.g., submit_tasks can emit batch summary plus per-task events behind a rate limiter).
- Backpressure: Drop or sample events server-side if a client lags (do not block workers).
- Timeouts: Redis publish with 100–200ms budget; failures are logged only.
- Recovery: If WS fails, client auto-reconnects; initial view can fetch a snapshot via `GET /monitor/snapshot` (optional fallback).
- Stalled task detection (Phase 1): if a task remains `processing` with no worker heartbeats owning it for > TTL, emit `task_stalled` and optionally requeue/mark failed.

### Project ID resolution algorithm (when missing)

1. Try `project_id = task.payload.get('project_id')`.
2. Else, compute `parent = task.parent_task_id or task.payload.get('task_id')`.
3. If `parent` exists, check Redis hash `nexus:task_meta:{parent}` for `project_id`.
4. If still missing, query KB: `global_kb.get_research_task(parent)` and read `project_id`.
5. Cache it back to `nexus:task_meta:{parent}` to avoid repeated lookups.
6. If not found, publish events without `project_id` (frontend should handle as "unknown").

## Security

- Dev default: no auth; CORS allowed for local frontend.
- Prod: require bearer token or cookie auth; enforce origin allowlist.

## Testing Plan

- Unit tests: `EventBus.publish()` resiliency, schema validation.
- Integration tests: spawn fake publisher, connect WS, assert receipt and filtering.
- Load test: simulate 1k events/sec briefly; ensure no worker slowdown.

### Dev testing quickstart

1) Start API server (root `api.py`) with Redis and Postgres available.
2) Create a Data Aggregation task to generate live events (replace placeholders):

```bash
curl -sS -X POST http://localhost:12000/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Private Schools GA",
    "research_query": "List and profile private K-12 schools in Georgia",
    "research_type": "data_aggregation",
    "user_id": "dev",
    "project_id": "default_project", 
    "data_aggregation_config": {
      "entities": ["private schools"],
      "attributes": ["address", "tuition", "enrollment"],
      "search_space": "in Georgia",
      "domain_hint": "schools"
    }
  }'
```

3) Connect a WebSocket client to `ws://localhost:12000/ws/monitor?project_id=default_project` and verify a stream of events.
4) Open the frontend monitoring page and confirm global stats, in-progress cards, and recent events populate in real time.

Notes:
- If `project_id` is missing in per-task payloads, add a one-time KB lookup on first event per `parent_task_id` and cache in `nexus:task_meta:{parent_task_id}`.

## Implementation Checklist

- [ ] Create `src/monitoring/event_bus.py` with `publish()` using `redis.asyncio` and env-configured channels; respect `NEXUS_MONITORING_ENABLED`.
- [ ] Instrument `src/orchestration/parallel_task_coordinator.py` at `submit_tasks`, `_worker`, `_process_task`, and queue-depth snapshotter.
- [ ] Add task-group Set writes to `nexus:task_group:{parent_task_id}` on submission when available.
- [ ] Instrument `src/orchestration/data_aggregation_orchestrator.py` with `phase_started/phase_completed` and periodic `stats_snapshot` using the task-group Set for counts.
- [ ] Add `src/api/monitoring_ws.py` with an `APIRouter` exposing `GET /ws/monitor` and server-side filtering.
- [ ] Mount the router in root `api.py`.
- [ ] Frontend: add `nexus-frontend/lib/useMonitoringFeed.ts`, `nexus-frontend/app/monitoring/page.tsx`, and UI components.
- [ ] Add env vars to `.env.example` and README snippets.
- [ ] Add unit/integration tests and a basic load probe.

### Pitfalls checklist (please verify while implementing)

- __Key mismatch__: Ensure all reads use `nexus:task:{id}:status` (not `nexus:task_status:*`).
- __No blocking__: Wrap `EventBus.publish()` in try/except; never let failures block task processing.
- __Event size__: Truncate `meta` to `MONITORING_MAX_EVENT_SIZE_BYTES` total payload; avoid dumping entire documents.
- __Sampling__: For very hot events (e.g., heartbeats), consider sampling if clients cannot keep up.
- __Channel fanout__: If publishing to both global and project channels, ensure the publish is best-effort and tolerant to failures.
- __Backpressure__: Drop messages to slow clients rather than blocking Redis subscription loop.
- __Feature flag__: Gate all instrumentation behind `NEXUS_MONITORING_ENABLED` to allow safe rollout.
- __Timezones__: Always UTC ISO8601 for timestamps.

## Acceptance Criteria

- __Event emission__: Task lifecycle and orchestrator phase events are published to `nexus:events` without slowing workers; includes `parent_task_id` and (when available) `project_id`.
- __Key standardization__: All status keys use `nexus:task:{id}:status`. Orchestrator verification updated accordingly.
- __Task-group tracking__: `nexus:task_group:{parent_task_id}` populated; snapshots compute `{completed, failed, pending}` using a pipeline.
- __WebSocket__: `GET /ws/monitor` streams events, supports `project_id`/`task_id`/`types` filters, and handles slow clients without backpressuring workers.
- __Frontend__: Monitoring page shows global stats, in-progress task cards with progress bars, recent events, and failures in real time.
- __Resilience__: Heartbeats published and TTL-ed; sampling and truncation guards in place; no crashes if Redis momentarily unavailable.

## Rollout Plan

1. Implement `EventBus` and WS hub behind `NEXUS_MONITORING_ENABLED`.
2. Instrument `ParallelTaskCoordinator` (P0 events) and `DataAggregationOrchestrator` phase events.
3. Ship frontend Monitoring page with global/project filters and live table + basic progress cards.
4. Add worker heartbeats and queue-depth snapshots (Phase 1).
5. Evaluate Redis Streams for replay (Phase 2).

## File/Code Touch List

- Backend:
  - `src/monitoring/event_bus.py` (new)
  - `src/api/monitoring_ws.py` (new); mount router in root `api.py`
  - `src/orchestration/parallel_task_coordinator.py` (instrument events)
  - `src/orchestration/data_aggregation_orchestrator.py` (phase events + snapshots)
- Frontend:
  - `nexus-frontend/lib/useMonitoringFeed.ts` (new)
  - `nexus-frontend/app/monitoring/page.tsx` (new)
  - `nexus-frontend/components/MonitoringDashboard/*.tsx` (new components)

## Open Questions

- Map `project_id` efficiently: include it in all task payloads upstream vs. lightweight KB lookup per event?
- Adopt Redis Streams now for replay vs. Pub/Sub only for MVP?
- Deduplicate events across processes if orchestrator and coordinator both emit similar signals (define authoritative sources per event type).
