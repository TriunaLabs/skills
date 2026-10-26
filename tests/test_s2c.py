import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/scan-to-comprehend/scripts/s2c_audit.py'
spec = importlib.util.spec_from_file_location('s2c_audit', SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class S2CPreflightTests(unittest.TestCase):
    def test_cli_records_audit_date_in_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'page.html'
            source.write_text('<h1>Products</h1>', encoding='utf-8')
            output = io.StringIO()
            with patch.object(audit.sys, 'argv', ['s2c_audit.py', str(source), '--json']), redirect_stdout(output):
                self.assertEqual(audit.main(), 0)
            result = json.loads(output.getvalue())
            self.assertRegex(result['audited_on'], r'^\d{4}-\d{2}-\d{2}$')
            self.assertEqual(len(result['reports']), 1)

    def test_reports_observable_structure_with_explained_risk_estimate(self):
        report = audit.audit_html('<h1>Compare outcomes</h1><h3>Methods</h3><img src="plot.png"><a href="/data">read more</a>', 'sample.html')
        codes = {item['code'] for item in report['findings']}
        self.assertEqual(codes, {'heading_jump', 'missing_alt', 'generic_link'})
        estimate = report['estimated_cognitive_load']
        self.assertEqual(estimate['score'], 26)
        self.assertEqual(estimate['confidence'], 'low')
        self.assertEqual({item['code'] for item in report['suggestions']}, codes)
        self.assertIn('labeled_sections', {item['code'] for item in report['strengths']})

    def test_clean_source_has_zero_flagged_friction_not_a_comprehension_claim(self):
        report = audit.audit_html('<!doctype html><html><body><h1>Products</h1><h2>Compare</h2>'
                                  '<table><tr><th>Product</th><th>Purpose</th></tr></table>'
                                  '<img src="chart.png" alt="Product comparison"></body></html>', 'sample.html')
        self.assertEqual(report['estimated_cognitive_load']['score'], 0)
        self.assertEqual(report['findings'], [])
        self.assertIn('table_headers_present', {item['code'] for item in report['strengths']})
        self.assertIn('source-only', report['limit'].lower())

    def test_missing_outline_is_charged_once(self):
        report = audit.audit_html('<!doctype html><html><body><p>Unlabeled page</p></body></html>', 'sample.html')
        self.assertEqual(report['estimated_cognitive_load']['score'], 22)
        self.assertEqual({item['code'] for item in report['findings']}, {'no_h1', 'no_headings'})

    def test_each_comparison_table_needs_its_own_headers(self):
        report = audit.audit_html('<h1>Compare</h1><table><tr><th>Plan</th></tr></table>'
                                  '<table><tr><td>Unlabeled value</td></tr></table>', 'sample.html')
        self.assertIn('table_headers', {item['code'] for item in report['findings']})
        self.assertNotIn('table_headers_present', {item['code'] for item in report['strengths']})

    def test_ignores_markdown_examples_inside_fences(self):
        report = audit.audit_markdown('# Findings\n```md\n### Not a real heading\n![](chart.png)\n```\n## Context\n', 'sample.md')
        self.assertEqual(report['findings'], [])
        self.assertEqual([item['text'] for item in report['headings']], ['Findings', 'Context'])

    def test_html_fragment_does_not_require_page_title(self):
        report = audit.audit_html('<section><h2>Useful details</h2></section>', 'component.html')
        self.assertEqual(report['findings'], [])


if __name__ == '__main__':
    unittest.main()
