from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class QuotaExceededException(Exception):
    def __init__(self, message: str):
        self.message = message

class PaymentRequiredException(Exception):
    def __init__(self, message: str):
        self.message = message

async def quota_exceeded_handler(request: Request, exc: QuotaExceededException) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": "Quota Exceeded",
            "message": exc.message,
            "code": "QUOTA_EXCEEDED"
        }
    )

async def payment_required_handler(request: Request, exc: PaymentRequiredException) -> JSONResponse:
    return JSONResponse(
        status_code=402,
        content={
            "error": "Payment Required",
            "message": exc.message,
            "code": "PAYMENT_REQUIRED"
        }
    )

def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(QuotaExceededException, quota_exceeded_handler)
    app.add_exception_handler(PaymentRequiredException, payment_required_handler)
