# Async Backlog Limiter

A lightweight, zero-dependency Python library to limit concurrent execution and queue size of asynchronous tasks — simulating a TCP-style backlog for async servers, job runners, or microservices to ensure overload protection.


## 📦 Installation

```
pip install async-backlog-limiter
```

## 🛠️ Usage

- If more than `capacity` concurrent requests are running, additional ones will wait.
- If the `total number of active + waiting` requests exceeds `queue_limit`, new ones are immediately rejected with a `RateLimitExceeded` exception.

```python
import asyncio
from async_backlog_limiter import AsyncBacklogLimiter, RateLimitExceeded

limiter = AsyncBacklogLimiter(capacity=5, queue_limit=10)

async def handle_request():
    try:
        async with limiter():
            # Your async work here
            await asyncio.sleep(1)
    except RateLimitExceeded:
        print("Request rejected due to overload.")

# Run many tasks
await asyncio.gather(*[handle_request() for _ in range(20)])
```

## 🧪 Tests

This project includes a comprehensive test suite using unittest.

To run tests:

```
python -m unittest discover -s tests
```
