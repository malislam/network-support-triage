"""Offline, evidence-led support-bundle triage. No network or device access."""

import argparse
from datetime import datetime
import ipaddress
import json
import math
from pathlib import Path
import sys

MAX_BYTES = 1_048_576
CHECKS = ("dns", "gateway", "tcp", "service", "disk", "logs")
UNOBSERVED = {"unknown", "not_collected"}


class BundleError(ValueError):
    """The input cannot be interpreted safely as the documented schema."""


def require(condition, message):
    if not condition:
        raise BundleError(message)


def string(value, name, limit=1000):
    require(isinstance(value, str) and 0 < len(value) <= limit,
            f"{name} must be a nonempty string of at most {limit} characters")
    require(all(ord(c) >= 32 or c in "\n\t" for c in value),
            f"{name} contains unsupported control characters")
    return value


def fields(value, allowed, name):
    require(isinstance(value, dict), f"{name} must be an object")
    unexpected = set(value) - set(allowed)
    require(not unexpected, f"{name} has unsupported fields: {sorted(unexpected)}")


def timestamp(value, name):
    string(value, name, 50)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise BundleError(f"{name} must be an ISO 8601 timestamp") from error
    require(parsed.tzinfo is not None, f"{name} must include a timezone")
    return parsed


def validate(bundle):
    fields(bundle, {"schema_version", "incident_id", "device", "captured_at",
                    "reported_impact", "checks"}, "bundle")
    require(type(bundle.get("schema_version")) is int and bundle["schema_version"] == 1,
            "schema_version must be integer 1")
    for key in ("incident_id", "device", "reported_impact"):
        string(bundle.get(key), key)
    captured = timestamp(bundle.get("captured_at"), "captured_at")
    checks = bundle.get("checks", {})
    fields(checks, CHECKS, "checks")
    normalized = {}
    for name in CHECKS:
        check = dict(checks.get(name, {"status": "not_collected"})) if isinstance(
            checks.get(name, {}), dict) else checks[name]
        allowed = {"status", "detail", "observed_at"}
        if name == "dns":
            allowed |= {"query", "answers"}
        if name in {"gateway", "tcp"}:
            allowed |= {"target"}
        if name == "tcp":
            allowed |= {"port"}
        if name == "disk":
            allowed |= {"used_percent", "mount"}
        if name == "logs":
            allowed |= {"events"}
        fields(check, allowed, f"checks.{name}")
        status = check.get("status")
        valid = {"pass", "fail"} | UNOBSERVED
        if name == "service":
            valid = {"running", "stopped", "failed"} | UNOBSERVED
        if name in {"disk", "logs"}:
            valid = {"collected"} | UNOBSERVED
        require(isinstance(status, str) and status in valid,
                f"checks.{name}.status must be one of {sorted(valid)}")
        if "detail" in check:
            string(check["detail"], f"checks.{name}.detail")
        if status in UNOBSERVED:
            require(set(check) <= {"status", "detail"},
                    f"checks.{name}: unobserved checks cannot contain measurement fields")
        else:
            observed = timestamp(check.get("observed_at"), f"checks.{name}.observed_at")
            require(observed <= captured, f"checks.{name}.observed_at is after captured_at")
            check["age_minutes"] = round((captured - observed).total_seconds() / 60, 2)
            if name == "dns":
                string(check.get("query"), "dns.query", 253)
                answers = check.get("answers", [])
                require(isinstance(answers, list) and len(answers) <= 32,
                        "dns.answers must be a list of at most 32 IP addresses")
                for answer in answers:
                    require(isinstance(answer, str), "dns answers must be strings")
                    try:
                        ipaddress.ip_address(answer)
                    except ValueError as error:
                        raise BundleError("dns.answers contains an invalid IP address") from error
                require((status == "pass" and bool(answers)) or (status == "fail" and not answers),
                        "dns pass requires answers; dns fail must not contain answers")
            if name in {"gateway", "tcp"}:
                require(isinstance(check.get("target"), str), f"{name}.target must be an IP address string")
                try:
                    ipaddress.ip_address(check.get("target"))
                except (ValueError, TypeError) as error:
                    raise BundleError(f"{name}.target must be an IP address") from error
            if name == "tcp":
                require(type(check.get("port")) is int and 1 <= check["port"] <= 65535,
                        "tcp.port must be an integer from 1 to 65535")
            if name == "disk":
                used = check.get("used_percent")
                require(type(used) in {int, float} and math.isfinite(used) and 0 <= used <= 100,
                        "disk.used_percent must be a finite number from 0 to 100")
                string(check.get("mount"), "disk.mount", 200)
            if name == "logs":
                events = check.get("events")
                require(isinstance(events, list) and len(events) <= 200,
                        "logs.events must be a list of at most 200 events")
                for event in events:
                    fields(event, {"at", "level", "message", "signal"}, "log event")
                    when = timestamp(event.get("at"), "log event.at")
                    require(when <= observed, "log event.at cannot follow logs.observed_at")
                    require(isinstance(event.get("level"), str) and event["level"] in {"info", "warning", "error"},
                            "log event.level must be info, warning or error")
                    require(isinstance(event.get("signal"), str) and event["signal"] in {"none", "connect_timeout", "no_space", "service_exit"},
                            "log event.signal is not supported")
                    string(event.get("message"), "log event.message")
        normalized[name] = check
    return {**bundle, "checks": normalized}


def analyze(bundle):
    bundle = validate(bundle)
    checks = bundle["checks"]
    findings = []
    def add(code, priority, title, evidence, interpretation, next_step):
        findings.append(dict(code=code, priority=priority, title=title, evidence=evidence,
                             interpretation=interpretation, next_step=next_step))

    # Observations older than 30 minutes relative to the bundle are displayed but
    # excluded from correlations; this threshold is a demo policy, not an SLA.
    def fresh(name):
        return checks[name]["status"] not in UNOBSERVED and checks[name]["age_minutes"] <= 30
    def state(name):
        return checks[name]["status"] if fresh(name) else "unknown"

    missing = [name for name in CHECKS if checks[name]["status"] in UNOBSERVED]
    stale = [name for name in CHECKS if checks[name]["status"] not in UNOBSERVED and not fresh(name)]
    if missing:
        add("evidence_missing", 3, "Evidence is incomplete", missing,
            "An unknown or uncollected check is not a failed test or a healthy result.",
            "Collect the missing observations and record their timestamps before narrowing the cause.")
    if stale:
        add("evidence_stale", 2, "Some observations are too old to correlate", stale,
            "These observations are more than 30 minutes older than the bundle timestamp.",
            "Refresh these checks within the same incident window; do not combine old and current results.")

    if state("tcp") == "fail":
        evidence = [f"TCP test to {checks['tcp']['target']}:{checks['tcp']['port']} failed."]
        if state("gateway") == "fail":
            evidence.append("Gateway ICMP probe also failed.")
        if state("dns") == "pass":
            evidence.append("DNS returned an address at the time of collection.")
        add("tcp_unreachable", 1, "Investigate the device-to-service path", evidence,
            "The TCP observation supports a connectivity symptom. It does not distinguish routing, filtering, a remote listener, or a transient problem; a failed ICMP probe alone does not prove a gateway outage.",
            "Correlate the target, port, VLAN, route, firewall policy and remote listener with the network/application owners. Compare a known-good device in the same segment.")
    if state("dns") == "fail":
        add("dns_failure", 1, "Investigate name resolution", [f"DNS query for {checks['dns']['query']} failed."],
            "A failed lookup is observed; resolver availability, record contents and local configuration still need validation. A direct-IP TCP result does not validate DNS.",
            "Compare the configured resolver and query result with a known-good device; record the actual DNS response or timeout.")
    if state("gateway") == "fail" and state("tcp") != "fail":
        add("gateway_probe", 2, "Gateway ICMP response needs context", ["Gateway ICMP probe failed."],
            "ICMP may be filtered or deprioritized. This observation alone does not establish a forwarding outage.",
            "Review routes and neighbor state and compare application TCP results before escalating a gateway fault.")

    disk_high = fresh("disk") and checks["disk"]["used_percent"] >= 90
    if disk_high:
        add("disk_pressure", 1 if checks["disk"]["used_percent"] >= 95 else 2,
            "Review storage pressure", [f"{checks['disk']['mount']} is {checks['disk']['used_percent']}% used."],
            "Capacity is near the demo threshold. Percentage alone does not establish a write failure; inode exhaustion, quotas and filesystem state are separate checks.",
            "Check free bytes, inodes, retention settings and application write paths. Obtain an approved remediation plan before deleting data.")
    if state("service") in {"stopped", "failed"}:
        add("service_unhealthy", 1, "Investigate the application service", [f"Service state: {checks['service']['status']}."],
            "The service was not running at collection time. Its reason for stopping is not established by state alone.",
            "Review the service exit status and bounded recent logs; preserve evidence before an approved restart.")
    events = checks["logs"].get("events", []) if fresh("logs") else []
    captured = timestamp(bundle["captured_at"], "captured_at")
    recent_events = [e for e in events if (captured - timestamp(e["at"], "event.at")).total_seconds() <= 1800]
    signals = {event["signal"] for event in recent_events}
    if "no_space" in signals:
        evidence = [e["message"] for e in recent_events if e["signal"] == "no_space"]
        add("write_failure_log", 1, "Correlate application write failures with storage", evidence,
            "A recent no-space signal was supplied in the log bundle. " +
            ("High disk utilization strengthens a storage hypothesis, but the affected path and timing must still be confirmed." if disk_high else "Check the affected filesystem, inode availability and quotas before assigning a cause."),
            "Map the reported write path to its mount and verify the failure timestamps against the service exit. Escalate with both observations.")
    if "connect_timeout" in signals and state("tcp") == "fail":
        add("timeout_correlation", 2, "Recent logs align with the TCP symptom",
            [e["message"] for e in recent_events if e["signal"] == "connect_timeout"],
            "The application timeout and TCP failure are consistent with each other; neither identifies the failing network hop.",
            "Include both timestamps and the destination in the escalation; avoid labeling the ISP or firewall as the cause without evidence.")
    if not findings:
        add("no_failure_observed", 3, "No failing check found in this snapshot", list(CHECKS),
            "The supplied checks do not demonstrate a failure. This is not proof that the complete application or camera workflow is healthy.",
            "Compare this snapshot with the reported incident time and collect application-specific evidence or reproduction steps.")
    findings.sort(key=lambda item: (item["priority"], item["code"]))
    focus = {"tcp_unreachable": "device-to-service connectivity", "dns_failure": "name resolution",
             "disk_pressure": "storage capacity", "service_unhealthy": "the application service",
             "write_failure_log": "application write failures"}
    symptoms = [focus[f["code"]] for f in findings if f["priority"] == 1 and f["code"] in focus]
    customer = (f"We reviewed the diagnostic snapshot for {bundle['device']}. " +
                ("The current investigation is focused on " + "; ".join(symptoms) + ". " if symptoms else
                 "The available evidence does not yet isolate the reported issue. ") +
                "The cause is not confirmed. We are validating the related network and service observations before recommending a change. " +
                "We will share the next update after those checks are reviewed.")
    return {"incident_id": bundle["incident_id"], "device": bundle["device"],
            "captured_at": bundle["captured_at"], "reported_impact": bundle["reported_impact"],
            "checks": checks, "findings": findings, "root_cause": "unconfirmed",
            "customer_update_draft": customer,
            "handoff": {"next_actions": [f["next_step"] for f in findings],
                        "missing_evidence": missing, "stale_evidence": stale,
                        "changes_performed": "None. Offline review only.",
                        "reproduction": "Not reproduced by this tool; only supplied observations were analyzed."}}


def md(value):
    """Render untrusted evidence as literal inline text, not markup or links."""
    value = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for char in "\\`*_{}[]()#+-.!|":
        value = value.replace(char, "\\" + char)
    return value.replace("\n", " ").replace("\r", " ")


def markdown(report):
    lines = [f"# Support triage: {md(report['incident_id'])}", "",
             f"**Device:** {md(report['device'])}  ",
             f"**Snapshot:** {md(report['captured_at'])}  ",
             f"**Reported impact:** {md(report['reported_impact'])}  ",
             "**Root cause:** Unconfirmed. This is an offline evidence review.", "",
             "## Evidence status", "", "| Check | Status | Age at snapshot (minutes) | Detail |",
             "| --- | --- | --- | --- |"]
    for name, check in report["checks"].items():
        lines.append(f"| {name} | {md(check['status'])} | {check.get('age_minutes', 'N/A')} | {md(check.get('detail', ''))} |")
    lines += ["", "## Prioritized findings", "", "Priority is investigation order, not a production incident severity."]
    for finding in report["findings"]:
        lines += ["", f"### P{finding['priority']}: {md(finding['title'])}", ""]
        lines += [f"- Evidence: {md(evidence)}" for evidence in finding["evidence"]]
        lines += [f"- Interpretation: {md(finding['interpretation'])}", f"- Next step: {md(finding['next_step'])}"]
    lines += ["", "## Customer update draft", "", md(report["customer_update_draft"]), "",
              "## Engineering handoff", "", "- Changes performed: None; offline review only.",
              "- Reproduction: Not attempted by the analyzer.",
              f"- Missing evidence: {md(', '.join(report['handoff']['missing_evidence']) or 'None in this schema')}",
              f"- Stale evidence: {md(', '.join(report['handoff']['stale_evidence']) or 'None')}", "",
              "### Next actions", ""]
    lines += [f"{i}. {md(action)}" for i, action in enumerate(report["handoff"]["next_actions"], 1)]
    lines += ["", "Review this draft before using it in a customer case. It contains no verified root-cause or resolution claim.", ""]
    return "\n".join(lines)


def reject_constant(value):
    raise BundleError(f"Nonstandard JSON number is not permitted: {value}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_bundle(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "Bundle exceeds the 1 MiB size limit")
    return json.loads(raw.decode("utf-8-sig"), parse_constant=reject_constant,
                      object_pairs_hook=unique_object)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Local JSON evidence bundle")
    parser.add_argument("--output", type=Path, help="New directory for report.md and report.json")
    args = parser.parse_args(argv)
    try:
        report = analyze(load_bundle(args.bundle))
        if args.output:
            # A new directory prevents accidental replacement of prior evidence.
            args.output.mkdir(parents=True, exist_ok=False)
            (args.output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            (args.output / "report.md").write_text(markdown(report), encoding="utf-8")
            print(f"Wrote {args.output / 'report.md'} and {args.output / 'report.json'}")
        else:
            print(markdown(report), end="")
    except (BundleError, OSError, ValueError, TypeError, RecursionError) as error:
        print(f"Cannot analyze bundle: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
