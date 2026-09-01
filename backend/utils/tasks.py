"""
tasks.py — Background task helpers for AI-Studio.

Provides the done_callback to log unhandled exceptions from asyncio.create_task().
asyncio.create_task exceptions are NOT caught by FastAPI's global exception handler,
so this callback ensures they appear in structured logs.
"""
import asyncio
from backend.utils.logger import get_logger

logger = get_logger("ai_studio.tasks")


def log_task_exception(task: asyncio.Task) -> None:
    """Done callback for background tasks — logs any unhandled exception.

    Usage:
        asyncio.create_task(my_coro()).add_done_callback(log_task_exception)
    """
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error(
            "background_task_exception",
            task_name=task.get_name(),
            error_type=type(exc).__name__,
            error=str(exc),
        )
