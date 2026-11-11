"""Synthetic alert triage demo. No device access or remediation execution."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

from triage import BundleError, fields, load_bundle, md, require, string, timestamp

SIGNALS = {
    'route_change': ('routing', 'Compare intended and observed routes; collect read-only path tests.'),
    'tcp_failure': ('routing', 'Compare intended and observed routes; collect read-only path tests.'),
    'high_utilization': ('capacity', 'Inspect utilization, drops and scheduled backup traffic.'),
    'packet_loss': ('capacity', 'Inspect utilization, drops and scheduled backup traffic.'),
    'high_latency': ('capacity', 'Inspect utilization, drops and scheduled backup traffic.'),
    'ha_failover': ('availability', 'Review HA state and session continuity with the firewall owner.'),
    'application_errors': ('availability', 'Review HA state and session continuity with the firewall owner.'),
    'power_supply_fault': ('hardware', 'Verify redundant power and open a hardware problem investigation.'),
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def correlate(bundle):
    fields(bundle, {'schema_version', 'synthetic', 'alerts'}, 'bundle')
    require(type(bundle.get('schema_version')) is int and bundle['schema_version'] == 1,
            'schema_version must be integer 1')
    require(bundle.get('synthetic') is True, 'Only explicitly synthetic alerts are accepted')
    alerts = bundle.get('alerts')
    require(isinstance(alerts, list) and 1 <= len(alerts) <= 500, 'Require 1 to 500 alerts')
    seen, groups = set(), {}
    for alert in alerts:
        fields(alert, {'id', 'site', 'device', 'observed_at', 'signal', 'impact'}, 'alert')
        for key in ('id', 'site', 'device'):
            value = string(alert.get(key), key, 60)
            require(re.fullmatch(r'demo-[a-z0-9-]+', value) is not None,
                    f'{key} must be a fictional demo- identifier')
        require(alert['id'] not in seen, 'Duplicate alert id')
        seen.add(alert['id'])
        timestamp(alert.get('observed_at'), 'observed_at')
        require(isinstance(alert.get('signal'), str) and alert['signal'] in SIGNALS, 'Unknown signal')
        require(alert.get('impact') in ('none', 'degraded', 'outage'), 'Unknown impact')
    # Sorting and fixed UTC five-minute buckets make input order irrelevant and
    # prevent an arbitrarily long chain of alerts from becoming one incident.
    for alert in sorted(alerts, key=lambda a: (timestamp(a['observed_at'], 'time'), a['id'])):
        family = SIGNALS[alert['signal']][0]
        bucket = int(timestamp(alert['observed_at'], 'time').timestamp()) // 300
        groups.setdefault((alert['site'], family, bucket), []).append(alert)
    incidents = []
    for (site, family, bucket), evidence in sorted(groups.items()):
        signals = sorted({a['signal'] for a in evidence})
        impacts = {a['impact'] for a in evidence}
        severity = 'SEV1' if 'outage' in impacts else 'SEV2' if 'degraded' in impacts else 'SEV3'
        reason = 'Highest reported synthetic impact in this group; root cause unconfirmed.'
        if family == 'hardware' and len(evidence) >= 3:
            severity = 'SEV1' if severity == 'SEV1' else 'SEV2'
            reason += ' Three or more power alarms in one bucket warrant problem review.'
        incidents.append({'incident_id': 'INC-' + digest([site, family, bucket])[:12],
                          'site': site, 'family': family, 'severity': severity,
                          'severity_reason': reason, 'signals': signals,
                          'timeline': evidence, 'root_cause': 'unconfirmed',
                          'escalation': 'Incident lead and network owner' if severity == 'SEV1' else 'Network support owner',
                          'suggested_runbook': SIGNALS[evidence[0]['signal']][1]})
    return {'schema_version': 1, 'synthetic': True, 'policy': 'site-family-fixed-5m-v1',
            'approval': 'pending', 'incidents': incidents,
            'summary': {'provider': 'offline', 'text': 'Review evidence, validate impact and approve or reject the proposed investigation. No changes executed.'}}


def projection(report):
    """Allowlisted, de-identified view of each incident for the model.

    Includes the ordered event sequence (seconds since the incident's first alert,
    a per-incident device ordinal, signal and impact) so the draft can reason about
    order and spread, but never input identifiers, timestamps, free text or keys.
    """
    items = []
    for number, item in enumerate(report['incidents'], start=1):
        start = timestamp(item['timeline'][0]['observed_at'], 'time')
        ordinals = {}
        events = []
        for alert in item['timeline']:
            device = ordinals.setdefault(alert['device'], f'device-{len(ordinals) + 1}')
            offset = int((timestamp(alert['observed_at'], 'time') - start).total_seconds())
            events.append({'t_plus_seconds': offset, 'device': device,
                           'signal': alert['signal'], 'impact': alert['impact']})
        items.append({'incident': number, 'family': item['family'], 'severity': item['severity'],
                      'alert_count': len(item['timeline']), 'device_count': len(ordinals),
                      'events': events, 'deterministic_runbook': item['suggested_runbook']})
    return items


SYSTEM_PROMPT = (
    'You are drafting notes for a network operations engineer reviewing synthetic incident evidence. '
    'Severity, grouping and escalation are already decided and are not yours to change. Root cause is unconfirmed. '
    'For each incident write four short sections: "What the evidence shows" (order and spread of events), '
    '"Hypotheses" (at most two, each marked unconfirmed; leave unranked unless evidence distinguishes them), '
    '"Read-only checks" (what to look at to confirm or rule out each hypothesis; no configuration changes), '
    'and "Post-mortem notes" (a timeline sketch and open questions). Do not invent facts beyond the events given, '
    'do not claim resolution, and say plainly when the evidence is too thin. '
    'Events are observations, not exact onset times. Impact none means no impact was reported in that event, not proof of health. '
    'A signal is an alert: never say a route_change event triggered no alert. '
    'Do not infer TCP retry exhaustion, protocol timers, BGP/OSPF use, actual configuration edits, '
    'user-visible scope, or intermediate events from the time gap. '
    'Keep the timeline strictly to supplied events; list mechanisms only as unsupported possibilities, '
    'and do not rank hypotheses by likelihood when the evidence cannot distinguish them. '
    'Do not imply historical measurements can be collected now; distinguish existing historical records '
    'from current read-only checks. '
    'For a route_change and tcp_failure pair, the only supported hypotheses are that the events may be related '
    'or may be independent; do not expand these into invented protocol-specific mechanisms. '
    'Only report the two recorded observations in the timeline. Never add a row for the interval between them. '
    'Reported outage impact does not establish user-facing, widespread, or all-flow failure. '
    'Keep the entire response under 350 words. Human approval is required. You have no tools.')


def claude_summary(report, model, api_key):
    require(bool(api_key) and bool(model), 'Claude requires ANTHROPIC_API_KEY and --model')
    body = {'model': model, 'max_tokens': 1500, 'system': SYSTEM_PROMPT,
            'messages': [{'role': 'user', 'content': json.dumps(projection(report))}]}
    request = urllib.request.Request('https://api.anthropic.com/v1/messages',
              data=canonical(body), headers={'content-type': 'application/json',
              'x-api-key': api_key, 'anthropic-version': '2023-06-01'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(65537)
        require(len(raw) <= 65536, 'Oversized Claude response')
        result = json.loads(raw)
        require(result.get('stop_reason') == 'end_turn', 'Incomplete Claude response')
        text = '\n'.join(block['text'] for block in result['content'] if block.get('type') == 'text')
        string(text, 'Claude summary', 20000)
        return {'provider': 'claude', 'model': model, 'text': text}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        # Never expose provider bodies, headers or credentials in errors/audit.
        raise BundleError('Claude request failed or returned an invalid response') from error


def render(report):
    lines = ['# Synthetic incident triage', '', '**Human approval: pending. No changes executed.**', '',
             '## Advisory summary (untrusted draft)', '',
             '\n'.join(md(line) for line in report['summary']['text'].splitlines())]
    for item in report['incidents']:
        lines += ['', f"## {item['incident_id']} — {item['severity']}", '',
                  f"Site: {item['site']}; family: {item['family']}", '',
                  item['severity_reason'], '', 'Root cause: unconfirmed.', '',
                  f"Escalation: {item['escalation']}", '',
                  f"Suggested investigation: {item['suggested_runbook']}", '', '### Evidence timeline', '']
        lines += [f"- {a['observed_at']} | {a['id']} | {a['device']} | {a['signal']} | {a['impact']}" for a in item['timeline']]
    return '\n'.join(lines) + '\n'


def event(kind, **details):
    return {'at': datetime.now(timezone.utc).isoformat(), 'event': kind, **details}


def write_report(directory, report, input_hash):
    directory.mkdir(parents=True, exist_ok=False)
    (directory / 'report.json').write_bytes(canonical(report) + b'\n')
    (directory / 'report.md').write_text(render(report), encoding='utf-8')
    initial = event('report_created', report_sha256=digest(report), input_sha256=input_hash,
                    provider=report['summary']['provider'],
                    model=report['summary'].get('model'),
                    provider_failure=report['summary'].get('failure'), approval='pending')
    (directory / 'audit.jsonl').write_bytes(canonical(initial) + b'\n')


def review(directory, decision, reviewer, reason):
    string(reviewer, 'reviewer', 100)
    string(reason, 'reason', 1000)
    require(decision in ('approve', 'reject'), 'Invalid decision')
    report = load_bundle(directory / 'report.json')
    audit = (directory / 'audit.jsonl').read_text(encoding='utf-8').splitlines()
    require(len(audit) == 1, 'Audit must contain exactly one report creation event')
    initial = json.loads(audit[0])
    require(isinstance(initial, dict) and initial.get('event') == 'report_created' and
            initial['report_sha256'] == digest(report), 'Report changed or already reviewed')
    record = event('human_review', decision=decision, reviewer=reviewer,
                   reason=reason, report_sha256=digest(report), changes_executed=False)
    # Exclusive creation prevents a second reviewer from silently replacing a decision.
    with (directory / 'review.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
    with (directory / 'audit.jsonl').open('ab') as stream:
        stream.write(canonical(record) + b'\n')
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run')
    run.add_argument('alerts', type=Path)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--claude', action='store_true', help='Send aggregate synthetic evidence to Claude')
    run.add_argument('--model', help='Claude model ID available to your account')
    check = commands.add_parser('review')
    check.add_argument('directory', type=Path)
    check.add_argument('--decision', choices=('approve', 'reject'), required=True)
    check.add_argument('--reviewer', required=True)
    check.add_argument('--reason', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'review':
            review(args.directory, args.decision, args.reviewer, args.reason)
            print('Review recorded. No changes executed.')
        else:
            require(not args.output.exists(), 'Output directory must be new')
            bundle = load_bundle(args.alerts)
            report = correlate(bundle)
            if args.claude:
                try:
                    report['summary'] = claude_summary(report, args.model, os.environ.get('ANTHROPIC_API_KEY'))
                except BundleError:
                    report['summary']['failure'] = 'Claude unavailable; deterministic offline report retained'
            write_report(args.output, report, digest(bundle))
            print(f'Wrote {args.output}. Human review required.')
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        print(f'Cannot process incident: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
