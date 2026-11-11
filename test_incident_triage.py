import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

import incident_triage as app
from triage import BundleError, load_bundle

ROOT = Path(__file__).parent


class IncidentTests(unittest.TestCase):
    def setUp(self):
        self.bundle = load_bundle(ROOT / 'examples/alerts/routing-failure.json')

    def test_scenarios_and_order_independence(self):
        for scenario, family, severity in [
            ('routing-failure', 'routing', 'SEV1'),
            ('wan-congestion', 'capacity', 'SEV2'),
            ('ha-failover', 'availability', 'SEV2'),
            ('recurring-hardware', 'hardware', 'SEV2')]:
            with self.subTest(scenario=scenario):
                bundle = load_bundle(ROOT / f'examples/alerts/{scenario}.json')
                report = app.correlate(bundle)
                incident, = report['incidents']
                self.assertEqual((family, severity), (incident['family'], incident['severity']))
                bundle['alerts'].reverse()
                self.assertEqual(report, app.correlate(bundle))
                self.assertEqual('unconfirmed', incident['root_cause'])

    def test_site_family_and_window_separation(self):
        for field, value in [('site', 'demo-other'), ('signal', 'packet_loss'),
                             ('observed_at', '2026-01-10T12:05:00Z')]:
            bundle = copy.deepcopy(self.bundle)
            bundle['alerts'][1][field] = value
            self.assertEqual(2, len(app.correlate(bundle)['incidents']))

    def test_equivalent_timezones_correlate(self):
        self.bundle['alerts'][1]['observed_at'] = '2026-01-10T07:01:00-05:00'
        self.assertEqual(1, len(app.correlate(self.bundle)['incidents']))

    def test_projection_keeps_relative_sequence_and_device_spread(self):
        self.bundle['alerts'][1]['device'] = 'demo-edge-02'
        self.bundle['alerts'][1]['observed_at'] = '2026-01-10T07:01:00-05:00'
        projected, = app.projection(app.correlate(self.bundle))
        self.assertEqual(2, projected['device_count'])
        self.assertEqual([0, 60], [e['t_plus_seconds'] for e in projected['events']])
        self.assertEqual(['device-1', 'device-2'], [e['device'] for e in projected['events']])
        self.assertEqual(['none', 'outage'], [e['impact'] for e in projected['events']])
        serialized = json.dumps(projected)
        for private in ('demo-', '2026-', 'observed_at', 'site'):
            self.assertNotIn(private, serialized)

    def test_reject_invalid_and_non_synthetic_input(self):
        for field, value in [('synthetic', False), ('schema_version', True), ('alerts', [])]:
            bundle = copy.deepcopy(self.bundle)
            bundle[field] = value
            with self.assertRaises(BundleError):
                app.correlate(bundle)
        for field, value in [('device', 'real-router'), ('signal', 'execute_command'),
                             ('observed_at', '2026-01-01'), ('impact', 'critical'),
                             ('raw_log', 'secret'), ('id', 'demo-alert-1')]:
            bundle = copy.deepcopy(self.bundle)
            bundle['alerts'][1][field] = value
            with self.subTest(field=field), self.assertRaises(BundleError):
                app.correlate(bundle)

    def test_review_digest_decision_and_no_overwrite(self):
        for decision in ('approve', 'reject'):
            with tempfile.TemporaryDirectory() as folder:
                out = Path(folder) / 'incident'
                report = app.correlate(self.bundle)
                app.write_report(out, report, app.digest(self.bundle))
                record = app.review(out, decision, 'Demo reviewer', 'Checked the evidence')
                self.assertEqual(decision, record['decision'])
                self.assertFalse(record['changes_executed'])
                self.assertEqual(2, len((out / 'audit.jsonl').read_text().splitlines()))
                with self.assertRaises((BundleError, FileExistsError)):
                    app.review(out, decision, 'Other reviewer', 'Second review')
                with self.assertRaises(FileExistsError):
                    app.write_report(out, report, 'unused')

    def test_tampered_report_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'incident'
            report = app.correlate(self.bundle)
            app.write_report(out, report, app.digest(self.bundle))
            report['incidents'][0]['severity'] = 'SEV3'
            (out / 'report.json').write_bytes(app.canonical(report))
            with self.assertRaises(BundleError):
                app.review(out, 'approve', 'Demo reviewer', 'Review')

    @patch('incident_triage.urllib.request.urlopen')
    def test_claude_projection_and_no_authority_over_severity(self, send):
        response = io.BytesIO(json.dumps({'stop_reason': 'end_turn', 'content': [
            {'type': 'text', 'text': 'Draft investigation only.'}]}).encode())
        send.return_value = response
        report = app.correlate(self.bundle)
        original = copy.deepcopy(report)
        summary = app.claude_summary(report, 'test-model', 'test-secret')
        self.assertEqual('claude', summary['provider'])
        self.assertEqual(original, report)
        request = send.call_args.args[0]
        payload = request.data.decode()
        for forbidden in ('demo-branch', 'demo-edge', 'observed_at', 'test-secret'):
            self.assertNotIn(forbidden, payload)
        self.assertNotIn('tools', json.loads(payload))
        sent = json.loads(json.loads(payload)['messages'][0]['content'])
        self.assertEqual(['t_plus_seconds', 'device', 'signal', 'impact'], list(sent[0]['events'][0]))
        self.assertEqual(0, sent[0]['events'][0]['t_plus_seconds'])
        self.assertTrue(all(e['device'].startswith('device-') for i in sent for e in i['events']))
        self.assertEqual(30, send.call_args.kwargs['timeout'])

    @patch('incident_triage.urllib.request.urlopen')
    def test_provider_failure_is_sanitized(self, send):
        send.side_effect = urllib.error.URLError('test-secret')
        with self.assertRaises(BundleError) as context:
            app.claude_summary(app.correlate(self.bundle), 'test-model', 'test-secret')
        self.assertNotIn('test-secret', str(context.exception))

    @patch('incident_triage.urllib.request.urlopen')
    def test_invalid_provider_responses(self, send):
        for body in [b'not json', b'{}', b'[]', b'null', b'x' * 65537,
                     b'{"stop_reason":"max_tokens","content":[]}',
                     b'{"stop_reason":"end_turn","content":[]}',
                     b'{"stop_reason":"end_turn","content":null}']:
            send.return_value = io.BytesIO(body)
            with self.subTest(body=body[:60]), self.assertRaises(BundleError):
                app.claude_summary(app.correlate(self.bundle), 'test-model', 'test-secret')

    @patch('incident_triage.urllib.request.urlopen')
    def test_missing_configuration_does_not_send(self, send):
        for model, key in [(None, 'key'), ('model', None)]:
            with self.assertRaises(BundleError):
                app.claude_summary(app.correlate(self.bundle), model, key)
        send.assert_not_called()

    def test_model_text_cannot_inject_markdown(self):
        report = app.correlate(self.bundle)
        draft = '## Evidence\n**Draft**\n```\n[click](https://example.com) <script>alert(1)</script>\n````'
        report['summary']['text'] = draft
        rendered = app.render(report)
        block = '`````text\n' + draft + '\n`````\n'
        self.assertIn(block, rendered)
        self.assertEqual(2, rendered.count('`````'))
        self.assertNotIn('\\#', rendered)

    @patch('incident_triage.claude_summary', side_effect=BundleError('Unavailable'))
    def test_cli_fallback_preserves_report_and_audit(self, summary):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'incident'
            self.assertEqual(0, app.main(['run', str(ROOT / 'examples/alerts/routing-failure.json'),
                                          '--output', str(out), '--claude']))
            report = load_bundle(out / 'report.json')
            self.assertIn('failure', report['summary'])
            self.assertEqual('pending', report['approval'])
            self.assertTrue((out / 'audit.jsonl').exists())

    @patch('incident_triage.urllib.request.urlopen')
    def test_offline_cli_never_calls_provider(self, send):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(0, app.main(['run', str(ROOT / 'examples/alerts/routing-failure.json'),
                                          '--output', str(Path(folder) / 'incident')]))
        send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
