# Wireless client connectivity

**Example equipment:** Juniper EX4300 switching and Mist AP43 access points. This is a newly authored diagnostic example, not an exported site procedure.

## Record the failing attempt

Capture the site, AP, SSID, client identifier in the approved ticket, timestamp/timezone, location, and exact symptom. Compare with a working client on the same SSID and with the affected client on another approved connection. Avoid moving multiple variables at once.

## Follow the connection

| Boundary | Evidence to collect | Decision |
| --- | --- | --- |
| AP power and uplink | AP connectivity, switch link/PoE state, interface errors, recent port changes | Multiple APs on one switch failing directs attention upstream; one AP failing needs a narrower comparison |
| Association/authentication | Client events at the reported time, SSID/security settings, authentication result | An authentication rejection goes to identity/policy investigation before DHCP troubleshooting |
| Addressing | Client IP, gateway, VLAN assignment, DHCP transaction/lease availability | No usable address requires checking the assigned VLAN and DHCP path |
| Gateway and DNS | Gateway reachability and a lookup for a known permitted service | A DNS failure with working IP connectivity is a different fault from a broken client VLAN |
| Application | Destination/port, policy result, traffic direction, working comparison | If the network path works, provide application support the specific failed request and timestamp |

Mist's [wireless SLE documentation](https://www.juniper.net/documentation/us/en/software/mist/mist-aiops/shared-content/topics/topic-map/wireless-sle.html) provides client connection and AP health categories that help locate the failing stage. Treat those observations as evidence to investigate, not a substitute for a client test.

For an AP that is disconnected, compare its management addressing and the switch port's intended VLANs before changing the radio configuration. Juniper's [AP disconnection guide](https://www.juniper.net/documentation/us/en/software/mist/mist-wireless/topics/ref/troubleshoot-ap-disconnect-issues.html) describes checking port configuration and DHCP availability.

## Change and validation

Make a change only after identifying the affected scope and recording the prior setting. Obtain the required approval for VLAN, port, WLAN, or authentication changes. A working AP should not be restarted just because one client reports an application problem.

Repeat the same client test after the change. Verify address assignment, name resolution, and the affected application; test roaming only if it was part of the reported problem. Capture the result and observation period. Escalate with the client/AP timestamps, failing stage, comparisons, and relevant logs if the fault remains.
