from datetime import UTC, datetime
from pathlib import Path

from scripts.bench import BenchmarkConfig, RequestResult, calculate_metrics, percentile, render_report


def test_percentile_empty_and_interpolated_values() -> None:
    assert percentile([], 0.95) == 0.0
    assert percentile([10.0], 0.95) == 10.0
    assert percentile([10.0, 20.0, 30.0], 0.50) == 20.0
    assert percentile([10.0, 20.0, 30.0], 0.95) == 29.0


def test_calculate_metrics() -> None:
    metrics = calculate_metrics(
        [
            RequestResult(success=True, latency_ms=10.0),
            RequestResult(success=True, latency_ms=30.0),
            RequestResult(success=False, latency_ms=50.0, error="HTTP 500"),
        ],
        total_time_seconds=2.0,
        stream=False,
    )

    assert metrics["total_requests"] == 3
    assert metrics["success"] == 2
    assert metrics["failed"] == 1
    assert metrics["avg_latency_ms"] == 20.0
    assert metrics["p50_latency_ms"] == 20.0
    assert metrics["min_latency_ms"] == 10.0
    assert metrics["max_latency_ms"] == 30.0
    assert metrics["throughput_req_per_sec"] == 1.5
    assert metrics["error_rate"] == 1 / 3


def test_stream_metrics_include_avg_stream_latency() -> None:
    metrics = calculate_metrics(
        [RequestResult(success=True, latency_ms=42.0)],
        total_time_seconds=1.0,
        stream=True,
    )

    assert metrics["avg_stream_latency_ms"] == 42.0


def test_render_report_contains_parameters_and_metrics() -> None:
    config = BenchmarkConfig(
        url="http://localhost:8000/v1/chat/completions",
        api_key="sk-demo",
        model="mock-small",
        concurrency=2,
        requests=5,
        stream=False,
        prompt="hello",
        output=Path("reports/benchmark.md"),
    )
    metrics = {
        "total_requests": 5,
        "success": 5,
        "failed": 0,
        "avg_latency_ms": 12.3,
        "p50_latency_ms": 10.0,
        "p95_latency_ms": 20.0,
        "min_latency_ms": 8.0,
        "max_latency_ms": 22.0,
        "throughput_req_per_sec": 4.0,
        "error_rate": 0.0,
        "total_time_seconds": 1.25,
    }

    report = render_report(
        config,
        metrics,
        generated_at=datetime(2026, 5, 10, tzinfo=UTC),
    )

    assert "# LightLLM-Gateway Benchmark Report" in report
    assert "| concurrency | 2 |" in report
    assert "| total_requests | 5 |" in report
    assert "All 5 requests succeeded" in report
