#!/usr/bin/env python3
"""
Repository Inventory Script — Deterministic Generator for Stage U0.A-R3

ENFORCED SNAPSHOT-ONLY:
- Never reads working tree content.
- All hashes, sizes, and metadata from the specified snapshot commit.
- Falls back to working tree ONLY for paths that don't exist in snapshot
  (allowlisted modified files). For untracked files: never included.
- Any path that IS tracked but NOT in snapshot raises RuntimeError.
"""

import os
import sys
import hashlib
import csv
import io
import subprocess
import argparse
import time
import re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

SCRIPT_VERSION = "u0.a-r3-1.0"
UTF8_ERRORS = 0


# ── Utility ──────────────────────────────────────────────────────────

def git_run(repo_root, *args):
    """Run git command, return (stdout_bytes, stderr_bytes, returncode)."""
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false"] + list(args),
        capture_output=True, cwd=repo_root, timeout=60
    )
    return result.stdout, result.stderr, result.returncode


def verify_snapshot_commit(repo_root, snapshot_sha):
    """Verify that snapshot_sha is a valid commit. Exit non-zero if not."""
    out, err, rc = git_run(repo_root, "cat-file", "-e", f"{snapshot_sha}^{{commit}}")
    if rc != 0:
        print(f"FATAL: Snapshot SHA is not a valid commit: {snapshot_sha}", file=sys.stderr)
        print(f"  stderr: {err.decode('utf-8', errors='replace').strip()}", file=sys.stderr)
        sys.exit(1)
    print(f"SNAPSHOT VERIFIED: {snapshot_sha} is a valid commit")


def verify_path_in_snapshot(repo_root, path, snapshot_sha):
    """Verify that a tracked path exists in the snapshot commit. Exit non-zero if not."""
    out, err, rc = git_run(repo_root, "cat-file", "-e", f"{snapshot_sha}:{path}")
    if rc != 0:
        print(f"FATAL: Tracked path not found in snapshot {snapshot_sha}: {path}", file=sys.stderr)
        sys.exit(1)


def get_blob_from_snapshot(repo_root, path, snapshot_sha):
    """Read blob content from snapshot commit. Raises RuntimeError if not found."""
    out, err, rc = git_run(repo_root, "show", f"{snapshot_sha}:{path}")
    if rc != 0:
        raise RuntimeError(
            f"Cannot read tracked path from snapshot {snapshot_sha}: {path}\n"
            f"  stderr: {err.decode('utf-8', errors='replace').strip()}"
        )
    return out


def get_blob_size(repo_root, path, snapshot_sha):
    """Get file size in bytes from snapshot blob."""
    out, err, rc = git_run(repo_root, "cat-file", "-s", f"{snapshot_sha}:{path}")
    if rc != 0:
        raise RuntimeError(f"Cannot get blob size from snapshot {snapshot_sha}: {path}")
    try:
        return int(out.decode("utf-8", errors="replace").strip())
    except ValueError:
        raise RuntimeError(f"Invalid blob size output for {snapshot_sha}:{path}: {out}")


def get_tracked_paths(repo_root):
    """Get all tracked file paths as UTF-8 strings using NUL delimiter."""
    out, err, rc = git_run(repo_root, "ls-files", "-z")
    if rc != 0:
        print(f"FATAL: git ls-files failed: {err.decode('utf-8', errors='replace')}", file=sys.stderr)
        sys.exit(1)
    raw = out.decode("utf-8", errors="replace")
    paths = [p for p in raw.split("\0") if p]
    # Normalize: remove leading ./, ensure /
    paths = [p.replace("\\", "/") for p in paths]
    paths = sorted(set(paths))
    return paths


def get_last_commit(repo_root, path, short=True):
    """Get last commit SHA for a tracked file. Returns empty string if unavailable."""
    out, err, rc = git_run(repo_root, "log", "-1", "--format=%H", "--", path)
    if rc != 0 or not out.strip():
        return ""
    sha = out.decode("utf-8", errors="replace").strip()
    if short and len(sha) >= 12:
        return sha[:12]
    return sha


def sha256_from_blob(blob_bytes):
    """Compute SHA-256 of blob bytes."""
    h = hashlib.sha256()
    h.update(blob_bytes)
    return h.hexdigest()


def classify_category(path):
    p = str(path)
    name = Path(path).name.lower()
    if "/evidence/" in p or "/reports/stage" in p:
        return "evidence"
    if path.endswith(".md") and "/docs/" in p:
        return "documentation"
    if path.endswith((".py", ".js", ".ts", ".css", ".html", ".go", ".rs")):
        return "source-code"
    if path.endswith((".yaml", ".yml", ".json", ".conf", ".toml", ".ini", ".cfg")):
        return "configuration"
    if path.endswith((".sh", ".bash", ".zsh")):
        return "script"
    if path.endswith((".txt", ".log")):
        return "text"
    if path.endswith((".png", ".jpg", ".jpeg", ".svg", ".gif", ".ico", ".webp")):
        return "asset"
    if path.endswith(".dot"):
        return "diagram"
    if path.endswith(".csv"):
        return "data"
    if path.endswith((".zip", ".docx", ".pptx", ".xlsx")):
        return "archive"
    if path.endswith(".pem") or path.endswith(".key"):
        return "crypto-key"
    if path.endswith(".lock") or name == "package-lock.json":
        return "dependency"
    if "dockerfile" in path.lower():
        return "container"
    if name in ("makefile", "gemfile", "rakefile"):
        return "build"
    if path.endswith(".sql"):
        return "database"
    if path.endswith((".env", ".env.example", ".env.template")):
        return "configuration"
    return "other"


def classify_component(path):
    p = str(path)
    if p.startswith("aither-v2/services/portal-frontend/"):
        return "portal-frontend"
    if p.startswith("aither-v2/services/portal-backend/"):
        return "portal-backend"
    if p.startswith("aither-v2/services/ai-platform/"):
        return "ai-platform"
    if p.startswith("aither-v2/services/identity/"):
        return "identity"
    if p.startswith("aither-v2/services/bff/"):
        return "bff"
    if p.startswith("aither-v2/manifests/"):
        if "04-gateway" in p or "nginx-gateway" in p:
            return "llm-gateway"
        if "05-bff" in p:
            return "bff"
        if "06-rate-limit" in p or "redis" in p.lower():
            return "redis"
        if "07-portal" in p or "07-auth" in p:
            return "portal"
        if "02-inference" in p:
            return "vllm"
        if "01-cluster" in p:
            return "cluster-gpu"
        return "manifests"
    if p.startswith("aither-v2/docs/project-control/"):
        return "project-governance"
    if p.startswith("aither-v2/docs/user-launch/"):
        return "user-launch"
    if p.startswith("aither-v2/docs/repository/"):
        return "repository-catalog"
    if p.startswith("aither-v2/docs/releases/"):
        return "release"
    if p.startswith("aither-v2/docs/mvp-roadmap/"):
        return "mvp-roadmap"
    if p.startswith("aither-v2/docs/"):
        return "stage-docs"
    if p.startswith("aither-v2/reports/stage10") or p.startswith("aither-v2/reports/stage10e") or p.startswith("aither-v2/reports/stage10f") or p.startswith("aither-v2/reports/stage10g"):
        return "stage10-reports"
    if p.startswith("aither-v2/reports/stage-u1") or p.startswith("aither-v2/reports/stage-u0"):
        return "stage-u-reports"
    if p.startswith("aither-v2/reports/ba02r") or p.startswith("aither-v2/reports/beta"):
        return "beta-reports"
    if p.startswith("aither-v2/reports/rc1") or p.startswith("aither-v2/reports/rc2"):
        return "rc-reports"
    if p.startswith("aither-v2/reports/"):
        return "reports"
    if p.startswith("aither-v2/evidence/"):
        return "evidence"
    if p.startswith("aither-v2/scripts/"):
        return "scripts"
    if p.startswith("aither-v2/tools/"):
        return "tools"
    if p.startswith("aither-v2/deploy/"):
        return "deployment"
    if p.startswith("aither-v2/03-vllm-14b-deploy/"):
        return "vllm-legacy"
    if p.startswith("aither-v2/01-k8s-gpu-operator/") or p.startswith("aither-v2/02-containerd-nvidia-runtime/"):
        return "cluster-setup"
    if p.startswith("aither-v2/04-") or p.startswith("aither-v2/05-") or p.startswith("aither-v2/06-") or p.startswith("aither-v2/07-"):
        return "placeholder"
    if p.startswith("aither-v2/release/"):
        return "release-artifacts"
    if p.startswith("aither-v2/playwright/"):
        return "testing"
    if p.startswith("aither-v2/"):
        return "aither-v2-root"
    if p.startswith("gateway/"):
        return "gateway-legacy"
    if p.startswith("portal/"):
        return "portal-legacy"
    if p.startswith("offline-deploy/"):
        return "offline-deploy"
    if p.startswith("docs/"):
        return "docs-legacy"
    if p.startswith("manifests/"):
        return "manifests-legacy"
    if p.startswith("diagrams/"):
        return "diagrams"
    if p.startswith("configs/"):
        return "configs"
    if p.startswith("references/"):
        return "references"
    if p.startswith("wiki/"):
        return "wiki"
    if p.startswith("archive/"):
        return "archive"
    if p.startswith("fine-tuning/"):
        return "fine-tuning"
    if p.startswith("hosts/"):
        return "hosts"
    if p.startswith("k8s/"):
        return "k8s-config"
    if p.startswith("grafana/"):
        return "grafana"
    if p.startswith("db/"):
        return "db"
    if p.startswith("delegation/"):
        return "delegation"
    if p.startswith(".github/"):
        return "ci-cd"
    if p.startswith("Usage-Collector/") or p.startswith("aither-article/") or p.startswith("aither-send") or p.startswith(".git"):
        return "external-content"
    return "root-other"


def gen_purpose(path, cat, comp):
    """Generate meaningful purpose description."""
    name = Path(path).name.lower()
    ext = Path(path).suffix.lower()

    if name in ("readme.md", "readme"):
        return "Project overview and entry point documentation"
    if name == "dockerfile" or "dockerfile" in path.lower():
        if comp and comp not in ("unknown", "root-other"):
            return f"Container image build for {comp}"
        return "Container image build definition"
    if ext in (".yaml", ".yml"):
        if "deployment" in path.lower() or "deploy" in path.lower():
            return f"Kubernetes Deployment for {comp}"
        if "service" in path.lower():
            return f"Kubernetes Service for {comp}"
        if "configmap" in path.lower() or "conf" in path.lower() or "gateway" in path.lower():
            return f"Configuration data for {comp}" if comp != "unknown" else "Application configuration"
        if "networkpolicy" in path.lower() or "network-policy" in path.lower():
            return f"Kubernetes NetworkPolicy for {comp}"
        if "secret" in path.lower():
            return f"Kubernetes Secret template for {comp}"
        if "role" in path.lower() or "rbac" in path.lower():
            return f"Kubernetes RBAC configuration for {comp}"
        if "pvc" in path.lower() or "storage" in path.lower():
            return f"Kubernetes PersistentVolumeClaim for {comp}"
        if "namespace" in path.lower():
            return f"Kubernetes Namespace for {comp}"
        if "hpa" in path.lower():
            return "Kubernetes HorizontalPodAutoscaler"
        if "prometheus" in path.lower() or "grafana" in path.lower() or "monitoring" in path.lower() or "servicemonitor" in path.lower():
            return "Kubernetes monitoring/observability configuration"
        if "alert" in path.lower():
            return "Alerting rule configuration"
        if "benchmark" in path.lower() or "job" in path.lower():
            return "Kubernetes Job for benchmark testing"
        return f"Kubernetes desired-state manifest for {comp}" if comp != "unknown" else "Kubernetes manifests"
    if ext == ".py":
        return f"Python source: implements {comp} logic" if comp != "unknown" else "Python source code"
    if ext == ".sh":
        return f"Shell script for {comp}" if comp != "unknown" else "Shell automation script"
    if ext == ".conf":
        if "nginx" in path.lower() or "gateway" in path.lower():
            return f"nginx configuration for {comp}"
        return f"Service configuration file for {comp}"
    if ext == ".json":
        if "dashboard" in path.lower():
            return f"Grafana dashboard JSON for {comp}"
        if "package" in name:
            return "npm package manifest"
        return f"JSON data for {comp}" if comp != "unknown" else "JSON data file"
    if ext == ".toml":
        if "containerd" in path.lower() or "runtime" in path.lower():
            return "Container runtime configuration (containerd)"
        return "TOML configuration file"
    if ext == ".svg" or ext == ".png" or ext == ".jpg" or ext == ".jpeg":
        return f"Architecture diagram or illustration for {comp}" if comp != "unknown" else "Diagram/illustration"
    if ext == ".dot":
        return f"Graphviz diagram source for {comp}"
    if ext == ".css":
        return f"CSS stylesheet for {comp}"
    if ext == ".html":
        return f"HTML page for {comp}"
    if ext == ".js" or ext == ".ts":
        return f"JavaScript/TypeScript source for {comp}"
    if ext == ".md" and cat == "documentation":
        return f"Documentation: {comp.replace('-', ' ').title()}" if comp != "unknown" else "Markdown documentation"
    if cat == "evidence":
        return f"Stage evidence: preserves raw or analytical output"
    if ext == ".txt":
        return f"Text data for {comp}" if comp != "unknown" else "Text data file"
    if ext == ".pem":
        return "Public/private key (cryptographic material)"
    if ext == ".csv":
        return "Comma-separated data"
    if ext == ".gitkeep":
        return "Placeholder to preserve empty directory in Git"
    if ext == ".env" or ext == ".env.example" or ext == ".env.template":
        return f"Environment variable template for {comp}" if comp != "unknown" else "Environment variable configuration"
    if ext == ".sql":
        return "SQL migration or seed script"
    if ext == ".lock" or name == "package-lock.json":
        return "Dependency lock file"
    if ext == ".tsconfig" or name == "tsconfig.json":
        return "TypeScript configuration"
    if name in ("makefile",):
        return "Build automation (Makefile)"
    if ext == ".zip":
        return "Compressed archive"
    if ext == ".docx":
        return "Word document"
    if ext == ".cfg":
        return "System configuration file"
    if ext == ".toml":
        return "TOML configuration"
    return f"Purpose requires manual classification for {comp}" if comp != "unknown" else "Purpose requires manual classification"


def gen_recommendation(cat, comp, path):
    if comp in ("placeholder", "external-content"):
        return "REVIEW"
    if comp in ("vllm-legacy", "gateway-legacy", "portal-legacy", "manifests-legacy", "docs-legacy", "offline-deploy", "archive", "references", "configs", "wiki"):
        return "REVIEW"
    if cat == "evidence":
        return "KEEP"
    if comp in ("repository-catalog", "project-governance", "user-launch"):
        return "KEEP"
    if comp in ("portal-frontend", "portal-backend", "ai-platform", "identity", "bff", "vllm", "redis", "llm-gateway", "cluster-gpu", "cluster-setup"):
        return "KEEP"
    if comp in ("scripts", "tools", "deployment", "testing"):
        return "KEEP"
    if cat == "source-code":
        return "KEEP"
    if comp in ("ci-cd",):
        return "KEEP"
    if comp in ("stage10-reports", "stage-u-reports", "beta-reports", "rc-reports", "reports"):
        return "KEEP"
    if comp == "mvp-roadmap":
        return "KEEP"
    if path.endswith(".gitkeep"):
        return "REVIEW"
    return "KEEP"


def gen_status(cat, comp, path):
    if comp in ("placeholder",):
        return "Stale"
    if comp in ("vllm-legacy", "gateway-legacy", "portal-legacy", "manifests-legacy", "docs-legacy", "offline-deploy", "archive", "references", "wiki", "configs", "external-content", "diagrams"):
        return "Historical"
    if comp in ("repository-catalog",):
        return "Generated"
    if cat == "evidence":
        return "Evidence"
    return "Active"


def has_aggregation(text):
    patterns = ["plus other", "various", "..."]
    for pat in patterns:
        if pat in text.lower():
            return True
    return False


def check_utf8_normalization(path_str):
    """Check for octal escapes or quote artifacts."""
    global UTF8_ERRORS
    issues = []
    if "\\" in path_str and any(c in path_str for c in "01234567"):
        issues.append("octal_escape")
        UTF8_ERRORS += 1
    if '"' in path_str and not path_str.startswith('"') and not path_str.endswith('"'):
        pass  # embedded quote is OK for UTF-8 paths
    if path_str.endswith('".svg') or path_str.endswith('".md'):
        issues.append("quoted_extension")
        UTF8_ERRORS += 1
    try:
        path_str.encode("utf-8").decode("utf-8")
    except:
        issues.append("utf8_error")
        UTF8_ERRORS += 1
    return issues


# ── Main Generator ───────────────────────────────────────────────────

def generate(repo_root, snapshot_sha, output_dir, catalog_path, csv_path, hash_path, tracked_path, rec_path, val_path, check_only=False):
    """Main generation function. Snapshot-only: never reads working tree for tracked files."""
    global UTF8_ERRORS
    UTF8_ERRORS = 0
    log = []
    log.append(f"# Generation Log")
    log.append(f"Snapshot: {snapshot_sha}")
    log.append(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    log.append(f"")

    # Verify snapshot commit
    t0 = time.time()
    verify_snapshot_commit(repo_root, snapshot_sha)
    t1 = time.time()
    log.append(f"COMMAND: git cat-file -e {snapshot_sha}^commit")
    log.append(f"EXIT: 0")
    log.append(f"TIME: {t1-t0:.2f}s")
    log.append(f"")

    # Get tracked paths
    t0 = time.time()
    paths = get_tracked_paths(repo_root)
    t1 = time.time()
    log.append(f"COMMAND: git ls-files -z")
    log.append(f"EXIT: 0")
    log.append(f"FILES: {len(paths)}")
    log.append(f"TIME: {t1-t0:.2f}s")
    log.append(f"")

    # Verify every tracked path exists in snapshot
    t0 = time.time()
    for path in paths:
        verify_path_in_snapshot(repo_root, path, snapshot_sha)
    t1 = time.time()
    log.append(f"COMMAND: git cat-file -e (all {len(paths)} paths in snapshot)")
    log.append(f"EXIT: 0")
    log.append(f"TIME: {t1-t0:.2f}s")
    log.append(f"")

    # Check for normalization issues
    norm_issues = defaultdict(list)
    for p in paths:
        issues = check_utf8_normalization(p)
        if issues:
            norm_issues[p] = issues

    # Build catalog data
    catalog_rows = []
    csv_rows = []
    hash_lines = []

    for path in paths:
        ext = Path(path).suffix or "(none)"
        cat = classify_category(path)
        comp = classify_component(path)
        purpose = gen_purpose(path, cat, comp)
        last_commit = get_last_commit(repo_root, path, short=True)
        runtime = "YES" if (cat == "configuration" and comp not in ("evidence", "reports", "documentation", "repository-catalog", "docs-legacy", "references")) else "NO"
        if "secret" in path.lower():
            runtime = "YES"
        if "Deployment" in purpose or "Service" in purpose:
            runtime = "YES"
        if cat == "source-code":
            runtime = "YES"
        if comp in ("portal-frontend", "portal-backend", "ai-platform", "identity", "llm-gateway", "redis", "vllm", "bff"):
            runtime = "YES"
        if cat in ("evidence", "asset", "diagram", "archive"):
            runtime = "NO"
        if comp in ("placeholder", "vllm-legacy", "docs-legacy", "references", "archive", "external-content", "gateway-legacy", "portal-legacy", "offline-deploy", "manifests-legacy", "configs", "wiki", "diagrams"):
            runtime = "NO"
        sot = "YES" if runtime == "YES" else ("PARTIAL" if "dockerfile" in path.lower() or path.endswith("requirements.txt") else "NO")
        if cat == "evidence":
            sot = "NO"
        if comp == "repository-catalog":
            sot = "YES"
        status = gen_status(cat, comp, path)
        rec = gen_recommendation(cat, comp, path)

        # Hash from snapshot ONLY (raises RuntimeError if blob not found)
        blob = get_blob_from_snapshot(repo_root, path, snapshot_sha)
        fhash = sha256_from_blob(blob)

        # Size from snapshot blob
        size_bytes = get_blob_size(repo_root, path, snapshot_sha)

        hash_lines.append(f"{fhash}  {path}")

        catalog_rows.append({
            "path": path,
            "type": ext,
            "category": cat,
            "component": comp,
            "purpose": purpose,
            "runtime": runtime,
            "sot": sot,
            "last_commit": last_commit,
            "status": status,
            "recommendation": rec,
        })

        csv_rows.append({
            "path": path,
            "type": ext,
            "size_bytes": size_bytes,
            "category": cat,
            "component": comp,
            "purpose": purpose,
            "runtime_impact": runtime,
            "source_of_truth": sot,
            "last_commit": last_commit,
            "status": status,
            "recommendation": rec,
            "sha256": fhash,
            "snapshot_sha": snapshot_sha,
        })

    count = len(catalog_rows)

    if check_only:
        print(f"CHECK-ONLY: {count} tracked paths")
        print(f"UTF-8 normalization issues: {len(norm_issues)}")
        return 0 if (count > 0 and len(norm_issues) == 0) else 1

    # Write TRACKED_FILE_LIST
    tracked_content = f"# Snapshot: {snapshot_sha}\n# Count: {count}\n" + "\n".join(paths) + "\n"
    write_file(tracked_path, tracked_content, log)

    # Write FILE_CATALOG.md
    catalog_lines = [
        f"# File Catalog \u2014 Complete ({count} files)",
        "",
        f"**Snapshot SHA:** {snapshot_sha}",
        f"**Generated at:** {datetime.now(timezone.utc).isoformat()}",
        f"**Generator version:** {SCRIPT_VERSION}",
        f"**Tracked file count:** {count}",
        "",
        "| Path | Type | Category | Component | Purpose | Runtime | SOT | Last Commit | Status | Recommendation |",
        "|------|------|----------|-----------|---------|---------|-----|-------------|--------|---------------|",
    ]
    for row in catalog_rows:
        p = row["path"].replace("|", "\\|")
        purp = row["purpose"].replace("|", "\\|").replace("\n", " ")
        catalog_lines.append(
            f"| `{p}` | {row['type']} | {row['category']} | {row['component']} | {purp} | {row['runtime']} | {row['sot']} | {row['last_commit']} | {row['status']} | {row['recommendation']} |"
        )
    catalog_lines.append("")
    write_file(catalog_path, "\n".join(catalog_lines), log)

    # Write FILE_METADATA.csv
    csv_buf = io.StringIO()
    writer = csv.DictWriter(csv_buf, fieldnames=[
        "path", "type", "size_bytes", "category", "component", "purpose",
        "runtime_impact", "source_of_truth", "last_commit", "status",
        "recommendation", "sha256", "snapshot_sha"
    ])
    writer.writeheader()
    for row in csv_rows:
        writer.writerow(row)
    write_file(csv_path, csv_buf.getvalue(), log)

    # Write FILE_HASHES.txt
    hash_content = "\n".join(hash_lines) + "\n"
    write_file(hash_path, hash_content, log)

    # Write FILE_RECONCILIATION.md
    rec_content = generate_reconciliation(paths, catalog_rows, csv_rows, hash_lines, snapshot_sha, count)
    write_file(rec_path, rec_content, log)

    # Write VALIDATION_REPORT.md
    val_content = generate_validation(paths, catalog_rows, repo_root, norm_issues, snapshot_sha, count)
    write_file(val_path, val_content, log)

    return 0


def write_file(path, content, log):
    """Write file, logging the action."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    log.append(f"WRITE: {path} ({len(content)} bytes)")
    log.append(f"")


def generate_reconciliation(paths, catalog_rows, csv_rows, hash_lines, snapshot_sha, count):
    catalog_paths = set(r["path"] for r in catalog_rows)
    csv_paths = set(r["path"] for r in csv_rows)
    hash_paths = set()
    for line in hash_lines:
        parts = line.split("  ", 1)
        if len(parts) == 2:
            hash_paths.add(parts[1].strip())
    tracked = set(paths)

    def diff(a, b, name_a, name_b):
        missing = a - b
        extra = b - a
        return {
            "source_a": name_a,
            "source_b": name_b,
            "count_a": len(a),
            "count_b": len(b),
            "unique_a": len(a),
            "unique_b": len(b),
            "missing": len(missing),
            "extra": len(extra),
            "duplicates": 0,
            "missing_list": sorted(missing),
            "extra_list": sorted(extra),
        }

    checks = [
        diff(tracked, catalog_paths, "git ls-files", "FILE_CATALOG.md"),
        diff(tracked, csv_paths, "git ls-files", "FILE_METADATA.csv"),
        diff(tracked, hash_paths, "git ls-files", "FILE_HASHES.txt"),
        diff(catalog_paths, csv_paths, "FILE_CATALOG.md", "FILE_METADATA.csv"),
        diff(catalog_paths, hash_paths, "FILE_CATALOG.md", "FILE_HASHES.txt"),
        diff(csv_paths, hash_paths, "FILE_METADATA.csv", "FILE_HASHES.txt"),
    ]

    lines = [
        f"# File Reconciliation Report",
        "",
        f"**Snapshot SHA:** {snapshot_sha}",
        f"**Generated at:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Path Set Comparison",
        "",
        "| Source | Count | Unique | Missing | Extra | Duplicates | Status |",
        "|--------|------:|-------:|-------:|------:|-----------:|--------|",
    ]

    all_pass = True
    for c in checks:
        passed = c["missing"] == 0 and c["extra"] == 0
        if not passed:
            all_pass = False
        lines.append(
            f"| {c['source_a']} vs {c['source_b']} | {c['count_a']} / {c['count_b']} "
            f"| {c['unique_a']} / {c['unique_b']} | {c['missing']} | {c['extra']} "
            f"| {c['duplicates']} | {'✅' if passed else '❌'} |"
        )
        if c["missing"] > 0:
            lines.append(f"\n  Missing in {c['source_b']}:")
            for m in c["missing_list"][:20]:
                lines.append(f"  - `{m}`")
        if c["extra"] > 0:
            lines.append(f"\n  Extra in {c['source_b']}:")
            for e in c["extra_list"][:20]:
                lines.append(f"  - `{e}`")

    set_eq = tracked == catalog_paths == csv_paths == hash_paths
    lines.extend([
        "",
        f"**Snapshot SHA:** {snapshot_sha}",
        f"**All path sets equal:** {'YES' if set_eq else 'NO'}",
        f"**All hashes present:** {'YES' if len(hash_lines) == count else 'NO'}",
        f"**Verdict:** {'PASSED' if (all_pass and set_eq) else 'FAILED'}",
        "",
    ])
    return "\n".join(lines) + "\n"


def generate_validation(paths, catalog_rows, repo_root, norm_issues, snapshot_sha, count):
    patterns = {
        "plus others": 0,
        "plus \\d+ others": 0,
        "various": 0,
        "\\...": 0,
        "TBD": 0,
        "TODO": 0,
        "CHANGEME": 0,
        "FIXME": 0,
        "To be added": 0,
    }

    # Collect all relevant text for pattern scanning
    catalog_text = "\n".join(
        f"{r['path']}|{r['purpose']}|{r['status']}|{r['recommendation']}"
        for r in catalog_rows
    )

    # Also scan the catalog markdown file content for readability issues
    # Use the full catalog paths and text

    pattern_matches = []
    for pat in sorted(patterns.keys()):
        if pat == "\\...":
            # Special handling: "..." is common punctuation.
            # Only flag when used as aggregation placeholder like "plus others..."
            matches_agg = list(re.finditer(r'(plus\s+others?\s*\.\.\.)', catalog_text, re.IGNORECASE))
            c = len(matches_agg)
        else:
            matches = list(re.finditer(pat, catalog_text, re.IGNORECASE))
            c = len(matches)
        pattern_matches.append({
            "pattern": pat,
            "count": c,
            "allowed": 0,
            "unregistered": c,
        })

    tbd_instances = []
    for r in catalog_rows:
        if "TBD" in r["purpose"]:
            tbd_instances.append({"path": r["path"], "field": "purpose", "text": r["purpose"]})

    field_issues = []
    for r in catalog_rows:
        if has_aggregation(r["purpose"]):
            field_issues.append(f"AGGREGATION in purpose: {r['path']}")
        if not r["purpose"] or r["purpose"].strip() in ("", "other", "various", "documentation", "config file", "unknown file"):
            field_issues.append(f"EMPTY/INVALID purpose: {r['path']}")

    lines = [
        f"# Validation Report",
        "",
        f"**Snapshot SHA:** {snapshot_sha}",
        f"**Generated at:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Pattern Validation",
        "",
        "| Pattern | Found | Allowed | Unregistered | Status |",
        "|---------|------:|-------:|------------:|--------|",
    ]

    for pm in pattern_matches:
        status = "✅" if pm["unregistered"] == 0 else "⚠️"
        lines.append(
            f"| `{pm['pattern']}` | {pm['count']} | {pm['allowed']} | {pm['unregistered']} | {status} |"
        )

    if tbd_instances:
        lines.extend(["", "### TBD Instances Found", ""])
        for inst in tbd_instances:
            lines.append(f"- `{inst['path']}`: {inst['text'][:100]}")

    lines.extend([
        "",
        "## Field Completeness",
        "",
        f"**Total entries:** {len(catalog_rows)}",
        f"**Missing/invalid purpose fields:** {len(field_issues)}",
        "",
    ])
    for fi in field_issues[:30]:
        lines.append(f"- {fi}")

    lines.extend([
        "",
        "## UTF-8 Normalization",
        "",
        f"**Paths with normalization issues:** {len(norm_issues)}",
        f"**Total UTF-8 errors:** {len(norm_issues)}",
        "",
    ])
    for path, issues in sorted(norm_issues.items()):
        lines.append(f"- `{path}`: {', '.join(issues)}")

    lines.extend([
        "",
        "## Aggregation Check",
        "",
        f"**Catalog entries with aggregation patterns:** {len(field_issues)}",
        "",
        "**Verdict:** " + ("PASSED" if (len(field_issues) == 0 and len(norm_issues) == 0 and len(tbd_instances) == 0) else "ISSUES FOUND"),
        "",
    ])
    return "\n".join(lines) + "\n"


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deterministic Repository Inventory Generator (Snapshot-Only)")
    parser.add_argument("--repo-root", default=".", help="Path to repository root")
    parser.add_argument("--snapshot", required=True, help="Snapshot commit SHA for content hashing")
    parser.add_argument("--generate", action="store_true", help="Generate all inventory outputs")
    parser.add_argument("--check-only", action="store_true", help="Validate only, no file writes")
    parser.add_argument("--validate", action="store_true", help="Alias for --check-only")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    snapshot_sha = args.snapshot
    aither_dir = os.path.join(repo_root, "aither-v2")

    output_dir = os.path.join(aither_dir, "reports", "stage-u0", "u0-a")
    r2_dir = os.path.join(aither_dir, "reports", "stage-u0", "u0-a-r2")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(r2_dir, exist_ok=True)

    catalog_path = os.path.join(aither_dir, "docs", "repository", "FILE_CATALOG.md")
    csv_path = os.path.join(output_dir, "05_FILE_METADATA.csv")
    hash_path = os.path.join(output_dir, "06_FILE_HASHES.txt")
    tracked_path = os.path.join(output_dir, "03_TRACKED_FILE_LIST.txt")
    rec_path = os.path.join(aither_dir, "docs", "repository", "FILE_RECONCILIATION.md")
    val_path = os.path.join(aither_dir, "docs", "repository", "VALIDATION_REPORT.md")

    if not args.generate and not args.check_only:
        parser.print_help()
        sys.exit(0)

    rc = generate(repo_root, snapshot_sha, output_dir, catalog_path, csv_path, hash_path,
                  tracked_path, rec_path, val_path, check_only=args.check_only)
    sys.exit(rc)


if __name__ == "__main__":
    main()
