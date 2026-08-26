"""
logger.py — Structured JSON logging via structlog.

Every log entry includes:
  provider, model, job_id, latency_ms, status, retry_count
as standard fields when available (bound via contextvars).
"""
import logging
import sys
import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Call once at application startup."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # Final renderer: JSON for machine-parseable output
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def get_logger(name: str = "ai_studio") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


# Convenience: bind job context into contextvars for the current async task
def bind_job_context(
    *,
    job_id: str = "",
    provider: str = "",
    model: str = "",
    mode: str = "",
) -> None:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        job_id=job_id,
        provider=provider,
        model=model,
        mode=mode,
    )
