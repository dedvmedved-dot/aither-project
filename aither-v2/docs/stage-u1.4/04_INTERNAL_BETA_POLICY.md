# Internal Beta Policy

## Scope
Closed beta for Aither AI Platform, limited to internal users only.

## Maximum Users
**5 users** — strictly enforced. Additional users require explicit approval.

## Allowed Load
- Maximum 300 requests per minute per client (gateway-enforced)
- Maximum 30 concurrent requests per client
- Total sustained load: ≤2 requests/second average
- Peak burst: ≤5 requests/second for <10 seconds

## Beta Operating Hours
- **Availability target:** 12 hours/day (08:00-20:00 local time)
- Outside hours: system may be unavailable for maintenance
- No SLA during beta period
- Planned maintenance: announced 24 hours in advance

## User Eligibility
- Internal team members only
- Must sign Beta Participation Agreement (acknowledge known limitations)
- Must agree to provide feedback within 48 hours of encountering issues
- API key is personal and non-transferable

## Bug Reporting
- Use designated feedback channel
- Required information: request details, expected vs actual behavior, timestamp
- See `05_FEEDBACK_PROCESS.md` for full procedure

## Update Policy
- Updates deployed during maintenance windows (or emergency fixes anytime)
- Users notified of breaking changes
- API backward compatibility maintained within Beta period
- Model updates require advance notice

## Beta Stop Criteria
Beta will be PAUSED or TERMINATED if:
1. Critical security vulnerability discovered
2. Data loss or corruption incident
3. >4 hours continuous unavailability
4. GPU failure requiring extended repair
5. >5 unresolved P1/P2 bugs

## Beta Success Criteria (→ Production)
Beta graduates to Production when:
1. All P1/P2 bugs resolved
2. 30 days without critical incidents
3. Monitoring and backup gaps addressed (see U1.3 gaps)
4. ≥80% user satisfaction from feedback
5. Architecture owner sign-off

## Data Policy
- User conversations are ephemeral — not persisted across requests
- API keys and user IDs stored in SQLite database
- No PII collection policy in place yet
- Databases subject to manual backup only

## Incident Response
- P1 (total outage): immediate response
- P2 (partial outage): <30 min response
- P3 (degraded): <2 hours
- See `RUNBOOK_INCIDENT.md` for procedures
