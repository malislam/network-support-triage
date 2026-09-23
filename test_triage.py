import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from triage import analyze, load_bundle, BundleError, markdown

ROOT = Path(__file__).resolve().parent


class TriageTests(unittest.TestCase):
    def bundle(self, name='network-path-failure.json'):
        return load_bundle(ROOT / name)

    def test_network_failure_does_not_assign_root_cause(self):
        result = analyze(self.bundle())
        self.assertEqual(result['root_cause'], 'unconfirmed')
        self.assertIn('tcp_unreachable', [f['code'] for f in result['findings']])
        self.assertIn('timeout_correlation', [f['code'] for f in result['findings']])

    def test_storage_correlations(self):
        codes = {f['code'] for f in analyze(self.bundle('service-storage-issue.json'))['findings']}
        self.assertTrue({'disk_pressure', 'service_unhealthy', 'write_failure_log'} <= codes)
        self.assertNotIn('tcp_unreachable', codes)

    def test_stale_and_missing_are_not_healthy(self):
        result = analyze(self.bundle('incomplete-evidence.json'))
        self.assertIn('service', result['handoff']['stale_evidence'])
        self.assertIn('tcp', result['handoff']['missing_evidence'])

    def test_failed_ping_does_not_imply_path_failure(self):
        bundle = self.bundle()
        bundle['checks']['tcp']['status'] = 'pass'
        codes = {f['code'] for f in analyze(bundle)['findings']}
        self.assertIn('gateway_probe', codes)
        self.assertNotIn('tcp_unreachable', codes)

    def test_malformed_measurements_rejected(self):
        for key, value in [('port', True), ('port', 70000)]:
            bundle = self.bundle()
            bundle['checks']['tcp'][key] = value
            with self.assertRaises(BundleError):
                analyze(bundle)
        bundle = self.bundle()
        bundle['checks']['disk']['used_percent'] = float('nan')
        with self.assertRaises(BundleError):
            analyze(bundle)

    def test_future_observation_rejected(self):
        bundle = self.bundle()
        bundle['checks']['dns']['observed_at'] = '2030-01-01T00:00:00Z'
        with self.assertRaises(BundleError):
            analyze(bundle)

    def test_evidence_cannot_inject_markdown_link(self):
        bundle = self.bundle()
        bundle['reported_impact'] = '[click](https://example.com) <script>'
        report = markdown(analyze(bundle))
        self.assertNotIn('<script>', report)
        self.assertNotIn('[click](https://example.com)', report)

    def test_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'
            path.write_text('{"device":"one","device":"two"}')
            with self.assertRaises(BundleError):
                load_bundle(path)

    def test_cli_reports_and_protects_previous_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'report'
            cmd = [sys.executable, str(ROOT / 'triage.py'), str(ROOT / 'network-path-failure.json'), '--output', str(target)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads((target / 'report.json').read_text())['root_cause'], 'unconfirmed')
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)


if __name__ == '__main__':
    unittest.main()
