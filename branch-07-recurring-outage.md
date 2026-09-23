# Synthetic incident: Branch 07 recurring outage

**Portfolio exercise — no customer incident, production log, or measured employment result is represented here.** The recurring-firewall symptom is inspired by remote-site work. All names, addresses, times, results, and process details below were created for this example.

## Scenario

Users at Branch 07 lose Internet access and the internal scheduling application. The branch has a SonicWall NSa firewall and two ISP circuits. The primary service path uses ISP A. A documented restricted management path over ISP B reaches the firewall; it does not bypass the firewall for user traffic.

| Example component | Synthetic identifier |
| --- | --- |
| Firewall | `branch07-fw.example.com` |
| ISP A firewall address / next hop | `198.51.100.2` / `198.51.100.1` |
| ISP B firewall address / next hop | `203.0.113.2` / `203.0.113.1` |
| Test workstation | `192.0.2.25` |
| Incident / recurring problem | `DEMO-INC-007` / `DEMO-PRB-003` |

These documentation addresses illustrate the investigation only. They are not a routable deployment plan.

## Evidence and decisions

| Elapsed time | Synthetic observation or action | Decision |
| --- | --- | --- |
| T+00 | Monitoring reports the main site path unavailable | Open an incident and verify user impact |
| T+04 | Site contact confirms multiple clients affected; local switch connectivity works | Broaden beyond a single endpoint; local switching has not failed completely |
| T+07 | Carrier reports no active ISP A outage; WAN link is up | Carrier response and link state alone do not rule out an upstream problem |
| T+10 | Restricted management over ISP B responds slowly; both WAN links show up; allowed application tests through the firewall fail | Compare forwarding and management behavior; do not conclude both circuits are healthy |
| T+14 | Available diagnostics, interface observations, recent changes, and timestamps are saved in restricted case storage | Preserve evidence before changing device state |
| T+18 | Incident owner approves the documented restart; site contact is available for recovery assistance | Proceed under emergency change `DEMO-CHG-009` |
| T+24 | Firewall returns; representative Internet, DNS, and VPN/application tests succeed | Enter monitoring; request user confirmation |
| T+29 | Site contact confirms the scheduling service works; alerts clear | Report service restored, with cause unconfirmed |
| T+54 | Tests remain successful during the agreed 30-minute observation period after restart | Hand off monitoring and the open recurring-problem investigation |

## What this proves — and what it does not

The evidence supports that service recovered after a controlled firewall restart. It does not establish a firmware defect, memory leak, ISP fault, or permanent repair. Slow management and failed forwarding are symptoms. A carrier reporting no outage is one data point, not proof of end-to-end circuit health.

I would leave the recurring issue open. The next steps are to compare current diagnostics with prior occurrences, have the vendor review the installed version and hardware health, and plan any recommended corrective change with validation and rollback. I would not schedule recurring reboots and call the problem resolved.

## Handoff extract

```text
Incident: DEMO-INC-007
Status: Service restored; monitoring and recurring-problem investigation continue
Impact: Internet and internal scheduling service unavailable at Branch 07
Recovery: Approved restart under DEMO-CHG-009
Validation: Representative DNS, Internet, VPN/application tests and user confirmation
Cause: Unconfirmed
Risk: Similar symptoms may recur; permanent corrective action not established
Next owner: Example Network Operations engineer
Next action: Review vendor response on DEMO-PRB-003 and correlate diagnostics
Next update: At the next agreed support checkpoint, or immediately on recurrence
Evidence: Restricted incident storage (no real files are supplied in this exercise)
```

Related: [branch recovery runbook](branch-firewall-outage.md) · [handoff template](incident-handoff.md).
