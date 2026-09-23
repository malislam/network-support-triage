# Read-only Linux evidence collection

This is a learning checklist for an authorized lab or support session, not a statement that these commands were used at a former employer. Check installed tools and permissions first. Capture the incident time and timezone before comparing observations.

| Question | Example read-only command | Limit |
| --- | --- | --- |
| What address and route does the host have? | `ip address show` and `ip route show` | Configuration alone does not establish forwarding |
| Does the host resolve the intended name? | `getent ahosts ingest.example.com` | Uses the host's name-service configuration; record the actual result |
| Is the systemd service running? | `systemctl status edge-demo.service --no-pager` | Fictional service name; a running process may still fail requests |
| What happened around the failure? | `journalctl -u edge-demo.service --since '15 minutes ago' --no-pager -n 100` | Review/redact logs before sharing; access may require permission |
| Is storage exhausted? | `df -h` and `df -i` | Check the actual write mount, inodes and quotas; do not delete logs as a default fix |

Use the application's approved destination and protocol to test service connectivity. A successful TCP handshake does not validate TLS, authentication, camera processing, or uploads. A failed ping does not establish a gateway outage.

Record actual outputs and timestamps in a restricted ticket. The JSON fixtures normalize observations manually; the Python tool does not run or parse these commands.

References: [systemctl](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html), [journalctl](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html), [GNU df](https://www.gnu.org/software/coreutils/manual/html_node/df-invocation.html).
