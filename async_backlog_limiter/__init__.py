import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import (
        AsyncGenerator,
        Callable,
    )
    from typing import AsyncContextManager


class RateLimitExceeded(Exception):
    """
    Raised when the total number of active and queued requests exceeds the
    allowed limit.
    """

    pass


def AsyncBacklogLimiter(
    capacity: int, queue_limit: int
) -> "Callable[[], AsyncContextManager[None]]":
    """
    AsyncBacklogLimiter simulates a server-like request handler with controlled
    concurrency and a bounded queue for pending tasks.

    It enforces two limits:
      - `capacity`: maximum number of concurrently executing tasks.
      - `queue_limit`: total number of active + waiting tasks allowed before
        rejecting new ones.

    This is conceptually similar to a thread pool with a TCP-style backlog:
    if too many requests are in progress or waiting, new ones are immediately
    rejected.

    Args:
        capacity (int): Max number of concurrently running tasks.
        queue_limit (int): Max number of total tasks (running + waiting).

    Returns:
        An async context manager that limits execution according to the
        configured capacity and queue.

    Raises:
        ValueError: If capacity or queue_limit values are invalid.
        RateLimitExceeded: If the queue is full and cannot accept more tasks.
    """
    if capacity <= 0:
        raise ValueError("Capacity must be greater than zero.")

    if queue_limit <= capacity:
        raise ValueError("Queue limit must be greater than the capacity.")

    queue_sem = asyncio.Semaphore(queue_limit)
    capacity_sem = asyncio.Semaphore(capacity)

    @asynccontextmanager
    async def manager() -> "AsyncGenerator[None, None]":
        if queue_sem.locked():
            raise RateLimitExceeded(
                "Too many pending requests in the backlog. Request rejected."
            )

        async with queue_sem, capacity_sem:
            yield

    return manager
