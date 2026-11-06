# Resilience Patterns

## Retry with Exponential Backoff

```python
async def with_retry(fn, max_attempts=3, base_delay=1.0, max_delay=30.0):
    for attempt in range(max_attempts):
        try:
            return await fn()
        except TransientError as e:
            if attempt == max_attempts - 1:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            await asyncio.sleep(delay + random.uniform(0, 0.1))
```

## Circuit Breaker

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state = "closed"
        self.last_failure = None

    async def call(self, fn):
        if self.state == "open":
            if time.time() - self.last_failure > self.timeout:
                self.state = "half-open"
            else:
                raise CircuitOpenError()

        try:
            result = await fn()
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def on_success(self):
        self.failures = 0
        self.state = "closed"

    def on_failure(self):
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"
```

## Bulkhead

- Isolate critical resources (thread pools, connections)
- Separate pools per downstream service
- Prevent cascade failures

## Timeout Budgets

- Set per-operation timeouts
- Total request budget (e.g., 500ms)
- Allocate to downstream calls proportionally
- Fail fast when budget exceeded

## Rate Limiting

- Token bucket for smooth limiting
- Leaky bucket for strict limiting
- Distributed: Redis-based
- Per-user, per-IP, per-endpoint

## Graceful Degradation

- Feature flags for non-critical features
- Fallback responses (cached, default, empty)
- Read-only mode during issues
- Queue non-critical work

## Health Checks

- Liveness: Process alive (k8s probe)
- Readiness: Can serve traffic
- Startup: Initialization complete
- Deep: Dependencies reachable

## Chaos Engineering

- Regular failure injection
- Game days with team
- Automated in staging
- Blast radius control
