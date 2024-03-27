import asyncio
import logging
import random

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
import structlog

from api import OpenPortCheckRequest, OpenPortCheckResponse
from middleware import logging_middleware, header_check
from open_port_checker import tcp_open_port_check


structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
logger = structlog.get_logger()

app = FastAPI()
app.middleware("http")(logging_middleware)
app.middleware("http")(header_check)


@app.get("/", include_in_schema=False)
async def root():
    return PlainTextResponse(  # HTML-ify this
        "Hello! You've found the Ray Cluster Open Port Checker."
        " This is used by users of Ray to validate that they have"
        " not accidentially exposed ports that allow arbitrary code"
        " execution to internet users."
        # TODO: Add more details
        # TODO: Add link to explation
    )


@app.post("/open-port-check")
async def open_port_check(
    request: OpenPortCheckRequest, raw_request: Request
) -> OpenPortCheckResponse:
    if not raw_request.client:
        raise HTTPException(status_code=500, detail="Failed to find client IP address")
    client = raw_request.client.host

    logger.debug("Received open port check", ports=request.ports)
    logger.info(
        "Checking open ports",
        ports_requested_count=len(request.ports),
        ports_requested_sample=sorted(
            random.sample(request.ports, k=min(10, len(request.ports)))
        ),
    )

    results = await asyncio.gather(
        *(tcp_open_port_check(client, port) for port in request.ports)
    )
    open_ports = [port for port, is_open in results if is_open]

    if len(open_ports) > 0:
        logger.warning("Open ports found", open_ports=open_ports)
    else:
        logger.info(
            "No open ports found",
            ports_checked_count=len(request.ports),
        )

    return OpenPortCheckResponse(
        open_ports=open_ports,
        checked_ports=request.ports,
    )
