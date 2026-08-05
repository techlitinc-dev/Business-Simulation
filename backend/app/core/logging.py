"""structlog configuration: JSON logs in production, pretty console in debug."""

import logging
import sys

import structlog
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
