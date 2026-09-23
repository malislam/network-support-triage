# Incident handoff and customer updates

The next engineer should be able to continue without repeating every test. Keep observed facts separate from assumptions, and make the next owner and next update time explicit.

## Handoff template

```text
Incident:
Site/service:
Current impact and affected users:
First observed / last known good (with timezone):
Current status: investigating / recovering / monitoring / restored

Observed evidence:
- Test, vantage point, timestamp, result

Working hypothesis (not confirmed root cause):

Actions completed:
- Time, action, approval/change reference, result

Changes to avoid repeating / remaining risk:

Next actions:
- Named owner, action, expected update time

Open carrier/vendor cases:
Restricted evidence location:
Customer contact and last update:
Next customer update:
Handoff accepted by / time:
```

## Customer update examples

These messages refer to the [synthetic Branch 07 case](branch-07-recurring-outage.md).

**Investigating**

> Branch 07 is unable to access the Internet and the internal scheduling service. Local switching remains available. We are checking the firewall and both circuit paths with the site contact. The cause is not confirmed. Our next update will be at T+20 minutes, or sooner if service changes.

**Recovery underway**

> We have approval to restart the branch firewall after collecting the available diagnostics. This will temporarily interrupt connectivity through that device. The site contact is available to assist if remote access does not return. We will test the affected services before reporting recovery.

**Service restored**

> Internet access and the internal scheduling service are working again, and the site contact has confirmed successful tests. Service recovered after the approved firewall restart. We have not established why the device stopped forwarding traffic. The recurring issue remains open for vendor investigation, with monitoring continuing through the agreed observation period.

## Before handing off

- Assign the incident and any separate problem investigation to an accepting owner.
- State whether business service is restored, whether monitoring is clear, and whether the cause is known; these are different facts.
- Include the next update commitment even if a vendor has not replied.
- Keep customer messages focused on impact and actions. Store credentials, internal addressing, diagnostic bundles, and detailed captures in the approved restricted system.
