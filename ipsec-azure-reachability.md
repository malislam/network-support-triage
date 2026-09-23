# IPsec and Azure reachability

**Example:** A site behind a Palo Alto firewall cannot reach an approved application in an Azure virtual network. The Palo Alto-to-Azure topology here is synthetic. My experience includes Palo Alto and IPsec support, and troubleshooting Azure access through Cisco ASA; this example combines transferable checks rather than claiming this exact previous deployment.

## Define the test

Record the source, destination, application port, first failure, last success, and any recent network change. Confirm whether the application name resolves to its expected address and whether all site users are affected. Use an approved destination; do not infer application health from ping alone.

## Separate negotiation from traffic forwarding

On PAN-OS, these read-only operational commands show IKE/IPsec state and VPN flow information:

```text
show vpn ike-sa
show vpn ipsec-sa
show vpn flow
```

Command reference: [Palo Alto Networks — Troubleshoot Site-to-Site VPN Issues Using CLI](https://docs.paloaltonetworks.com/network-security/ipsec-vpn/administration/troubleshooting/troubleshooting-site-to-site-vpn-issues-using-cli). Check the installed version and access permissions before use.

| Evidence | Investigate next |
| --- | --- |
| IKE negotiation absent or failing | Peer reachability, peer addresses, approved authentication configuration, proposals, and timed logs from both ends |
| IKE present but expected IPsec SA absent | Negotiated settings and traffic selectors where applicable; compare both peers |
| SAs present but no traffic in either direction | Whether the test traffic reaches the firewall, the selected route/tunnel, and matching policy/NAT behavior |
| Outbound encrypted traffic increases but return traffic does not | Remote routing, permitted source/destination, destination service, and the return path with the cloud owner |
| Bidirectional tunnel traffic but one application still fails | That application's policy/logs, DNS result, service listener, and client/server evidence |

## Work with the Azure owner

Compare the connection's status and peer definitions with the site configuration. Review effective routes and applicable security rules on the workload path. Establish whether the issue is connectivity to the VM/service or within the service itself. Microsoft's [site-to-site troubleshooting guide](https://learn.microsoft.com/en-ca/azure/vpn-gateway/vpn-gateway-troubleshoot-site-to-site-cannot-connect) covers gateway and peer configuration checks; select the guidance for the actual gateway type and deployment.

Keep secrets and actual packet captures in approved storage. Do not paste shared keys into the incident or this repository. Do not clear SAs, reset a gateway, or broaden firewall/NSG rules as a routine first step; those actions can interrupt other traffic and require the appropriate change approval.

## Close or escalate

After an approved change, rerun the same source/destination/port test and confirm service with an affected user. Provide the next owner with timestamps, direction-specific observations, relevant policy/route findings, changes attempted, and current impact. If a tunnel came back without an established cause, document recovery separately from root cause.
