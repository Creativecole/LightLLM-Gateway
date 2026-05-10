"""In-memory metrics collector."""

import asyncio
from collections import defaultdict
from typing import Any


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._total_requests = 0
        self._success_requests = 0
        self._failed_requests = 0
        self._active_requests = 0
        self._cache_hits = 0
        self._total_latency_ms = 0.0
        self._total_ttft_ms = 0.0
        self._ttft_count = 0
        self._requests_per_model: dict[str, int] = defaultdict(int)
        self._requests_per_backend: dict[str, int] = defaultdict(int)

    async def start_request(self, *, model: str, backend: str | None) -> None:
        async with self._lock:
            self._total_requests += 1
            self._active_requests += 1
            self._requests_per_model[model] += 1
            if backend is not None:
                self._requests_per_backend[backend] += 1

    async def finish_request(
        self,
        *,
        success: bool,
        cache_hit: bool,
        latency_ms: float,
        ttft_ms: float | None = None,
    ) -> None:
        async with self._lock:
            self._active_requests = max(0, self._active_requests - 1)
            if success:
                self._success_requests += 1
            else:
                self._failed_requests += 1
            if cache_hit:
                self._cache_hits += 1
            self._total_latency_ms += latency_ms
            if ttft_ms is not None:
                self._total_ttft_ms += ttft_ms
                self._ttft_count += 1

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            completed_requests = self._success_requests + self._failed_requests
            avg_latency_ms = (
                self._total_latency_ms / completed_requests if completed_requests else 0.0
            )
            avg_ttft_ms = self._total_ttft_ms / self._ttft_count if self._ttft_count else 0.0
            cache_hit_rate = self._cache_hits / self._success_requests if self._success_requests else 0.0
            error_rate = self._failed_requests / self._total_requests if self._total_requests else 0.0

            return {
                "total_requests": self._total_requests,
                "success_requests": self._success_requests,
                "failed_requests": self._failed_requests,
                "active_requests": self._active_requests,
                "cache_hits": self._cache_hits,
                "cache_hit_rate": cache_hit_rate,
                "avg_latency_ms": avg_latency_ms,
                "avg_ttft_ms": avg_ttft_ms,
                "requests_per_model": dict(self._requests_per_model),
                "requests_per_backend": dict(self._requests_per_backend),
                "error_rate": error_rate,
            }
