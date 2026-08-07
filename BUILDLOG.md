# BUILDLOG.md — Honest AI-Usage Log

Keep this running *during* the build, not reconstructed at the end.
Log anything non-trivial the AI wrote, fixed, or got wrong — including
mistakes and how they were caught. This is a credibility document, not
a highlight reel; per Harness doctrine, a caught-and-fixed AI mistake
that produced a rule update is more valuable to log than a clean
one-shot.

## Format
```
### [DATE] <short title>
- Prompted for:
- AI produced:
- Accepted as-is / modified / rejected because:
- If rejected or buggy: root cause + link to learnings.md entry, if any
```

## Log

### 2026-08-07 conftest.py event loop mismatch fix
- Prompted for: Fixing `InterfaceError: cannot perform operation: another operation is in progress` during tests.
- AI produced: Reconfigured conftest database engine and connection fixtures to be function-scoped rather than session-scoped, resolving the asyncpg loop mismatch.
- Accepted as-is / modified / rejected because: Accepted as-is, fixes asyncpg loop mismatch.
- If rejected or buggy: root cause + link to learnings.md entry, if any: event loop mismatch (recorded in learnings.md).

### 2026-08-07 concurrency test deadlock fix
- Prompted for: Fixing hang/stuck pytest on concurrent race condition test.
- AI produced: Redesigned the concurrency test to use a delayed background commit task for session 1, allowing session 2 to block on flush and unblock cleanly when session 1 commits (simulating a real production race condition).
- Accepted as-is / modified / rejected because: Accepted as-is, resolving the postgres uncommitted concurrent insert deadlock.
- If rejected or buggy: root cause + link to learnings.md entry, if any: concurrent uncommitted insert deadlock (recorded in learnings.md).

### 2026-08-07 conftest type hint NameError fix
- Prompted for: Fixing `NameError: name 'AsyncClient' is not defined` error when starting pytest.
- AI produced: Imported `AsyncClient` from `httpx` at the top level of `conftest.py` instead of only inside the fixture definition.
- Accepted as-is / modified / rejected because: Accepted as-is, fixes import dependency for type hinting.

### 2026-08-07 conftest client get_db override fix
- Prompted for: Fixing `RuntimeError` and `InterfaceError` related to mismatched event loops during integration tests.
- AI produced: Overrode FastAPI's `get_db` dependency in the `client` fixture inside `conftest.py` to yield the shared test session `db`.
- Accepted as-is / modified / rejected because: Accepted as-is, guarantees same loop/session usage inside API requests during integration tests.
- If rejected or buggy: root cause + link to learnings.md entry, if any: event loop mismatch in integration tests (recorded in learnings.md).

### 2026-08-07 API calls quota check fix
- Prompted for: Fixing API call quota boundary test failure (request #1001 passing instead of returning 429).
- AI produced: Updated `QuotaService.check_quota()` to count `ai_token` event rows (generation requests) towards the API calls limit.
- Accepted as-is / modified / rejected because: Accepted as-is, accurately aggregates all API requests.
- If rejected or buggy: root cause + link to learnings.md entry, if any: token events not counted as API calls (recorded in learnings.md).





