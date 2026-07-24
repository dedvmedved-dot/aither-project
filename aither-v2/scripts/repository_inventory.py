#!/usr/bin/env python3
"""
Repository Inventory Script for Stage U0.A
Read-only, deterministic, no network changes, no deletions.
"""
import os
import sys
import hashlib
import csv
import io
import json
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(os.environ.get("AITHER_ROOT", "/root/aither-v2"))
GIT_DIR = BASE_DIR  # /root/aither-v2 is the git root

def run_git(*args):
    """Run git command and return output."""
    import subprocess
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=GIT_DIR, timeout=30
    )
    return result.stdout, result.stderr, result.returncode

def sha256_file(path):
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def classify_category(path):
    """Classify a file by its path and purpose."""
    p = str(path)
    name = path.name.lower()
    
    # Evidence
    if "/evidence/" in p or "/reports/stage" in p:
        return "evidence"
    
    # Documentation
    if "/docs/" in p and path.suffix == ".md":
        return "documentation"
    
    # Source code
    if path.suffix in (".py", ".js", ".ts", ".css", ".html"):
        return "source-code"
    
    # Configuration
    if path.suffix in (".yaml", ".yml", ".json", ".conf", ".toml", ".ini"):
        return "configuration"
    
    # Scripts
    if path.suffix in (".sh", ".bash", ".ps1"):
        return "script"
    
    # Container
    if name == "dockerfile":
        return "container"
    if name == "docker-compose.yaml" or name == "docker-compose.yml":
        return "container"
    
    # Dot files
    if name.startswith(".env"):
        return "configuration"
    if name.startswith("dockerfile"):
        return "container"
    
    # Makefile
    if name == "makefile":
        return "build"
    
    # Lock files
    if path.suffix in (".lock",) or name == "requirements.txt":
        return "dependency"
    
    # Images / assets
    if path.suffix in (".png", ".jpg", ".svg", ".gif", ".ico"):
        return "asset"
    
    # Diagrams
    if path.suffix == ".dot":
        return "diagram"
    
    # Text
    if path.suffix == ".txt":
        return "documentation"
    
    # Markdown
    if path.suffix == ".md":
        return "documentation"
    
    return "other"

def classify_component(path):
    """Determine which component a file belongs to."""
    p = str(path)
    
    # Services
    if "/services/portal-frontend/" in p:
        return "portal-frontend"
    if "/services/portal-backend/" in p:
        return "portal-backend"
    if "/services/ai-platform/" in p:
        return "ai-platform"
    if "/services/identity/" in p:
        return "identity"
    
    # Manifests
    if "/manifests/mvp-roadmap/04-gateway/" in p:
        return "llm-gateway"
    if "/manifests/mvp-roadmap/05-bff/" in p:
        return "bff"
    if "/manifests/mvp-roadmap/06-rate-limiting/" in p:
        return "redis"
    if "/manifests/mvp-roadmap/07-portal/" in p:
        return "portal"
    if "/manifests/mvp-roadmap/02-inference-acceptance/" in p:
        return "vllm"
    if "/manifests/mvp-roadmap/01-cluster-gpu/" in p:
        return "cluster-gpu"
    
    # Docs
    if "/docs/user-launch/" in p:
        return "user-launch"
    if "/docs/project-control/" in p:
        return "project-governance"
    if "/docs/mvp-roadmap/" in p:
        return "mvp-roadmap"
    if "/docs/releases/" in p:
        return "release"
    if "/docs/rc2r-corrections" in p:
        return "rc2r-corrections"
    if "/docs/stage17/" in p:
        return "observability"
    
    # Stage reports
    if "/reports/stage10" in p or "/reports/stage10e/" in p or "/reports/stage10f/" in p:
        return "stage10"
    if "/reports/stage-u1/" in p:
        return "stage-u1"
    
    # Scripts
    if "/scripts/" in p and "/scripts/rc2r/" not in p:
        return "scripts"
    if "/scripts/rc2r/" in p:
        return "rc2r-local"
    
    # Legacy
    if "/03-vllm-14b-deploy/" in p:
        return "vllm-legacy"
    if "/02-containerd-nvidia-runtime/" in p:
        return "container-runtime"
    if "/01-k8s-gpu-operator/" in p:
        return "cluster-gpu"
    if "/04-tensor-parallelism/" in p:
        return "tensor-parallelism"
    if "/05-gateway-redis/" in p:
        return "gateway-redis"
    if "/06-portal-spa-bff-sse/" in p:
        return "portal-legacy"
    if "/07-oauth/" in p:
        return "oauth-legacy"
    
    # Deploy
    if "/deploy/" in p:
        return "deployment"
    
    # Tools
    if "/tools/" in p:
        return "tools"
    
    # Root level
    if "/evidencer" in p or p.endswith("audit-report.md"):
        return "audit"
    if "/playwright/" in p:
        return "testing"
    
    return "unknown"

def determine_stage(path):
    """Determine which Stage a file belongs to."""
    p = str(path)
    stage_map = {
        "01": "Stage 01", "02": "Stage 02", "03": "Stage 03",
        "04": "Stage 04", "05": "Stage 05", "06": "Stage 06",
        "07": "Stage 07", "08": "Stage 08", "09": "Stage 09",
        "10": "Stage 10-10G", "10e": "Stage 10E", "10f": "Stage 10F",
        "10g": "Stage 10G",
        "u1": "Stage U1.0", "u0": "Stage U0.A",
        "15": "Stage 15", "16": "Stage 16", "17": "Stage 17",
        "18": "Stage 18",
    }
    for key, stage in stage_map.items():
        if f"/stage{key}" in p.lower() or f"-stage{key}" in p.lower():
            return stage
    if "/mvp-roadmap/01-" in p:
        return "Stage 01"
    if "/mvp-roadmap/02-" in p:
        return "Stage 02"
    if "/mvp-roadmap/04-" in p:
        return "Stage 04"
    if "/mvp-roadmap/05-" in p:
        return "Stage 05"
    if "/mvp-roadmap/06-" in p:
        return "Stage 06"
    if "/mvp-roadmap/07-" in p:
        return "Stage 07"
    if "/mvp-roadmap/08-" in p:
        return "Stage 08"
    if "/mvp-roadmap/09-" in p:
        return "Stage 09"
    if "/stage10" in p:
        return "Stage 10-10G"
    if "/stage-u1/" in p or "/user-launch/" in p:
        return "Stage U1.0"
    if "/stage-u0/" in p:
        return "Stage U0.A"
    if "/stage15" in p or "/test-stage15" in p:
        return "Stage 15"
    if "/stage16" in p or "/test-stage16" in p:
        return "Stage 16"
    if "/stage17" in p:
        return "Stage 17"
    if "/stage18" in p:
        return "Stage 18"
    return "pre-MVP"

def main_inventory():
    """Main inventory function."""
    # Get tracked files
    out, err, rc = run_git("ls-files")
    if rc != 0:
        print(f"ERROR: git ls-files failed: {err}", file=sys.stderr)
        sys.exit(1)
    
    tracked_files = [f.strip() for f in out.strip().split("\n") if f.strip()]
    
    print(f"Total tracked files: {len(tracked_files)}")
    
    # Get last commit info for each file
    metadata = []
    file_hashes = []
    duplicate_hashes = {}
    duplicate_names = {}
    
    for tf in tracked_files:
        full_path = BASE_DIR / tf
        if not full_path.exists():
            # File exists in git but not in working tree (unlikely)
            print(f"WARNING: {tf} in git but not on disk", file=sys.stderr)
            continue
        
        # SHA-256
        fhash = sha256_file(full_path)
        file_hashes.append(f"{fhash}  {tf}")
        
        # Group by hash for duplicate detection
        if fhash not in duplicate_hashes:
            duplicate_hashes[fhash] = []
        duplicate_hashes[fhash].append(tf)
        
        # Group by name for duplicate name detection
        name_lower = os.path.basename(tf).lower()
        if name_lower not in duplicate_names:
            duplicate_names[name_lower] = []
        duplicate_names[name_lower].append(tf)
        
        # File size
        size = full_path.stat().st_size
        
        # Category and component
        category = classify_category(full_path)
        component = classify_component(tf)
        stage = determine_stage(tf)
        
        metadata.append({
            "path": tf,
            "type": full_path.suffix or "none",
            "size_bytes": size,
            "category": category,
            "component": component,
            "stage": stage,
        })
    
    return tracked_files, metadata, file_hashes, duplicate_hashes, duplicate_names

if __name__ == "__main__":
    tf, md, fh, dh, dn = main_inventory()
    print(f"Files with metadata: {len(md)}")
    print(f"Unique SHA-256 hashes: {len(dh)}")
    
    # Exact duplicates (same hash, different paths)
    exact_dups = {h: paths for h, paths in dh.items() if len(paths) > 1}
    print(f"Exact duplicates (same content, different paths): {len(exact_dups)}")
    for h, paths in sorted(exact_dups.items()):
        print(f"  {h[:16]}... {'; '.join(paths)}")
    
    # Same-name files
    same_name = {n: paths for n, paths in dn.items() if len(paths) > 1}
    print(f"\nSame-name files (different locations): {len(same_name)}")
    for n, paths in sorted(same_name.items()):
        print(f"  {n}: {'; '.join(paths)}")
    
    # Categories
    from collections import Counter
    cats = Counter(m["category"] for m in md)
    print(f"\nCategories:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    
    # Components
    comps = Counter(m["component"] for m in md)
    print(f"\nComponents:")
    for comp, count in sorted(comps.items(), key=lambda x: -x[1]):
        print(f"  {comp}: {count}")
