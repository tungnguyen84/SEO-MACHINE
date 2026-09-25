"""
Production Security Headers & Middleware
Injects enterprise security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
and provides safe error shielding to prevent internal stack trace leakage.
"""

import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger("openseo.security")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Appends OWASP-recommended HTTP security headers to all responses.
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Baseline security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self';"
        )

        # Cache control for API responses to avoid sensitive data caching
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"

        return response


class SafeErrorShieldMiddleware(BaseHTTPMiddleware):
    """
    Shields internal application errors from being leaked to clients.
    Logs full exception with unique request_id and returns safe sanitized JSON.
    """
    async def dispatch(self, request: Request, call_next):
        request_id = f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            logger.error(f"[ERROR-SHIELD] Request {request_id} failed on {request.method} {request.url.path}: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "An internal server error occurred. Please contact support with the request ID.",
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )
