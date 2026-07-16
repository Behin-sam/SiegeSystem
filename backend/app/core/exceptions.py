"""
Application-wide exception hierarchy and FastAPI exception handlers.
Every handled error returns a consistent JSON envelope:

{
  "error": {
    "code": "SOME_ERROR_CODE",
    "message": "Human readable message",
    "details": {...}   # optional
  }
}
"""
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for all predictable, application-raised errors."""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None):
        super().__init__(message, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND, details=details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Not authenticated", details: dict[str, Any] | None = None):
        super().__init__(message, code="UNAUTHORIZED", status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Not authorized", details: dict[str, Any] | None = None):
        super().__init__(message, code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN, details=details)


class ConflictError(AppError):
    def __init__(self, message: str = "Resource conflict", details: dict[str, Any] | None = None):
        super().__init__(message, code="CONFLICT", status_code=status.HTTP_409_CONFLICT, details=details)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation failed", details: dict[str, Any] | None = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)


def _error_envelope(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logger.warning("app_error", code=exc.code, path=str(request.url), message=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        logger.warning("validation_error", path=str(request.url), errors=exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_envelope(
                "VALIDATION_ERROR",
                "Request validation failed",
                {"errors": exc.errors()},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning("http_error", status_code=exc.status_code, path=str(request.url))
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_envelope("HTTP_ERROR", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", path=str(request.url), exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope("INTERNAL_SERVER_ERROR", "An unexpected error occurred"),
        )
