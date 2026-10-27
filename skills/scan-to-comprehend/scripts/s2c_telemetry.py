"""Opt-in OpenTelemetry spans for one S2C run, with an explicit attribute allowlist."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from typing import Iterator


# Do not add raw URLs, page content, prompts, screenshot paths, or exception messages.
ALLOWED_ATTRIBUTES = frozenset({
    "s2c.run.id", "s2c.input.kind", "s2c.mode", "s2c.stage.mode",
    "s2c.capture.frame_count", "s2c.capture.bytes",
    "s2c.robots.status", "s2c.network.request_count", "s2c.network.blocked_count",
    "s2c.source.finding_count", "s2c.rule.pass_count",
    "s2c.rule.warning_count", "s2c.rule.review_count",
    "s2c.rule.not_checked_count", "s2c.rubric.version",
    "s2c.attention.frame_count", "s2c.report.bytes", "s2c.error.type",
})


class _NoopSpan:
    def set_attribute(self, _key: str, _value: object) -> None:
        pass

    def get_span_context(self) -> None:
        return None


class _SafeSpan:
    def __init__(self, span: object) -> None:
        self._span = span

    def set_attribute(self, key: str, value: object) -> None:
        if key not in ALLOWED_ATTRIBUTES:
            raise ValueError(f"Telemetry attribute is not allowed: {key}")
        self._span.set_attribute(key, value)

    def get_span_context(self) -> object:
        return self._span.get_span_context()


@dataclass
class Telemetry:
    """A private provider avoids changing another application's global tracer."""

    tracer: object | None = None
    provider: object | None = None
    exporter: object | None = None
    _finished: bool = False
    _flush_completed: bool = True

    @classmethod
    def create(cls, enabled: bool, endpoint: str | None = None) -> Telemetry:
        if not enabled:
            return cls()
        endpoint = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        if not endpoint:
            raise ValueError("--otel requires --otlp-endpoint or OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("OTLP traces endpoint must use HTTP or HTTPS")
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExportResult
        except ImportError as error:
            raise RuntimeError("Install observability/requirements.txt to use --otel") from error

        class TrackingExporter(OTLPSpanExporter):
            success_count = 0
            failure_count = 0

            def export(self, spans):
                try:
                    result = super().export(spans)
                except Exception:
                    self.failure_count += 1
                    raise
                if result == SpanExportResult.SUCCESS:
                    self.success_count += 1
                else:
                    self.failure_count += 1
                return result

        provider = TracerProvider(resource=Resource.create({
            "service.name": "s2c-cli", "service.version": "s2c-pipeline/0.1.0",
        }))
        exporter = TrackingExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        return cls(tracer=provider.get_tracer("triunalabs.s2c"), provider=provider, exporter=exporter)

    @contextmanager
    def span(self, name: str, attributes: dict[str, object] | None = None) -> Iterator[object]:
        if self.tracer is None:
            yield _NoopSpan()
            return
        # Exception recording is disabled: its default message can contain a URL or page text.
        with self.tracer.start_as_current_span(
            name, record_exception=False, set_status_on_exception=False,
        ) as span:
            safe = _SafeSpan(span)
            for key, value in (attributes or {}).items():
                safe.set_attribute(key, value)
            try:
                yield safe
            except Exception as error:
                from opentelemetry.trace.status import Status, StatusCode
                safe.set_attribute("s2c.error.type", type(error).__name__)
                span.set_status(Status(StatusCode.ERROR))
                raise

    @staticmethod
    def trace_id(span: object) -> str | None:
        context = span.get_span_context()
        if context is None or not context.is_valid:
            return None
        return f"{context.trace_id:032x}"

    def finish(self) -> bool:
        if self.provider is None or self._finished:
            return self._flush_completed
        try:
            flushed = bool(self.provider.force_flush(timeout_millis=10000))
            accepted = (self.exporter is None or
                        (self.exporter.success_count > 0 and self.exporter.failure_count == 0))
            self._flush_completed = flushed and accepted
            return self._flush_completed
        finally:
            self.provider.shutdown()
            self._finished = True
