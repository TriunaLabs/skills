"""A real OTLP export must preserve stage ancestry without leaking page data."""

import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
from threading import Thread
import unittest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills/scan-to-comprehend/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from s2c_telemetry import Telemetry  # noqa: E402

HAS_OTEL = bool(importlib.util.find_spec("opentelemetry"))
if HAS_OTEL:
    HAS_OTEL = bool(importlib.util.find_spec("opentelemetry.sdk"))


@unittest.skipUnless(HAS_OTEL, "install the skill's observability/requirements.txt to test OTLP export")
class S2COtelTests(unittest.TestCase):
    def test_stage_spans_are_linked_and_do_not_record_content(self):
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        telemetry = Telemetry(tracer=provider.get_tracer("triunalabs.s2c"), provider=provider)
        with telemetry.span("s2c.run", {"s2c.run.id": "safe-run-id"}) as root:
            trace_id = Telemetry.trace_id(root)
            with self.assertRaisesRegex(ValueError, "private page"):
                with telemetry.span("s2c.capture"):
                    raise ValueError("private page https://example.org/private?token=secret")
            with self.assertRaisesRegex(ValueError, "not allowed"):
                root.set_attribute("url.full", "https://example.org/private?token=secret")
        self.assertTrue(telemetry.finish())
        self.assertRegex(trace_id, r"^[0-9a-f]{32}$")
        spans = {span.name: span for span in exporter.get_finished_spans()}
        self.assertEqual(set(spans), {"s2c.run", "s2c.capture"})
        self.assertEqual(spans["s2c.capture"].parent.span_id, spans["s2c.run"].context.span_id)
        self.assertEqual(spans["s2c.capture"].context.trace_id, spans["s2c.run"].context.trace_id)
        self.assertEqual(dict(spans["s2c.capture"].attributes), {"s2c.error.type": "ValueError"})
        self.assertNotIn("example.org", repr(spans))
        self.assertNotIn("token=secret", repr(spans))
        self.assertNotIn("private page", repr(spans))

    @unittest.skipUnless(os.environ.get("S2C_TEST_OTLP_HTTP") == "1", "loopback OTLP test is opt-in")
    def test_otlp_http_export_reaches_receiver(self):
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

        received = []

        class Receiver(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(200)
                self.send_header("Content-Type", "application/x-protobuf")
                self.end_headers()
                self.wfile.write(b"")

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            telemetry = Telemetry.create(True, f"http://127.0.0.1:{server.server_port}/v1/traces")
            with telemetry.span("s2c.run", {"s2c.run.id": "safe-run-id"}) as root:
                trace_id = Telemetry.trace_id(root)
                with telemetry.span("s2c.capture") as capture:
                    capture.set_attribute("s2c.capture.frame_count", 3)
            self.assertTrue(telemetry.finish())
            self.assertRegex(trace_id, r"^[0-9a-f]{32}$")
            self.assertTrue(received)
            request = ExportTraceServiceRequest()
            request.ParseFromString(b"".join(received))
            spans = [span for resource in request.resource_spans
                     for scope in resource.scope_spans for span in scope.spans]
            self.assertEqual({span.name for span in spans}, {"s2c.run", "s2c.capture"})
            root_span = next(span for span in spans if span.name == "s2c.run")
            capture_span = next(span for span in spans if span.name == "s2c.capture")
            self.assertEqual(capture_span.parent_span_id, root_span.span_id)
            self.assertEqual(capture_span.trace_id, root_span.trace_id)
            self.assertEqual({a.key for a in capture_span.attributes}, {"s2c.capture.frame_count"})
            exported = b"".join(received)
            self.assertNotIn(b"example.org", exported)
            self.assertNotIn(b"token=secret", exported)
            self.assertNotIn(b"private page", exported)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_requires_explicit_export_destination(self):
        from unittest.mock import patch
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": ""}):
            with self.assertRaisesRegex(ValueError, "requires"):
                Telemetry.create(True)


if __name__ == "__main__":
    unittest.main()
