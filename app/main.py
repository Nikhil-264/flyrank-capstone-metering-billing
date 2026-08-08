from fastapi import FastAPI
from app.api.errors import register_error_handlers
from app.api.generate import router as generate_router
from app.api.checkout import router as checkout_router
from app.api.webhooks.stripe import router as stripe_webhook_router
from app.api.usage import router as usage_router

app = FastAPI(
    title="Usage Metering & Billing Engine",
    description="A multi-tenant usage metering, quota enforcement, and billing service.",
    version="1.0.0"
)

# Register custom exception handlers for 429 and 402 errors
register_error_handlers(app)

# Include routes
app.include_router(generate_router, tags=["Generation"])
app.include_router(checkout_router, tags=["Checkout"])
app.include_router(stripe_webhook_router, tags=["Stripe Webhook"])
app.include_router(usage_router, tags=["Usage"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}
