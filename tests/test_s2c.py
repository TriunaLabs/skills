import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/scan-to-comprehend/scripts/s2c_audit.py'
spec = importlib.util.spec_from_file_location('s2c_audit', SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class S2CPreflightTests(unittest.TestCase):
    def test_reports_observable_structure_without_a_comprehension_score(self):
        report = audit.audit_html('<h1>Compare outcomes</h1><h3>Methods</h3><img src="plot.png"><a href="/data">read more</a>', 'sample.html')
        codes = {item['code'] for item in report['findings']}
        self.assertEqual(codes, {'heading_jump', 'missing_alt', 'generic_link'})
        self.assertNotIn('score', report)

    def test_ignores_markdown_examples_inside_fences(self):
        report = audit.audit_markdown('# Findings\n```md\n### Not a real heading\n![](chart.png)\n```\n## Context\n', 'sample.md')
        self.assertEqual(report['findings'], [])
        self.assertEqual([item['text'] for item in report['headings']], ['Findings', 'Context'])

    def test_html_fragment_does_not_require_page_title(self):
        report = audit.audit_html('<section><h2>Useful details</h2></section>', 'component.html')
        self.assertEqual(report['findings'], [])


if __name__ == '__main__':
    unittest.main()
