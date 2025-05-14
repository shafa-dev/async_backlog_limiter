import asyncio
from contextlib import asynccontextmanager
from typing import (
    TYPE_CHECKING,
    NamedTuple,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class Stats(NamedTuple):
    active: int
    pending: int


class RateLimitExceeded(Exception):
    """
    Raised when the total number of active and queued requests exceeds the
    allowed limit.
    """

    pass


class AsyncBacklogLimiter:
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

    def __init__(self, capacity: int, queue_limit: int) -> None:
        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero.")

        if queue_limit <= capacity:
            raise ValueError("Queue limit must be greater than the capacity.")

        self.queue_sem = asyncio.Semaphore(queue_limit)
        self.capacity_sem = asyncio.Semaphore(capacity)
        self.capacity = capacity
        self.queue_limit = queue_limit

    @asynccontextmanager
    async def __call__(self) -> "AsyncGenerator[None, None]":
        if self.queue_sem.locked():
            raise RateLimitExceeded(
                "Too many pending requests in the backlog. Request rejected."
            )

        async with self.queue_sem, self.capacity_sem:
            yield

    def stats(self) -> Stats:
        """
        Returns current statistics about the limiter's state.

        - active:  The number of tasks currently executing within capacity.
        - pending: The number of tasks waiting in the queue for a slot.

        """

        active_queue = self.capacity - self.capacity_sem._value
        common_queue = self.queue_limit - self.queue_sem._value
        return Stats(
            active=active_queue,
            pending=common_queue - active_queue,
        )

    def __repr__(self) -> str:
        return (
            "<AsyncBacklogLimiter "
            f"capacity={self.capacity} "
            f"queue_limit={self.queue_limit}"
            ">"
        )
