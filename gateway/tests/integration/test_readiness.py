"""R7-R5-EMG-GW-R5 — Readiness Integration Tests (READY-001..008)

Gateway /ready endpoint HTTP integration tests.
Test accounting: UNIT PASS | STATIC REVIEW | INTEGRATION PASS | RUNTIME PASS | E2E PASS | FAIL | SKIPPED | NOT EXECUTED

Only tests with actual runtime execution and exit code count as PASS.
Static code-review checks are classified as STATIC REVIEW — NOT included in PASS count.
"""
import urllib.request, json, sys, os

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://aither-gateway.aither-inference.svc.cluster.local:8000")
BASE = GATEWAY_URL.rstrip("/")

passed = 0          # RUNTIME PASS only
static_review = 0   # STATIC REVIEW
failed = 0
results = []

def runtime_check(test_id, desc, status, expected):
    global passed, failed
    ok = status == expected
    tag = "RUNTIME PASS" if ok else "FAIL"
    if ok: passed += 1
    else: failed += 1
    results.append({"test": test_id, "description": desc, "category": tag, "expected": expected, "actual": status})
    print(f"[{tag}] {test_id}: {desc} (expected {expected}, got {status})")

def static_review_check(test_id, desc, expected_behavior):
    global static_review
    static_review += 1
    results.append({"test": test_id, "description": desc, "category": "STATIC REVIEW", "expected": expected_behavior, "actual": "CODE VERIFIED"})
    print(f"[STATIC REVIEW] {test_id}: {desc} — expected: {expected_behavior}")

def get_ready():
    try:
        r = urllib.request.urlopen(f"{BASE}/ready", timeout=5)
        body = json.loads(r.read().decode())
        return r.status, body
    except Exception as e:
        return 0, {"error": str(e)}

print("=" * 60)
print("READINESS INTEGRATION TESTS (corrected accounting)")
print("=" * 60)

# READY-001: All deps healthy → 200 (RUNTIME)
s, body = get_ready()
runtime_check("READY-001", "all dependencies healthy", s, 200)
if s == 200:
    deps = body.get("dependencies", {})
    print(f"  deps: redis={deps.get('redis')}, postgres={deps.get('postgres')}, "
          f"catalog={deps.get('catalog')}, "
          f"14b={deps.get('model_qwen-14b')}, 32b={deps.get('model_qwen-32b-base')}")
else:
    print(f"  FAIL: status={s}, body={body}")

# READY-002..008: STATIC REVIEW (code design verification, not runtime)
print("\n--- Static reviews (NOT counted as PASS) ---")
static_review_check("READY-002", "empty catalog → 503", "critical_fail=True when catalog empty")
static_review_check("READY-003", "missing 14B from catalog → 503", "model=None after ID-based lookup → critical_fail=True")
static_review_check("READY-004", "missing 32B from catalog → 503", "model=None after ID-based lookup → critical_fail=True")
static_review_check("READY-005", "14B HTTP 500 → 503", "resp.raise_for_status() on non-2xx")
static_review_check("READY-006", "32B timeout → 503", "httpx.TimeoutException → critical_fail=True")
static_review_check("READY-007", "Redis unavailable → 503", "ping() fails → critical_fail=True")
static_review_check("READY-008", "PostgreSQL unavailable → 503", "billing_enabled=True + PG down → critical_fail=True")

print()
print("=" * 60)
total = passed + static_review + failed
print(f"RESULTS: {passed} RUNTIME PASS, {static_review} STATIC REVIEW, {failed} FAIL ({total} total)")
print("=" * 60)

for r in results:
    cat = r["category"]
    print(f"  [{cat}] {r['test']}: {r['description']}")

# Exit code: fail only on actual runtime failures
sys.exit(0 if failed == 0 else 1)
