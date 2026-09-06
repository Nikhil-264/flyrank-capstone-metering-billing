import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import settings
from app.api.errors import register_error_handlers
from app.api.generate import router as generate_router
from app.api.checkout import router as checkout_router
from app.api.webhooks.stripe import router as stripe_webhook_router
from app.api.usage import router as usage_router
from app.api.admin_jobs import router as admin_jobs_router

logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = None
    if settings.ENABLE_SCHEDULER:
        # Imported lazily so the test suite never pulls in APScheduler.
        from app.jobs.scheduler import start_scheduler, shutdown_scheduler

        scheduler = (start_scheduler, shutdown_scheduler)
        scheduler[0]()
    else:
        logger.info("Scheduler disabled (ENABLE_SCHEDULER=false)")
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler[1]()


app = FastAPI(
    title="Usage Metering & Billing Engine",
    description="A multi-tenant usage metering, quota enforcement, and billing service.",
    version="1.1.0",
    lifespan=lifespan,
)

# Register custom exception handlers (429 / 402 / 400 / 422 envelopes)
register_error_handlers(app)

# Routes
app.include_router(generate_router, tags=["Generation"])
app.include_router(checkout_router, tags=["Checkout"])
app.include_router(stripe_webhook_router, tags=["Stripe Webhook"])
app.include_router(usage_router, tags=["Usage"])
app.include_router(admin_jobs_router, tags=["Admin / Jobs"])


@app.get("/health")
def health_check():
    return {"status": "healthy"}
