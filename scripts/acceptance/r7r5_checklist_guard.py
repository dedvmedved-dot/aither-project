#!/usr/bin/env python3
"""
R7-R5 Checklist Guard — validates execution checklist integrity.
Exit code 0 = valid, non-zero = invalid.
"""
import json
import sys
import os

CHECKLIST_PATH = os.environ.get("R7R5_CHECKLIST", "docs/evidence/u1.3-ops-r7-r5/execution-checklist.json")

def guard():
    if not os.path.exists(CHECKLIST_PATH):
        print(f"ERROR: Checklist not found at {CHECKLIST_PATH}")
        sys.exit(1)

    with open(CHECKLIST_PATH) as f:
        data = json.load(f)

    errors = []

    # 1. Exactly 30 directions
    dirs = data.get("directions", [])
    if len(dirs) != 30:
        errors.append(f"Expected 30 directions, got {len(dirs)}")

    # 2. Arithmetic check
    statuses = {}
    for d in dirs:
        s = d.get("status", "UNKNOWN")
        statuses[s] = statuses.get(s, 0) + 1

    total = sum(statuses.values())
    if total != 30:
        errors.append(f"Status count sum = {total}, expected 30")

    # 3. Required fields
    required = ["direction", "name", "status", "implementation_commit", "evidence_commit", "evidence_paths"]
    for d in dirs:
        for field in required:
            if field not in d:
                errors.append(f"Direction {d.get('direction', '?')} missing field: {field}")

    # 4. DONE validation
    for d in dirs:
        if d.get("status") == "DONE":
            if not d.get("implementation_commit"):
                errors.append(f"D{d['direction']}: DONE but no implementation_commit")
            if not d.get("evidence_commit"):
                errors.append(f"D{d['direction']}: DONE but no evidence_commit")
            if not d.get("run_id"):
                errors.append(f"D{d['direction']}: DONE but no run_id")
            if d.get("open_defects"):
                errors.append(f"D{d['direction']}: DONE but has open defects: {d['open_defects']}")
            if d.get("blocker"):
                errors.append(f"D{d['direction']}: DONE but has blocker: {d['blocker']}")

    # 5. COMPLETE check
    done_count = statuses.get("DONE", 0)
    if done_count == 30:
        in_progress = statuses.get("IN_PROGRESS", 0)
        todo = statuses.get("TODO", 0)
        failed = statuses.get("FAILED", 0)
        blocked = statuses.get("BLOCKED", 0)
        if in_progress > 0 or todo > 0 or failed > 0 or blocked > 0:
            errors.append(f"30 DONE but also {in_progress} IN_PROGRESS, {todo} TODO, {failed} FAILED, {blocked} BLOCKED")

    if errors:
        print(f"CHECKLIST GUARD FAILED: {len(errors)} errors")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"CHECKLIST GUARD PASSED: 30 directions, arithmetic valid")
    print(f"  DONE: {statuses.get('DONE', 0)}, IN_PROGRESS: {statuses.get('IN_PROGRESS', 0)}, TODO: {statuses.get('TODO', 0)}, FAILED: {statuses.get('FAILED', 0)}, BLOCKED: {statuses.get('BLOCKED', 0)}")
    sys.exit(0)

if __name__ == "__main__":
    guard()
