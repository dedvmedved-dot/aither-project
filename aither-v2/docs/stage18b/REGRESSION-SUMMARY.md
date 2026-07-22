# Stage 18B — Regression Summary

| ID | Check | Expected | Actual | Result | Evidence Source |
|----|-------|----------|--------|--------|----------------|
| R-01 | Accepted HEAD | `d1e641b...` | `d1e641b602b61c36a0b965c6d4c3a2e37c312d10` | ✅ PASS | `git rev-parse HEAD` |
| R-02 | Working tree baseline | CLEAN | CLEAN | ✅ PASS | `git status --short` |
| R-03 | Kubernetes API | reachable | reachable (https://10.129.13.78:6443) | ✅ PASS | `kubectl cluster-info` |
| R-04 | Nodes | Ready | n7 Ready, n8 Ready | ✅ PASS | `kubectl get nodes` |
| R-05 | containerd | active | active on both nodes | ✅ PASS | `systemctl is-active containerd` via SSH |
| R-06 | CRI | operational | RuntimeReady true, NetworkReady true | ✅ PASS | `crictl info` via SSH on n8 |
| R-07 | Registry API | available | `{}` 200 OK | ✅ PASS | `curl localhost:5000/v2/` |
| R-08 | Registry catalog | 3 repositories | aither-identity, aither-portal-backend, aither-ai-platform | ✅ PASS | `curl /v2/_catalog` |
| R-09 | Image tags | present | `stage18a-82fe433` on all 3 | ✅ PASS | `curl /v2/*/tags/list` |
| R-10 | Image digests | recorded | `sha256:427...`, `sha256:940...`, `sha256:ab2...` | ✅ PASS | `kubectl describe pod` |
| R-11 | Secret exists | PASS | `aither-identity-secret` exists | ✅ PASS | `kubectl get secret` |
| R-12 | Secret values not exposed | PASS | No exposure in files, logs, or evidence | ✅ PASS | Secret scan + review |
| R-13 | Missing Secret test | non-zero exit | exit 1 with clear message | ✅ PASS | Задание №5 |
| R-14 | Initial deploy | exit 0 | exit 0 | ✅ PASS | Задание №6 |
| R-15 | Identity rollout | PASS | Successfully rolled out | ✅ PASS | Deploy output |
| R-16 | Portal rollout | PASS | Successfully rolled out | ✅ PASS | Deploy output |
| R-17 | AI platform rollout | PASS | Successfully rolled out | ✅ PASS | Deploy output |
| R-18 | Repeated deploy | exit 0 | exit 0 | ✅ PASS | Задание №7 |
| R-19 | Idempotency | PASS | Generations unchanged, no duplicate resources | ✅ PASS | Задание №7 |
| R-20 | Secret UID unchanged | PASS | `4bfb16b9-...` unchanged | ✅ PASS | Задание №6–7 |
| R-21 | PVC unchanged | PASS | Both Bound, same PV | ✅ PASS | `kubectl get pvc,pv` |
| R-22 | Identity health ×3 | PASS | HTTP 200 ×3 | ✅ PASS | Задание №8 |
| R-23 | Portal health ×3 | PASS | HTTP 200 ×3 | ✅ PASS | Задание №8 |
| R-24 | AI platform health ×3 | PASS | HTTP 200 ×3 | ✅ PASS | Задание №8 |
| R-25 | Identity pod recovery | PASS | New pod Running, health 200 | ✅ PASS | Задание №9 |
| R-26 | Portal pod recovery | PASS | New pod Running, health 200 | ✅ PASS | Задание №9 |
| R-27 | AI platform pod recovery | PASS | Existing pod Running | ✅ PASS | Задание №9 |
| R-28 | First node containerd restart (n8) | PASS | active, Ready, CRI ok | ✅ PASS | Задание №10 |
| R-29 | Second node containerd restart (n7) | PASS | active, Ready | ✅ PASS | Задание №10 |
| R-30 | Registry restart | PASS | active, API available | ✅ PASS | Задание №11 |
| R-31 | Registry catalog preserved | PASS | 3 repos — unchanged | ✅ PASS | Задание №11 |
| R-32 | Registry digests preserved | PASS | Image pull: `Image is up to date` | ✅ PASS | Задание №11 |
| R-33 | Persistent marker preserved | PASS | `stage18b-persistence-marker-1784738828` | ✅ PASS | Задание №12 |
| R-34 | Missing manifest error | non-zero exit | exit 1, clear message | ✅ PASS | F5 |
| R-35 | Invalid cluster error | non-zero exit | exit 1, clear message | ✅ PASS | F2 |
| R-36 | Rollout failure path | non-zero exit | exit 1 (actual mock test) | ✅ PASS | F6 — mock kubectl rollout status → exit 1 |
| R-37 | Diagnostics on failure | PASS | deployment + pod output (actual mock test) | ✅ PASS | F6 — `ERROR: Rollout failed`, deployment + pod diagnostics emitted |
| R-38 | `bash -n` | PASS | 5/5 PASS | ✅ PASS | `bash -n` check |
| R-39 | shellcheck | PASS or NOT RUN | TOOL NOT INSTALLED | ⚠️ NOT RUN | `command -v shellcheck` |
| R-40 | Secret scan | CLEAN | No real secrets | ✅ PASS | Secret scan |
| R-41 | `git diff --check` | CLEAN | CLEAN | ✅ PASS | `git diff --check` |
| R-42 | Documentation consistency | PASS | All docs match actual state | ✅ PASS | Review |

## Summary

| Metric | Value |
|--------|-------|
| **PASS** | 41 |
| **FAIL** | 0 |
| **NOT RUN** | 1 (shellcheck — tool not installed) |
| **BLOCKED** | 0 |
