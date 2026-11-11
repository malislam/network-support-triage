# Live Claude example: editorial review required

This is an actual Claude API response to the synthetic routing fixture, regenerated once after removing case-specific prompt constraints. Model: `claude-haiku-4-5-20251001`. The draft wording below is unaltered and displayed as plain text (trailing whitespace normalized); these editorial notes were added afterward. No human approval or device action is claimed.

## Editorial review

- Supported observations: one route-change alert, then one TCP-failure alert 60 seconds later on the same fictional device. The second alert reports outage impact. Cause, actual onset time and affected scope remain unknown. No reported impact in the first alert is not proof of health.
- The title and evidence section infer delayed, user-visible impact and route modification. The supplied signals establish neither exact onset nor an actual configuration edit or user scope. The timestamps show observation order only.
- The hypotheses infer convergence, next-hop changes and TCP retransmission/timeout behavior. Those mechanisms are unsupported possibilities, not findings. The 60-second observation gap does not distinguish them.
- The timeline inserts a silent interval with convergence, loss or degradation occurring. No observations support that interval; retain only the two supplied events in an evidence timeline.
- The suggested prefix and next-hop details are absent from this fixture. They would require additional evidence. Historical interface logs, metrics and counters can be reviewed only if retained; current checks cannot reconstruct past conditions, and comparisons should use the intended state for the relevant time.
- The response has 363 whitespace-delimited words; the prompt's under-350-word instruction is advisory and is not enforced by the application.

Disposition: pending human review; not approved for operational use. Validate impact and collect available routing/path evidence before accepting a hypothesis. The model draft does not override deterministic severity, grouping, escalation or runbook fields.

## Original generated report

# Synthetic incident triage

**Human approval: pending. No changes executed.**

## Advisory summary (untrusted draft)

```text
# Incident 1: Routing Anomaly with Delayed TCP Impact

## What the evidence shows

At t+0s, device-1 observes a route change with no reported impact. Sixty seconds later, device-1 signals TCP failures associated with an outage. The 60-second delay between route modification and user-visible TCP breakdown suggests either transient traffic loss during convergence, or a cascading effect where the new route state gradually degrades reachability or introduces latency/packet loss that TCP eventually cannot tolerate.

## Hypotheses

**H1 (unconfirmed): Route withdrawn or repointed to unreachable/lossy path**
The route_change at t+0s altered next-hop resolution or path selection. The destination may have become unreachable, packet-loss-prone, or latency-bound over the new path. TCP sessions accumulate retransmission timeouts during this interval until application-layer timeouts or connection resets occur.

**H2 (unconfirmed): Route change triggered by upstream convergence event**
An external topology change (link failure, BGP withdrawal, OSPF reconvergence) caused device-1's route table to update. The 60-second gap may reflect routing protocol convergence delay or gradual session timeout exhaustion rather than a direct causality between route and TCP failure.

## Read-only checks

- Compare forwarding table snapshot (if available from t+0s) against current intended state; identify which route(s) changed and their new next-hops.
- Retrieve prefix and nexthop specifics from the route_change alert payload to confirm what destination(s) were affected.
- Check device-1's interface state and neighbor adjacency logs around t+0s for link or peer flaps.
- Review packet loss, latency, or jitter metrics on device-1's egress interfaces during [t+0s, t+60s].
- Inspect TCP/IP stack counters on device-1 (retransmits, connection resets, timeouts) to correlate with the outage window.
- If topology maps exist, verify whether the new next-hop for the affected prefix is actually reachable from device-1.

## Post-mortem notes

**Timeline sketch:**
t+0s → route change observed (cause: unknown)
t+0s–t+60s → silent interval (convergence, transient loss, or session degradation occurring)
t+60s → TCP failures reported as outage

**Open questions:**
- Which specific prefix(es) changed, and what were the old vs. new next-hops?
- Was device-1 the originator or follower of this route change?
- Did the route change to an invalid/unreachable next-hop, or to a slower/lossy one?
- Were any upstream topology events logged?

Human approval is required before proceeding.
```

## INC-a6d424b09916 — SEV1

Site: demo-branch-01; family: routing

Highest reported synthetic impact in this group; root cause unconfirmed.

Root cause: unconfirmed.

Escalation: Incident lead and network owner

Suggested investigation: Compare intended and observed routes; collect read-only path tests.

### Evidence timeline

- 2026-01-10T12:00:00Z | demo-alert-1 | demo-edge-01 | route_change | none
- 2026-01-10T12:01:00Z | demo-alert-2 | demo-edge-01 | tcp_failure | outage
