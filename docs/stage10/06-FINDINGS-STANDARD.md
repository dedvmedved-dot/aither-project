
# 06-FINDINGS-STANDARD

**Project:** Aither / AI Hermes MVP  
**Stage:** Stage 10 — RC1 Gate

## 1. Purpose
This document defines the mandatory classification, lifecycle and handling of audit findings discovered during Stage 10.

## 2. Severity Levels

### Critical
A finding that prevents acceptance, compromises integrity, security, safety, evidence validity or RC1 requirements.

### Major
A finding affecting mandatory functionality or acceptance criteria but not causing immediate integrity failure.

### Minor
A documentation, formatting or low-risk implementation issue that does not prevent RC1.

### Observation
Recommendation for improvement with no nonconformity.

## 3. Status Lifecycle

Open → Confirmed → Assigned → In Progress → Ready for Review → Verified → Closed

Rejected findings shall include documented justification.

## 4. Mandatory Fields

Each finding shall contain:

1. Identifier
2. Title
3. Requirement reference
4. Evidence reference
5. Commit SHA
6. Severity
7. Owner
8. Target resolution
9. Verification method
10. Closure decision

## 5. Resolution Rules

Critical and Major findings must be corrected and re-audited before final PASSED unless explicitly accepted by the defined governance process.

Every correction requires:

- new Commit SHA;
- updated Evidence;
- repeat external audit.

## 6. Acceptance Rules

A finding may be closed only when:

- corrective action is committed;
- evidence is updated;
- independent verification succeeds;
- external auditor confirms closure.

Hermes may propose closure but cannot declare it closed.

## 7. Reporting

Audit reports shall summarize:

- findings by severity;
- open findings;
- closed findings;
- deferred findings with justification;
- recommendation for RC1.

## 8. Responsibilities

Hermes:
- records findings;
- prepares evidence;
- implements fixes.

Owner:
- coordinates delivery.

External auditor:
- validates closure;
- assigns PASSED / FAILED / PASS WITH FINDINGS.

## 9. Final Rule

Only independently verified findings may be considered closed.
