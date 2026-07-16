"""
Lightweight header-normalization middleware for authenticated routes.

Note: actual auth *enforcement* happens via the `get_current_user` dependency
(app/api/deps.py) so that OpenAPI docs correctly reflect which routes require
a token. This middleware only handles cross-cutting concerns such as
rejecting obviously malformed Authorization headers early.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class AuthHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization")
        if auth_header is not None and not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "MALFORMED_AUTH_HEADER",
                        "message": "Authorization header must use the 'Bearer <token>' scheme",
                        "details": {},
                    }
                },
            )
        return await call_next(request)
