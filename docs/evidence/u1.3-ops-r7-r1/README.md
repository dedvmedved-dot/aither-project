# U1.3-OPS-R7-R1 — Critical User Safety Gate

This iteration addresses only defects that could directly impact users
during limited handover:

1. Redis/Lua safety fix (NameError + unsafe fallback removal)
2. Exact token_id↔secret correlation
3. Cross-replica revoked-token validation
4. Session invalidation with raw evidence
5. Gitleaks current-state scan
6. Post-fix Track A 10/10 + Full WUI 28/28

Commit chain: e4013bd → P (implementation) → Q (evidence)
