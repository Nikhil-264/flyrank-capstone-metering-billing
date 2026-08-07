# Stack — Locked Choices & Why

Per Harness Engineering principle: prioritize built-in tools and
proven libraries over custom tooling until the foundation is proven.

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Chosen lane (see project setup) |
| Framework | FastAPI | Async, typed request/response models, free |
| DB | PostgreSQL via Docker Compose | Free, matches production-shape DB; SQLite acceptable fallback for quick local tests only, not for submission |
| ORM/migrations | SQLAlchemy 2.x + Alembic | Explicit migrations = real persistence per capstone shared-requirement #4 |
| Payments | Stripe test mode + Stripe CLI | Free, no card, exact webhook shapes |
| Testing | pytest + pytest-asyncio + httpx (ASGI test client) | Standard FastAPI testing stack |
| Containerization | Docker Compose | "A stranger can run it" with one command |

## Non-goals for this stack
- No AI provider SDK — tokens are simulated counts (`tech-debt-tracker.md`).
- No ORM abstraction beyond SQLAlchemy — an extra repository layer is
  optional, not required, given the "Architecture: swap without
  touching business logic" bar can be met with service-layer
  boundaries alone.
