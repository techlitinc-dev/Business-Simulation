"""structlog configuration: JSON logs in production, pretty console in debug.

Also hosts the request-ID middleware helper: every request gets a
``X-Request-ID`` (client-supplied or generated), bound to structlog
contextvars so all log lines in that request carry it, and echoed back
in the response header (T48).
"""

import logging
import sys
import uuid

import structlog
from fastapi import Request
from structlog.types import Processor


def setup_logging(*, debug: bool = False) -> None:
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    final_processor: Processor
    if debug:
        final_processor = structlog.dev.ConsoleRenderer()
    else:
        shared_processors.append(structlog.processors.TimeStamper(fmt="iso"))
        final_processor = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, final_processor],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route stdlib "uvicorn" / "sqlalchemy" logs through structlog's formatting too.
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)


def bind_request_id(request: Request) -> str:
    """Bind the request's ``X-Request-ID`` to structlog contextvars.

    Reads the client-supplied header or generates a fresh ``uuid4().hex``,
    binds it (so every log line in this request carries it), and returns it
    so the caller can echo it back as a response header.
    """
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    structlog.contextvars.bind_contextvars(request_id=request_id)
    return request_id
