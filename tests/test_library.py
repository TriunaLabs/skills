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

spec = importlib.util.spec_from_file_location('profile_csv', ROOT / 'skills/csv-profile/scripts/profile_csv.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

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

if __name__ == '__main__':
    unittest.main()
