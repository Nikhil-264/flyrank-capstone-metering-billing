from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class QuotaExceededException(Exception):
    """Raised when a tenant's metered usage would exceed its plan allowance (-> 429)."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        self.message = message
        # Seconds until the quota window resets. Surfaced as the Retry-After
        # header so machine callers can back off correctly.
        self.retry_after = retry_after


class PaymentRequiredException(Exception):
    """Raised when the plan itself does not permit the action (-> 402)."""

    def __init__(self, message: str):
        self.message = message


class InvalidUsageError(ValueError):
    """
    Domain-level bad input in the metering path (-> 400).

    Subclasses ``ValueError`` so service-layer call sites and their unit tests
    can still ``raise``/``pytest.raises(ValueError)``, but only *this* type is
    mapped to an HTTP 400 — an unexpected ``ValueError`` elsewhere still becomes
    a 500 instead of being silently masked as a client error.
    """


async def quota_exceeded_handler(
    request: Request, exc: QuotaExceededException
) -> JSONResponse:
    headers = {}
    if exc.retry_after is not None:
        headers["Retry-After"] = str(int(exc.retry_after))
    return JSONResponse(
        status_code=429,
        content={
            "error": "Quota Exceeded",
            "message": exc.message,
            "code": "QUOTA_EXCEEDED",
        },
        headers=headers,
    )


async def payment_required_handler(
    request: Request, exc: PaymentRequiredException
) -> JSONResponse:
    return JSONResponse(
        status_code=402,
        content={
            "error": "Payment Required",
            "message": exc.message,
            "code": "PAYMENT_REQUIRED",
        },
    )


async def invalid_usage_handler(request: Request, exc: InvalidUsageError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": "Bad Request",
            "message": str(exc),
            "code": "BAD_REQUEST",
        },
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Give boundary-validation failures the same envelope as every other error."""
    errors = exc.errors()
    try:
        first = errors[0]
        loc = ".".join(str(p) for p in first.get("loc", []))
        summary = f"{loc}: {first.get('msg', 'invalid')}" if loc else first.get("msg", "invalid")
    except (IndexError, KeyError, TypeError):
        summary = "Request validation failed."
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": summary,
            "code": "VALIDATION_ERROR",
            "detail": errors,  # kept for backwards compatibility
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(QuotaExceededException, quota_exceeded_handler)
    app.add_exception_handler(PaymentRequiredException, payment_required_handler)
    app.add_exception_handler(InvalidUsageError, invalid_usage_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
