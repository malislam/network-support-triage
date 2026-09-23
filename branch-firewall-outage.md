# Recurring branch firewall outage

**Example platform:** SonicWall NSa; exact model and SonicOS version must be recorded during an actual incident.

**Trigger:** A site loses Internet access, application access, or VPN traffic, and the firewall may be unresponsive. This runbook is inspired by remote-site recovery work; the [Branch 07 case](branch-07-recurring-outage.md) is entirely synthetic.

## 1. Establish impact and the access path

- Record the site, first observed failure, affected services, timezone, and last known good state.
- Confirm whether one client, one VLAN, or the whole site is affected. Obtain a test from onsite staff as well as monitoring.
- Identify the physical circuit and firewall interface used by each test. A successful check through ISP B does not prove ISP A is healthy.
- Check whether a documented backup or out-of-band path is available. Do not create public management access during the outage.

## 2. Collect evidence before changing state

| Observation | What it suggests | Next check |
| --- | --- | --- |
| WAN link down or carrier handoff unavailable | Circuit or physical path may be involved | Compare link state, cabling, carrier status, and the other circuit |
| WAN link up, but expected traffic does not pass | Link state alone does not prove forwarding works | Test the approved next hop and a known service; compare firewall counters/logs |
| Firewall management unavailable, but user traffic passes | Management-path problem may be separate | Check allowed management source/path and resource alerts |
| Local switching works; multiple services fail through the firewall | Failure may be at the firewall or upstream | Compare both circuits, firewall health, and permitted traffic logs |
| One application fails while other services work | Site-wide recovery may be unnecessary | Trace that application's DNS, port, policy, and route |

If management is available, record uptime, resource observations, interface state, current alerts, and recent changes. Collect the diagnostic files requested for the installed version. SonicWall documents support-report and log collection in its [diagnostic information guide](https://www.sonicwall.com/it-it/support/knowledge-base/how-do-i-collect-sonicwall-product-diagnostic-information/kA1VN0000000LCd0AM). Store actual diagnostic bundles in approved restricted storage, not a public repository.

## 3. Decide whether recovery is justified

Use the existing approved recovery procedure or obtain emergency-change approval. Record who approved it and what service interruption is expected. Confirm that onsite assistance or another documented recovery path is available if remote access does not return.

A restart is an available recovery action only when the evidence, platform guidance, and approval support it. It is not the default response to every VPN or connectivity failure. If HA is present, establish peer health and the documented sequence first; do not improvise a restart of both members.

If the failure appears upstream, pursue the carrier case instead. If the device remains unresponsive and no controlled recovery path is available, escalate to the incident owner and vendor.

## 4. Verify and follow through

- Recheck Internet, DNS, VPN, and an affected application from a representative client.
- Compare interface/tunnel state and monitoring with the baseline; obtain onsite confirmation.
- Observe for the incident team's agreed period. A single successful ping is insufficient.
- Record **service restored; cause unconfirmed** if that is what the evidence supports.
- Keep a separate problem/vendor investigation for recurrence, including firmware/version, timestamps, diagnostics, and change history. Do not automate repeated reboots as a substitute for that investigation.
