# Stage U1.0 — Executive Summary

## Stage

Stage U1.0 — Governance и фиксация архитектуры пользовательского доступа

## Status

AWAITING EXTERNAL AUDIT

## Purpose

Define, document, and verify the user access architecture for Aither / AI Hermes MVP Internal Pilot before any network or runtime changes.

## Key Deliverables

1. User Access Architecture document
2. Endpoint Matrix (current + target)
3. Access Security Baseline
4. Stage U1 Roadmap
5. Architecture Decision Records (7 ADRs)
6. Project Master update (Track A, Stage U1)
7. Full evidence package (11 reports)

## Key Findings

| ID | Severity | Description | Owning Stage |
|----|----------|-------------|-------------|
| U1-GAP-001 | HIGH | DNS `fb1.spb.ru` not configured | U1.1 |
| U1-GAP-002 | HIGH | No TLS certificate for `fb1.spb.ru` | U1.1 |
| U1-GAP-003 | MEDIUM | No TLS certificate for `10.129.13.78` | U1.1 |
| U1-GAP-004 | HIGH | No Ingress or reverse proxy deployed | U1.2 |
| U1-GAP-005 | HIGH | Portal Frontend nginx uses HTTP only | U1.2 |
| U1-GAP-006 | MEDIUM | `/v1/chat/completions` dual routing path | U1.3 |
| U1-GAP-007 | HIGH | `/api/v1/chat/completions` not exposed | U1.4 |
| U1-GAP-008 | MEDIUM | No user documentation | U1.5 |
| U1-GAP-009 | MEDIUM | API Key management not accessible externally | U1.3 |
| U1-GAP-010 | MEDIUM | `10.129.13.78` is node IP, not service endpoint | U1.2 |

## Runtime Access

AVAILABLE (intermittent — 1% K8s API timeout due to conntrack on n8)

## Markdown Verification

- All code fences: paired and even count
- No broken table formatting
- No absolute local paths
- No secrets in evidence
- No non-evidenced PASSED statuses

## Final Declarations

- Stage U1.0: AWAITING EXTERNAL AUDIT
- Stage U1.1: NOT STARTED
- Internal Pilot: NOT YET OPEN
- Stage U2: BLOCKED BY STAGE U1
- Production v1.0: NO-GO
