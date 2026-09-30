import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate import validate

CSV_SCRIPT_DIR = ROOT / 'skills/csv-profile/scripts'
sys.path.insert(0, str(CSV_SCRIPT_DIR))
spec = importlib.util.spec_from_file_location('profile_csv', CSV_SCRIPT_DIR / 'profile_csv.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
analyze_spec = importlib.util.spec_from_file_location('analyze_csv', CSV_SCRIPT_DIR / 'analyze_csv.py')
analyzer = importlib.util.module_from_spec(analyze_spec)
analyze_spec.loader.exec_module(analyzer)

class LibraryTests(unittest.TestCase):
    def test_catalog(self):
        records = validate()
        self.assertGreaterEqual(len(records), 1)
        self.assertEqual(len({r['name'] for r in records}), len(records))

    def test_invalid_metadata_and_resources_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / 'skills/decision-record', root / 'skills/decision-record')
            skill = root / 'skills/decision-record/SKILL.md'
            with skill.open('a', encoding='utf-8') as stream:
                stream.write('\n[escape](../../outside.md)')
            with self.assertRaisesRegex(ValueError, 'reference'):
                validate(root)
            shutil.copy2(ROOT / 'skills/decision-record/SKILL.md', skill)
            meta = root / 'skills/decision-record/catalog.json'
            data = json.loads(meta.read_text())
            data['compatibility']['codex'] = 'tested'
            meta.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'compatibility'):
                validate(root)

    def test_preview_metadata_is_validated(self):
        records = validate()
        csv_profile = next(record for record in records if record['name'] == 'csv-profile')
        self.assertEqual(csv_profile['preview']['src'], 'assets/catalog-preview.png')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / 'skills/csv-profile', root / 'skills/csv-profile')
            meta = root / 'skills/csv-profile/catalog.json'
            data = json.loads(meta.read_text())
            data['preview']['src'] = '../../outside.png'
            meta.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'preview'):
                validate(root)

    def test_csv_multiline_bom_missing_and_width(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data.csv'
            path.write_text('\ufeffname,name,value\n"two\nlines",,3\nx, y\nz, ,4\n', encoding='utf-8')
            report = module.profile(path)
            self.assertEqual(report['rows'], 3)
            self.assertEqual(report['duplicate_headers'], ['name'])
            self.assertEqual(report['width_mismatches'], 1)
            self.assertEqual(report['missing_by_column_index'], [0, 2, 0])
            self.assertNotIn('two', json.dumps(report))

    def test_csv_empty_and_alternate_delimiter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data.csv'
            path.write_text('')
            self.assertEqual(module.profile(path)['rows'], 0)
            path.write_text('a;b\n1;2\n')
            self.assertEqual(module.profile(path, ';')['columns'], 2)

    def test_malformed_csv_fails(self):
        import csv
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.csv'
            path.write_text('a,b\n"unclosed,2')
            with self.assertRaises(csv.Error):
                module.profile(path)

    def test_rich_csv_analysis_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'observations.csv'
            path.write_text(
                'id,amount,status,observed_at,note\n'
                '1,10,Open,2026-01-01,ok\n'
                '2,"$1,200",open,2026-01-02,\n'
                '3,oops, OPEN ,not-a-date,  padded  \n'
                '3,oops, OPEN ,not-a-date,  padded  \n'
                '5,99999,N/A,2026-01-05,ok\n',
                encoding='utf-8',
            )
            report = analyzer.analyze(path, include_values=True)
            self.assertEqual(report['summary']['rows'], 5)
            self.assertEqual(report['summary']['duplicate_rows'], 1)
            self.assertGreater(report['summary']['missing'], 0)
            self.assertGreater(report['summary']['mixed_type_values'], 0)
            self.assertTrue(any(item['kind'] == 'category variants' for item in report['issues']))
            self.assertTrue(any(sample.get('values') for sample in report['row_samples']))
            html = analyzer.render_html(report)
            self.assertIn('<!doctype html>', html)
            self.assertIn('CSV quality report', html)
            self.assertNotIn('/*__CSV_PROFILE_', html)
            self.assertNotIn('https://', html)
            markdown = analyzer.render_markdown(report)
            self.assertIn('## Priority findings', markdown)
            self.assertIn('| Column | Inferred type |', markdown)

    def test_rich_report_excludes_values_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'private.csv'
            path.write_text('name,value\nPRIVATE_PERSON,\n', encoding='utf-8')
            report = analyzer.analyze(path)
            self.assertFalse(report['privacy']['values_included'])
            self.assertNotIn('PRIVATE_PERSON', json.dumps(report['row_samples']))

    def test_width_issue_count_is_not_limited_by_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'widths.csv'
            path.write_text('a,b\n1\n2\n3\n4,5\n', encoding='utf-8')
            report = analyzer.analyze(path, row_sample_limit=1)
            self.assertEqual(report['summary']['rows'], 4)
            self.assertEqual(report['summary']['rectangular_rows'], 1)
            self.assertEqual(report['summary']['width_issues'], 3)
            self.assertEqual(len(report['width_issue_samples']), 1)

    def test_laya_semantic_review_attaches_to_html_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'semantic.csv'
            path.write_text('id,amount\n1,10\n2,20\n', encoding='utf-8')
            report = analyzer.analyze(path)
            columns = []
            for column in report['columns']:
                columns.append({
                    'index': column['index'], 'name': column['name'],
                    'semantic_role': {'label': 'identifier', 'confidence': .91, 'probabilities': {'identifier': .91}},
                    'review_priority': {'label': 'routine', 'confidence': .88, 'probabilities': {'routine': .88}},
                    'gate': 'accepted',
                })
            review = {
                'schema_version': '1.0', 'generated_at': '2026-09-30T00:00:00Z',
                'source': {'name': path.name, 'profile_schema_version': report['schema_version'], 'aggregate_sha256': 'test'},
                'engine': {'name': 'Laya', 'runtime': '@receptron/laya@0.1.2', 'model': 'fixture'},
                'policy': {'mode': 'shadow', 'confidence_threshold': .8, 'low_confidence_action': 'review'},
                'privacy': {'raw_values_sent': False, 'input': 'aggregates'}, 'columns': columns,
            }
            review_path = root / 'review.json'
            review_path.write_text(json.dumps(review), encoding='utf-8')
            analyzer.attach_semantic_review(report, review_path)
            html = analyzer.render_html(report)
            markdown = analyzer.render_markdown(report)
            self.assertIn('Laya semantic review', html)
            self.assertIn('semantic_role', html)
            self.assertIn('## Laya semantic review', markdown)
            self.assertIn('80%', markdown)

    def test_semantic_review_rejects_raw_value_declaration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'semantic.csv'
            path.write_text('id\n1\n', encoding='utf-8')
            report = analyzer.analyze(path)
            review = {
                'schema_version': '1.0', 'source': {'name': path.name},
                'privacy': {'raw_values_sent': True},
                'columns': [{'index': 0, 'name': 'id'}],
            }
            review_path = root / 'review.json'
            review_path.write_text(json.dumps(review), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'raw_values_sent'):
                analyzer.attach_semantic_review(report, review_path)

if __name__ == '__main__':
    unittest.main()
