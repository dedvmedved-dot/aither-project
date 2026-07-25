# TRACK-A-R3.1 — REPRODUCIBILITY SUMMARY
============================================================

Repository:  dedvmedved-dot/aither-project
Branch:      aither-v2

Rejected commit:      62783811a8dece59f5f8062f586dd183a2b72e8f

Implementation commit: 1ed95001ffa817fb5c774a2ed5ebf58d810be759
  Contains: test_r3_identities.py fix (pytest._r3_agent_keys removal),
            close-modal investigation

Tested commit:         1ed95001ffa817fb5c774a2ed5ebf58d810be759
  All 40/40 test runs executed on this exact commit

Evidence commit:       bb224c4b01a8602252f9b154dd9b650715259cc6
  Adds: JUnit XMLs, logs, acceptance matrix update
  Parent: 1ed95001ffa817fb5c774a2ed5ebf58d810be759
  No test code changes — only evidence files

Final documentation commit: <set at next push>

Current Remote HEAD:   bb224c4b01a8602252f9b154dd9b650715259cc6

Test source SHA-256:   963f6df157c4ffb265d83f82a2978bca1e7f45217bf5c1dcfbdc165fa62e85e1
Test source unchanged between tested and evidence commits: YES

Local/Remote match: YES
Working tree before tests: CLEAN

## closeModal Root Cause
closeModal was referenced in an intermediate UNCOMMITTED version of
test_r3_identities.py that used standalone functions. The committed
version uses class-based tests with DOM-based modal closure:
  page.locator("#modal-overlay").click(position={"x": 1, "y": 1})
No closeModal call exists in committed test code.

closeModal references in final test_r3_identities.py: 0

## Test File Integrity
Working-tree SHA-256: 963f6df157c4ffb265d83f82a2978bca1e7f45217bf5c1dcfbdc165fa62e85e1
HEAD SHA-256:         963f6df157c4ffb265d83f82a2978bca1e7f45217bf5c1dcfbdc165fa62e85e1
Hashes match: YES

## Fix Applied for R3.1
- Removed pytest._r3_agent_keys hidden inter-test state
- All 10 tests are fully independent — no order dependency

## Control Test Results

Individual BETA01:        4/4 PASSED  Exit code: 0
Individual BETA02:        2/2 PASSED  Exit code: 0
Individual OWNER01:       2/2 PASSED  Exit code: 0
Individual Agent:         2/2 PASSED  Exit code: 0

Full Run 1:              10/10 PASSED  Exit code: 0  (226.31s)
Full Run 2:              10/10 PASSED  Exit code: 0  (226.61s)

Fresh-Clone Run:         10/10 PASSED  Exit code: 0  (226.74s)

Combined complete runs:  40/40 PASSED

## Internet 32B Stability
10/10 HTTP 200, 0 HTTP 504, 0 timeout, 0 empty response

## Security Evidence
7/7 files present and non-empty
No secrets leaked in evidence files

## Acceptance Matrix
52/52 PASS = 100%

## Evidence Inventory
evidence/track-a-r3.1/
├── 00_SUMMARY.md
├── close-modal-investigation.txt
├── git-state-before-test.txt
├── source-hashes.txt
├── beta01.xml / beta01.log
├── beta02.xml / beta02.log
├── owner.xml   / owner.log
├── agent.xml   / agent.log
├── full-r3-run-1.xml / full-r3-run-1.log
├── full-r3-run-2.xml / full-r3-run-2.log
├── fresh-clone-r3.xml / fresh-clone-r3.log
└── internet-32b-stability.txt

## User Distribution
BLOCKED — awaiting ChatGPT external audit
