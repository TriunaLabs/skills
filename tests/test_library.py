import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate import validate

CSV_SCRIPT_DIR = ROOT / 'skills/csv-profile/scripts'
ROUTE_SKILL_DIR = ROOT / 'skills/route-agent-message'
RELEASE_SKILL_DIR = ROOT / 'skills/release-brief'
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

    def test_route_agent_message_acceptance_scenario_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            route = root / 'route.json'
            subprocess.run([
                sys.executable, str(ROUTE_SKILL_DIR / 'scripts/route-event'),
                str(ROUTE_SKILL_DIR / 'samples/api-change-event.json'),
                str(ROUTE_SKILL_DIR / 'samples/active-sessions.json'), str(route), '--offline',
            ], check=True, capture_output=True, text=True)
            data = json.loads(route.read_text())
            selected = {item['session_id'] for item in data['recipients'] if item['selected']}
            self.assertEqual(selected, {'web-client', 'mobile-client', 'contract-tests'})
            self.assertEqual(data['summary']['active_candidates'], 5)
            self.assertEqual(data['summary']['held'], 2)
            self.assertEqual(data['policy']['provider'], 'laya')
            self.assertEqual(data['evaluation']['missed_recipients'], [])
            self.assertEqual(data['evaluation']['unnecessary_messages'], [])

            receipts = root / 'receipts.json'
            receipts.write_text(json.dumps({'receipts': [
                {'recipient_id': recipient, 'status': 'delivered', 'transport': 'fixture'}
                for recipient in sorted(selected)
            ]}))
            html_report = root / 'route.html'
            markdown_report = root / 'route.md'
            for report_format, output in [('html', html_report), ('markdown', markdown_report)]:
                subprocess.run([
                    sys.executable, str(ROUTE_SKILL_DIR / 'scripts/inspect-route'), str(route),
                    '--receipts', str(receipts), '--format', report_format, '--out', str(output),
                ], check=True, capture_output=True, text=True)
            html_text = html_report.read_text(encoding='utf-8')
            self.assertIn('<!doctype html>', html_text)
            self.assertIn('From event to receipt', html_text)
            self.assertNotIn('/*__ROUTE_', html_text)
            self.assertNotIn('https://', html_text)
            self.assertIn('| web-client | yes | relevant | delivered |', markdown_report.read_text(encoding='utf-8'))

    def test_route_agent_message_uses_configurable_decision_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event = root / 'event.json'
            registry = root / 'registry.json'
            decisions = root / 'decisions.json'
            route = root / 'route.json'
            event.write_text(json.dumps({
                'source': {'session_id': 'source'}, 'summary': 'Question about shared auth behavior',
                'repo': 'platform', 'topic': 'shared behavior', 'evidence_ref': 'issue:1',
                'requested_action': 'Confirm whether your task is affected.',
            }))
            registry.write_text(json.dumps({'sessions': [{
                'session_id': 'candidate', 'active': True, 'repo': 'platform',
                'task': 'Investigate client behavior', 'components': [], 'owned_paths': [],
                'depends_on': [], 'topics': [], 'transport': {'kind': 'fixture', 'target': 'candidate'},
            }]}))
            decisions.write_text(json.dumps({'decisions': [{
                'candidate_id': 'candidate', 'answer': 'relevant', 'confidence': .91,
            }]}))
            subprocess.run([
                sys.executable, str(ROUTE_SKILL_DIR / 'scripts/route-event'),
                str(event), str(registry), str(route), '--provider', 'jev', '--decisions', str(decisions),
            ], check=True, capture_output=True, text=True)
            data = json.loads(route.read_text())
            self.assertEqual(data['policy']['provider'], 'jev')
            self.assertTrue(data['recipients'][0]['selected'])
            self.assertEqual(data['summary']['ambiguous_decisions'], 1)

    def test_release_brief_collects_git_evidence_and_renders_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / 'repo'
            repo.mkdir()
            def run_git(*args):
                return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()
            run_git('init')
            run_git('config', 'user.email', 'fixture@example.com')
            run_git('config', 'user.name', 'Release Fixture')
            (repo / 'README.md').write_text('base\n')
            run_git('add', 'README.md')
            run_git('commit', '-m', 'chore: initial fixture')
            base = run_git('rev-parse', 'HEAD')
            run_git('config', 'user.name', 'Developer One')
            (repo / 'openapi').mkdir()
            (repo / 'openapi/auth.yaml').write_text('expires_at: string\n')
            run_git('add', 'openapi/auth.yaml')
            run_git('commit', '-m', 'feat(auth): return absolute session expiry (#142)')
            run_git('config', 'user.name', 'Developer Two')
            (repo / 'openapi/auth.yaml').write_text('session:\n  expires_at: string\n')
            run_git('add', 'openapi/auth.yaml')
            run_git('commit', '-m', 'feat(auth)!: remove expires_in from response', '-m', 'BREAKING CHANGE: clients must read session.expires_at.')
            target = run_git('rev-parse', 'HEAD')
            evidence = root / 'evidence.json'
            evidence.write_text(json.dumps({
                'issues': [{'id': '142', 'title': 'Expiry contract', 'url': 'https://tracker.example/142', 'state': 'closed'}],
                'tests': [{'name': 'contract suite', 'status': 'passed', 'evidence_ref': 'run:1'}],
                'security_scans': [{'provider': 'Snyk', 'scope': 'dependencies', 'status': 'passed', 'introduced': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}, 'resolved': {'critical': 0, 'high': 1, 'medium': 0, 'low': 0}, 'remaining': {'critical': 0, 'high': 0, 'medium': 1, 'low': 0}, 'evidence_ref': 'snyk:1'}],
                'supply_chain': {'sbom': {'status': 'present', 'evidence_ref': 'artifact:sbom'}, 'provenance': {'status': 'verified', 'evidence_ref': 'attestation:1'}, 'signature': {'status': 'unknown'}},
                'deployment': {'status': 'not_deployed'},
                'rollback': {'status': 'tested', 'evidence_ref': 'run:rollback'},
                'observability': {'status': 'verified', 'evidence_ref': 'dashboard:1'},
                'rollout': {'status': 'ready', 'evidence_ref': 'plan:1'},
                'known_limitations': ['Older clients need an upgrade.'],
            }))
            artifact = root / 'release.json'
            subprocess.run([
                sys.executable, str(RELEASE_SKILL_DIR / 'scripts/collect-release'), '--repo', str(repo),
                '--base', base, '--target', target, '--audience', 'users', '--evidence', str(evidence), '--out', str(artifact),
            ], check=True, capture_output=True, text=True)
            data = json.loads(artifact.read_text(encoding='utf-8'))
            self.assertEqual(data['summary']['commits'], 2)
            self.assertEqual(data['source']['base_sha'], base)
            self.assertEqual(data['source']['target_sha'], target)
            self.assertEqual({entry['category'] for entry in data['entries']}, {'Added', 'Breaking'})
            self.assertIn('142', data['commits'][0]['verified_issue_refs'])
            self.assertTrue(any(item['kind'] == 'breaking-change' for item in data['risk_flags']))
            self.assertEqual(data['schema_version'], '1.1')
            self.assertEqual(data['summary']['contributors'], 2)
            self.assertEqual(len(data['confidence']['domains']), 5)
            self.assertEqual(data['confidence']['security_delta']['resolved']['high'], 1)
            self.assertEqual(data['readiness'], 'draft')

            html_report, markdown_report = root / 'release.html', root / 'release.md'
            for report_format, output in [('html', html_report), ('markdown', markdown_report)]:
                subprocess.run([
                    sys.executable, str(RELEASE_SKILL_DIR / 'scripts/render-release'), str(artifact),
                    '--format', report_format, '--out', str(output),
                ], check=True, capture_output=True, text=True)
            html_text = html_report.read_text(encoding='utf-8')
            self.assertIn('<!doctype html>', html_text)
            self.assertIn('Release entries', html_text)
            self.assertIn('Release evidence matrix', html_text)
            self.assertIn('EXPORT PDF', html_text)
            self.assertIn('window.print()', html_text)
            self.assertNotIn('/*__RELEASE_', html_text)
            self.assertNotIn('<script src=', html_text)
            markdown_text = markdown_report.read_text(encoding='utf-8')
            self.assertIn('**Draft**', markdown_text)
            self.assertIn('## Breaking', markdown_text)
            self.assertIn('## Collaboration and scope', markdown_text)
            self.assertIn('## Release evidence matrix', markdown_text)

if __name__ == '__main__':
    unittest.main()
