# Risks and Blockers — Stage U1.0

## Blockers

| ID | Blocker | Stage | Description |
|----|---------|-------|-------------|
| B-01 | No Ingress controller | U1.2 | Cannot expose Portal without Ingress. No alternative (NodePort, LoadBalancer) exists. |
| B-02 | No DNS resolution | U1.1 | `fb1.spb.ru` not configured. External domain access requires DNS + TLS. |
| B-03 | No TLS certificate | U1.1 | No trusted certificate for `fb1.spb.ru`. HTTPS cannot be properly configured. |

## Risks

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R-01 | K8s API 1% timeout (conntrack) | HIGH | Intermittent Ingress health check failures | Sysctl mitigation applied; needs hardware fix |
| R-02 | Single GPU node (n7) for vLLM | MEDIUM | No redundancy; n7 failure = no inference | Accepted for Internal Pilot |
| R-03 | No monitoring/alerting | HIGH | Cannot detect outages | Deferred to post-U1 |
| R-04 | No backup/restore test for user data | MEDIUM | Data loss risk | Test needed before opening to users |
| R-05 | Portal Frontend has direct `/v1/chat/completions` proxy | MEDIUM | Auth bypass risk | Assigned to U1.3 |
| R-06 | n7 MissingClusterDNS | MEDIUM | Pod DNS resolution unreliable | Workaround via ClusterIP in ConfigMap (deployed) |
| R-07 | TLS by IP for internal access | LOW | Certificate mismatch warning | Document as known limitation or use internal DNS |
