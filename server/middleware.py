import time
import secrets

from fastapi import Request, Response, status
import structlog

logger = structlog.get_logger()


async def logging_middleware(request: Request, call_next) -> Response:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request.headers.get(
            "X-Appengine-Request-Log-Id", secrets.token_urlsafe()
        ),
        request={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None,
        },
    )

    logger.info("Request received")
    start = time.monotonic_ns()
    resp = await call_next(request)
    end = time.monotonic_ns()

    logger.info(
        "Request completed",
        request_duration_ms=(end - start) // 1_000_000,
        response={"status_code": resp.status_code},
    )
    return resp


async def header_check(request: Request, call_next):
    if request.url.path == "/":
        # Allow the root path to be accessed without port-check ehader
        return await call_next(request)

    if "X-Ray-Open-Port-Check" not in request.headers:
        return Response(
            status_code=status.HTTP_403_FORBIDDEN,
            content="Missing Ray header not found",
        )

    return await call_next(request)
