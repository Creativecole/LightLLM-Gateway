#!/usr/bin/env python
"""Async benchmark client for LightLLM-Gateway."""

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx


@dataclass(frozen=True)
class BenchmarkConfig:
    url: str
    api_key: str
    model: str
    concurrency: int
    requests: int
    stream: bool
    prompt: str
    output: Path


@dataclass(frozen=True)
class RequestResult:
    success: bool
    latency_ms: float
    error: str | None = None


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]

    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * percentile_value
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def calculate_metrics(
    results: list[RequestResult],
    total_time_seconds: float,
    *,
    stream: bool,
) -> dict[str, float | int]:
    latencies = [result.latency_ms for result in results if result.success]
    total_requests = len(results)
    success = len(latencies)
    failed = total_requests - success

    metrics: dict[str, float | int] = {
        "total_requests": total_requests,
        "success": success,
        "failed": failed,
        "avg_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
        "min_latency_ms": min(latencies) if latencies else 0.0,
        "max_latency_ms": max(latencies) if latencies else 0.0,
        "throughput_req_per_sec": total_requests / total_time_seconds
        if total_time_seconds > 0
        else 0.0,
        "error_rate": failed / total_requests if total_requests else 0.0,
        "total_time_seconds": total_time_seconds,
    }
    if stream:
        metrics["avg_stream_latency_ms"] = metrics["avg_latency_ms"]
    return metrics


def render_report(
    config: BenchmarkConfig,
    metrics: dict[str, float | int],
    *,
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.now(UTC)
    conclusion = _conclusion(metrics)
    metric_rows = "\n".join(
        f"| {name} | {_format_metric(value)} |" for name, value in metrics.items()
    )
    return f"""# LightLLM-Gateway Benchmark Report

Generated at: {generated_at.isoformat()}

## Parameters

| Parameter | Value |
| --- | --- |
| url | `{config.url}` |
| model | `{config.model}` |
| concurrency | {config.concurrency} |
| requests | {config.requests} |
| stream | {config.stream} |
| prompt | `{config.prompt}` |

## Metrics

| Metric | Value |
| --- | ---: |
{metric_rows}

## Conclusion

{conclusion}
"""


async def run_benchmark(config: BenchmarkConfig) -> tuple[list[RequestResult], float]:
    semaphore = asyncio.Semaphore(config.concurrency)
    timeout = httpx.Timeout(60.0)
    started_at = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [_send_with_semaphore(client, config, semaphore) for _ in range(config.requests)]
        results = await asyncio.gather(*tasks)
    total_time_seconds = time.perf_counter() - started_at
    return results, total_time_seconds


async def _send_with_semaphore(
    client: httpx.AsyncClient,
    config: BenchmarkConfig,
    semaphore: asyncio.Semaphore,
) -> RequestResult:
    async with semaphore:
        return await _send_request(client, config)


async def _send_request(client: httpx.AsyncClient, config: BenchmarkConfig) -> RequestResult:
    payload = {
        "model": config.model,
        "messages": [{"role": "user", "content": config.prompt}],
        "stream": config.stream,
    }
    headers = {"Authorization": f"Bearer {config.api_key}"}
    started_at = time.perf_counter()
    try:
        if config.stream:
            async with client.stream("POST", config.url, json=payload, headers=headers) as response:
                if response.status_code < 200 or response.status_code >= 300:
                    latency_ms = _elapsed_ms(started_at)
                    return RequestResult(False, latency_ms, f"HTTP {response.status_code}")
                async for _line in response.aiter_lines():
                    pass
        else:
            response = await client.post(config.url, json=payload, headers=headers)
            if response.status_code < 200 or response.status_code >= 300:
                latency_ms = _elapsed_ms(started_at)
                return RequestResult(False, latency_ms, f"HTTP {response.status_code}")
        return RequestResult(True, _elapsed_ms(started_at))
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        return RequestResult(False, _elapsed_ms(started_at), str(exc))


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_args() -> BenchmarkConfig:
    parser = argparse.ArgumentParser(description="Benchmark LightLLM-Gateway chat completions.")
    parser.add_argument("--url", default="http://localhost:8000/v1/chat/completions")
    parser.add_argument("--api-key", default="sk-demo")
    parser.add_argument("--model", default="llama3.1")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--prompt", default="hello")
    parser.add_argument("--output", type=Path, default=Path("reports/benchmark.md"))
    args = parser.parse_args()
    return BenchmarkConfig(
        url=args.url,
        api_key=args.api_key,
        model=args.model,
        concurrency=args.concurrency,
        requests=args.requests,
        stream=args.stream,
        prompt=args.prompt,
        output=args.output,
    )


def print_results(metrics: dict[str, float | int]) -> None:
    print("\nLightLLM-Gateway Benchmark")
    print("==========================")
    for name, value in metrics.items():
        print(f"{name}: {_format_metric(value)}")


async def async_main() -> None:
    config = parse_args()
    results, total_time_seconds = await run_benchmark(config)
    metrics = calculate_metrics(results, total_time_seconds, stream=config.stream)
    report = render_report(config, metrics)
    write_report(config.output, report)
    print_results(metrics)
    print(f"\nReport written to: {config.output}")


def _format_metric(value: float | int) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _conclusion(metrics: dict[str, float | int]) -> str:
    success = int(metrics["success"])
    failed = int(metrics["failed"])
    error_rate = float(metrics["error_rate"])
    if failed == 0:
        return f"All {success} requests succeeded with no observed errors."
    return f"{success} requests succeeded and {failed} failed. Error rate was {error_rate:.2%}."


def _elapsed_ms(started_at: float) -> float:
    return (time.perf_counter() - started_at) * 1000


if __name__ == "__main__":
    asyncio.run(async_main())
