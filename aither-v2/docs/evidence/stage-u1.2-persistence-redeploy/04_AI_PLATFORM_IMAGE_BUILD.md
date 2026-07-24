# AI Platform Image Build

## Image Details
- **Tag:** `10.129.13.78:5000/ai-platform:u1.2-persistence-20260725-0004`
- **Image ID:** `sha256:fcf111165f61720e8d010e0b204c0c798cfe89df26b4f085174cca93f499783b`
- **Built on:** VPS2 (10.129.13.78 via localhost), pushed to local registry
- **Build time:** 2026-07-25 00:04 UTC

## Changes from Previous Image (`u1-3-models-fix`)
- 429 passthrough: 3 code blocks handle HTTP 429 from upstream (was converted to 502)
- All other code unchanged

## Verification
- AST analysis confirms 3 x `400 <= status_code < 500` blocks in running pod
- Pod `aither-ai-platform-84c478c874-rh6mg` running new image
- 0 restarts after deploy

## Rollback
- Previous image: `10.129.13.78:5000/ai-platform:u1-3-models-fix`
- Command: `kubectl rollout undo deploy/aither-ai-platform -n aither-inference`
