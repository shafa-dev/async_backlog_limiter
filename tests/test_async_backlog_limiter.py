import asyncio
from unittest import IsolatedAsyncioTestCase

from async_backlog_limiter import (
    AsyncBacklogLimiter,
    RateLimitExceeded,
)


class TestAsyncBacklogLimiter(IsolatedAsyncioTestCase):

    def test_invalid_capacity(self):
        with self.assertRaises(ValueError):
            AsyncBacklogLimiter(0, 2)

    def test_invalid_queue_limit(self):
        with self.assertRaises(ValueError):
            AsyncBacklogLimiter(2, 2)

    async def test_allows_within_capacity(self):
        limiter = AsyncBacklogLimiter(capacity=1, queue_limit=5)
        async with limiter():
            await asyncio.sleep(0.01)

    async def test_allows_concurrent_tasks_within_limits(self):
        capacity = 2
        queue_limit = 5
        limiter = AsyncBacklogLimiter(capacity, queue_limit)
        results = []

        async def task():
            async with limiter():
                results.append(1)
                await asyncio.sleep(0.01)

        tasks = [asyncio.create_task(task()) for _ in range(queue_limit)]
        await asyncio.gather(*tasks)
        self.assertEqual(len(results), queue_limit)

        # Repeat to ensure reusability
        results.clear()
        tasks = [asyncio.create_task(task()) for _ in range(queue_limit)]
        await asyncio.gather(*tasks)
        self.assertEqual(len(results), queue_limit)

    async def test_rejects_when_backlog_exceeded(self):
        capacity = 2
        queue_limit = 5
        limiter = AsyncBacklogLimiter(capacity, queue_limit)
        results = []

        async def task():
            async with limiter():
                await asyncio.sleep(0.1)
                results.append(1)

        tasks = [asyncio.create_task(task()) for _ in range(queue_limit)]
        await asyncio.sleep(0.01)

        # This should raise because backlog is full
        with self.assertRaises(RateLimitExceeded):
            async with limiter():
                pass

        await asyncio.gather(*tasks)
        self.assertEqual(len(results), queue_limit)

        # Repeat to ensure reusability
        results.clear()
        tasks = [asyncio.create_task(task()) for i in range(queue_limit)]
        await asyncio.gather(*tasks)
        self.assertEqual(len(results), queue_limit)

    async def test_gather_handles_rejections(self):
        capacity = 2
        queue_limit = 5
        limiter = AsyncBacklogLimiter(capacity, queue_limit)

        async def task():
            async with limiter():
                await asyncio.sleep(0.1)
                return True

        tasks = [asyncio.create_task(task()) for _ in range(queue_limit * 2)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successes = [r for r in results if r is True]
        failures = [r for r in results if isinstance(r, RateLimitExceeded)]

        self.assertEqual(len(successes), queue_limit)
        self.assertEqual(len(failures), queue_limit)

    async def test_exception_does_not_block_future_requests(self):
        capacity = 1
        queue_limit = 2
        limiter = AsyncBacklogLimiter(capacity, queue_limit)

        async def faulty_task():
            async with limiter():
                raise RuntimeError("Intentional failure")

        async def safe_task():
            async with limiter():
                return "ok"

        # Ensure that exceptions don't cause deadlocks or leaks
        for _ in range(queue_limit * 2):
            with self.assertRaises(RuntimeError):
                await faulty_task()

        for _ in range(queue_limit * 2):
            result = await safe_task()
            self.assertEqual(result, "ok")

    async def test_concurrent_task_count_never_exceeds_capacity(self):
        test_cases = [
            (1, 2),
            (1, 10),
            (5, 10),
            (9, 10),
        ]

        for capacity, queue_limit in test_cases:
            limiter = AsyncBacklogLimiter(capacity, queue_limit)
            active = 0
            max_concurrent = 0
            lock = asyncio.Lock()

            async def monitored_task():
                nonlocal active, max_concurrent
                async with limiter():
                    async with lock:
                        active += 1
                        max_concurrent = max(max_concurrent, active)
                    await asyncio.sleep(0.05)
                    async with lock:
                        active -= 1

            with self.subTest(
                f"capacity={capacity}, queue_limit={queue_limit}"
            ):
                tasks = [
                    asyncio.create_task(monitored_task()) for _ in range(20)
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
                self.assertLessEqual(max_concurrent, 0)
