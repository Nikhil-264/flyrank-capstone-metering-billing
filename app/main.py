from fastapi import FastAPI
from app.api.errors import register_error_handlers
from app.api.generate import router as generate_router

app = FastAPI(
    title="Usage Metering & Billing Engine",
    description="A multi-tenant usage metering, quota enforcement, and billing service.",
    version="1.0.0"
)

# Register custom exception handlers for 429 and 402 errors
register_error_handlers(app)

# Include routes
app.include_router(generate_router, tags=["Generation"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}
