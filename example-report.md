# Support triage: DEMO\-NET\-101

**Device:** edge\-lab\-01  
**Snapshot:** 2026\-09\-22T14:00:00Z  
**Reported impact:** Synthetic customer reports that one edge device stopped uploading event summaries\.  
**Root cause:** Unconfirmed. This is an offline evidence review.

## Evidence status

| Check | Status | Age at snapshot (minutes) | Detail |
| --- | --- | --- | --- |
| dns | pass | 1.0 | A record returned by the configured resolver\. |
| gateway | fail | 0.83 | ICMP probe did not receive a reply; forwarding has not been independently checked\. |
| tcp | fail | 0.67 | Direct\-IP TCP connection timed out\. |
| service | running | 0.5 | edge\-agent process is active; this does not prove successful uploads\. |
| disk | collected | 0.42 |  |
| logs | collected | 0.25 |  |

## Prioritized findings

Priority is investigation order, not a production incident severity.

### P1: Investigate the device\-to\-service path

- Evidence: TCP test to 203\.0\.113\.20:443 failed\.
- Evidence: Gateway ICMP probe also failed\.
- Evidence: DNS returned an address at the time of collection\.
- Interpretation: The TCP observation supports a connectivity symptom\. It does not distinguish routing, filtering, a remote listener, or a transient problem; a failed ICMP probe alone does not prove a gateway outage\.
- Next step: Correlate the target, port, VLAN, route, firewall policy and remote listener with the network/application owners\. Compare a known\-good device in the same segment\.

### P2: Recent logs align with the TCP symptom

- Evidence: Synthetic upload attempt to ingest\.example\.com timed out\.
- Interpretation: The application timeout and TCP failure are consistent with each other; neither identifies the failing network hop\.
- Next step: Include both timestamps and the destination in the escalation; avoid labeling the ISP or firewall as the cause without evidence\.

## Customer update draft

We reviewed the diagnostic snapshot for edge\-lab\-01\. The current investigation is focused on device\-to\-service connectivity\. The cause is not confirmed\. We are validating the related network and service observations before recommending a change\. We will share the next update after those checks are reviewed\.

## Engineering handoff

- Changes performed: None; offline review only.
- Reproduction: Not attempted by the analyzer.
- Missing evidence: None in this schema
- Stale evidence: None

### Next actions

1. Correlate the target, port, VLAN, route, firewall policy and remote listener with the network/application owners\. Compare a known\-good device in the same segment\.
2. Include both timestamps and the destination in the escalation; avoid labeling the ISP or firewall as the cause without evidence\.

Review this draft before using it in a customer case. It contains no verified root-cause or resolution claim.
