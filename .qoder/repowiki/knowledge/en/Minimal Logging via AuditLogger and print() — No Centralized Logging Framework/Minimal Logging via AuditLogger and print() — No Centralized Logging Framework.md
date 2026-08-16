---
kind: logging_system
name: Minimal Logging via AuditLogger and print() — No Centralized Logging Framework
category: logging_system
scope:
    - '**'
source_files:
    - agent2/audit/audit_logger.py
    - agent2/database/repositories/audit_repository.py
    - api/main.py
    - agent2/database/importer.py
    - agent2/database/db_manager.py
    - agent2/reasoning/criterion_mapper.py
    - agent2/reasoning/rejection_analyzer.py
    - agent2/submission/package_builder.py
    - agent2/submission/boundary_filter.py
---

## What system/approach is used

The repository does **not** use a centralized logging framework (no `logging`, `loguru`, `structlog`, `sentry_sdk`, or similar). There is no `logging.basicConfig` call, no log-level configuration, and no structured JSON logger. The only dedicated logging facility is a custom `AuditLogger` in `agent2/audit/audit_logger.py`, which persists audit events to SQLite and prints a human-readable summary line to stdout. All other output across the codebase is produced via bare `print()` calls.

## Key files and packages

- `agent2/audit/audit_logger.py` — the sole structured logging class; writes to `AuditRepository` (SQLite) and emits a formatted status line via `print()`.
- `agent2/database/repositories/audit_repository.py` — persistence layer for audit records (called by `AuditLogger`).
- `api/main.py` — FastAPI entry point; uses `print()` for startup/lifecycle messages and debug dumps gated by `DEBUG` env var / query parameter.
- `agent2/database/importer.py`, `agent2/database/db_manager.py` — data import scripts that emit progress/error via `print()`.
- `agent2/reasoning/criterion_mapper.py`, `agent2/reasoning/rejection_analyzer.py`, `agent2/submission/package_builder.py`, `agent2/submission/boundary_filter.py` — business modules that emit warnings and security notices through `print()`.

## Architecture and conventions

1. **Audit trail as the only structured sink.** `AuditLogger.log_transition(...)` records claim lifecycle state transitions (`state_before -> state_after`) with fields `audit_id`, `correlation_id`, `claim_id`, `claim_version`, `action`, `result`, `error`. Each event gets a generated `AUD-<uuid>` id and a per-run `A2RUN-<uuid>` correlation id. This is the only place where structured, persistent audit data is produced.

2. **Console-only operational logs.** Every non-audit message is a plain `print(...)` call — no formatting library, no timestamp, no severity level, no file/stderr routing. Messages are ad-hoc strings such as `[Warning] ...`, `[Security] ...`, or `================= DEBUG FOR {claim_id} =================` blocks.

3. **Debug gating via environment/query.** In `api/main.py`, verbose pipeline dumps are controlled by `os.getenv("DEBUG", "false")` and an optional `debug` query parameter on `/triage` and `/evaluate`. When disabled, only minimal startup `print()` lines appear.

4. **No cross-cutting log injection.** Modules do not accept a logger instance; they call `print()` directly. There is no dependency-injected logger, no context manager wrapping requests, and no middleware that attaches correlation IDs to console output.

5. **Audit events are decoupled from request flow.** `AuditLogger` is instantiated with an explicit `correlation_id` (e.g. the run id passed from the orchestrator), but there is no automatic propagation of this id into the surrounding `print()` statements outside audit entries.

## Conventions and constraints

- **Observed convention:** Operational progress and error reporting is done with `print()` at module scope; structured, queryable history is written exclusively through `AuditLogger.log_transition`.
- **Observed convention:** Debug output is opt-in via the `DEBUG` environment variable or the `debug` query parameter on API endpoints.
- **Observed convention:** Security-sensitive findings (e.g. blocked sensitive evidence) are printed with a `[Security]` prefix to make them visually distinct in stdout.
- **Constraint enforced by design:** Audit records always contain a stable `correlation_id` per run and a unique `audit_id` per event, enabling later reconstruction of a claim's full lifecycle from the SQLite audit table.
- **Not present:** No log levels (INFO/WARN/ERROR), no structured JSON log lines, no log rotation, no centralized configuration file for logging, no external sinks (file, syslog, cloud logging service).

In short, the repository relies on a thin, purpose-built audit subsystem for structured persistence and otherwise treats logging as informal console output via `print()`.