# U1.3-WUI-R1 — CORRECTIONS

## Defect 1: Agent Page — ReferenceError

**Finding:** `renderAgentPage()` called from `showPage('agent')` but never defined.

**Impact:** JavaScript error in console when navigating to Agent Page.
Page structure was visible (CSS class toggle works), but dynamic content (API URL, model list) was not populated.

**Fix:**
- Added `renderAgentPage()` function with:
  - Dynamic API base URL based on zone origin
  - Model list loaded via API `/models`
- Added `if (page === 'agent') renderAgentPage()` to nav link click handlers

**File changed:** `portal/static/index.html` (+27 lines)

## Defect 2: Model Key Selection

**Finding:** `#modal-token-models` select option values confirmed correct:
- `both`, `qwen-14b`, `qwen-32b-base`

**Manual reproduction:** Options present and selectable. No code change required.
Previous failures likely due to stale ConfigMap deployment during initial U1.3 run.

**Verification:** Full suite re-run after clean deployment.
