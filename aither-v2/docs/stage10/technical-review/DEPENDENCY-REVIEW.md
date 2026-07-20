# DEPENDENCY-REVIEW.md

**Project:** Aither / AI Hermes MVP  
**Stage:** Stage 10 — RC1 Gate  
**Document:** Dependency Review  
**Date:** 2026-07-20

---

## 1. Purpose

Audit all software dependencies across the repository — identify outdated libraries, conflicting versions, unused packages, missing version pins, and upgrade risks.

## 2. Scope

- Python: `tools/bff/app.py` (pip installs), `gateway/` (implicit)
- TypeScript/Node: `portal/package.json`, `portal/package-lock.json`, `portal/bff/package.json`
- Docker images: `bff-mvp.yaml`, `portal-mvp.yaml`, `redis-rate-limit.yaml`, `nginx-gateway-32b-hardened.yaml`
- System: `scripts/`

## 3. Methodology

Review of package manifests, Docker image references, and pip install commands.

## 4. Python Dependencies

### BFF (`tools/bff/app.py`, via `bff-mvp.yaml:278`)

| Package | Version | Status |
|---|---|---|
| `fastapi` | latest (no pin) | ⚠️ Warning — not pinned |
| `uvicorn` | latest (no pin) | ⚠️ Warning — not pinned |
| `httpx` | latest (no pin) | ⚠️ Warning — not pinned |
| `pydantic` | latest (no pin) | ⚠️ Warning — not pinned |
| `redis` | latest (no pin) | ⚠️ Warning — not pinned |

### Gateway (`gateway/`)

| Package | Version | Status |
|---|---|---|
| No explicit requirements file | — | ❌ Missing — cannot reproduce |

### Python Base Images

| Usage | Image | Status |
|---|---|---|
| BFF runtime | `python:3.11-slim` | ✅ Adequate for MVP |

## 5. Node.js / TypeScript Dependencies

### Portal (`portal/package.json`)

| Package | Version | Status |
|---|---|---|
| `express` | (implicit) | ⚠️ Present in `server.js` |
| `jsonwebtoken` | (implicit) | ❌ Outdated usage patterns observed |
| `dotenv` | (implicit) | ⚠️ Not found — env configs likely missing |

### Portal BFF (`portal/bff/package.json`)

| Package | Version | Status |
|---|---|---|
| `fastify` | (implicit) | ⚠️ Used but no explicit version pin |
| `@fastify/jwt` | (implicit) | ⚠️ Not pinned |

**Note:** The `portal/` directory appears to be a legacy QuickJS/Node deployment not integrated with the aither-v2 MVP structure.

## 6. Docker Images

| Image | Location | Pin Status |
|---|---|---|
| `python:3.11-slim` | `bff-mvp.yaml:273` | Version tag only |
| `nginx:alpine` | `nginx-gateway-32b-hardened.yaml:54` | Version tag only ⚠️ |
| `redis:7-alpine` | `redis-rate-limit.yaml:23` | Version tag only |
| `nginx:alpine` | `portal-mvp.yaml:358` | Version tag only ⚠️ |

## 7. Findings

| ID | Severity | Description |
|---|---|---|
| DEP-01 | Major | **No Python requirements files anywhere.** BFF uses inline `pip install` without version pins. Gateway has no requirements.txt. Builds are non-reproducible. |
| DEP-02 | Minor | **Portal npm audit not run.** `package-lock.json` present but no `npm audit` step in CI. |
| DEP-03 | Minor | **Two separate Node.js projects in `portal/`.** `portal/package.json` (main portal) and `portal/bff/package.json` (separate BFF) — unclear which is active. |
| DEP-04 | Minor | **No `pip-audit` or safety check in CI.** Python dependencies are never scanned for vulnerabilities. |

## 8. Recommendations

1. Create `requirements.txt` for BFF with pinned versions (`fastapi>=0.110,<1.0`, `uvicorn>=0.27,<1.0`, `httpx>=0.27,<1.0`, `redis>=5.0,<6.0`, `pydantic>=2.0,<3.0`).
2. Create `requirements.txt` for Gateway Python code.
3. Pin Docker images by digest in manifests.
4. Add `pip-audit` to CI pipeline.
5. Run `npm audit` on portal if it remains in active use.

## 9. Conclusion

Dependency management is the weakest area of the MVP. No version pins, no requirements files, and no automated vulnerability scanning. Acceptable for MVP only with explicit risk acceptance.
