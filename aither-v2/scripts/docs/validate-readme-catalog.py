#!/usr/bin/env python3
"""README-REFRESH-01: Validate that README.md covers all tracked files.

Compares `git ls-files` against file paths extracted from README.md.
Accounts for documented exclusions in readme-catalog-exclusions.txt.
Exits 0 if all tracked files are accounted for (catalogued or excluded).
"""
import os, re, sys, subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
README = REPO_ROOT / "README.md"
EXCLUSIONS = Path(__file__).resolve().parent / "readme-catalog-exclusions.txt"

def get_tracked_files():
    """Return set of all Git-tracked file paths (relative to repo root)."""
    os.chdir(REPO_ROOT)
    result = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR: git ls-files failed", file=sys.stderr)
        sys.exit(1)
    return {f.strip() for f in result.stdout.strip().split("\n") if f.strip()}

def get_readme_paths():
    """Extract file paths referenced in README.md via backtick code spans or markdown links."""
    if not README.exists():
        print("ERROR: README.md not found", file=sys.stderr)
        sys.exit(1)
    paths = set()
    content = README.read_text()
    # Find paths in backtick code spans: `path/to/file`
    for m in re.finditer(r'`([^`\n]+)`', content):
        path = m.group(1)
        # Match paths that contain /, or look like filenames (.gitignore, .gitkeep, etc.)
        is_path_like = '/' in path or ('.' in path and not path.startswith('http') and not path.startswith(' '))
        if is_path_like and not path.startswith('http') and not path.startswith(' '):
            path = path.strip().strip("'\"")
            # Skip if it looks like a command or description (starts with typical command words)
            if any(path.startswith(w) for w in ('ssh', 'sshpass', 'curl', 'python', 'pytest', 'gitleaks', 'grep', 'find', 'tree', 'git', 'kubectl', 'docker', 'sudo', 'systemctl', 'chown', 'nslookup', 'diff')):
                continue
            # Skip IP:port patterns
            if re.match(r'^\d+\.\d+\.\d+\.\d+(:\d+)?$', path):
                continue
            # Skip K8s service names (contain .svc)
            if '.svc' in path:
                continue
            # Skip if it's just a path fragment in code
            if len(path.split()) > 1:
                continue
            paths.add(path)
    # Also find paths in markdown links: [text](path)
    for m in re.finditer(r'\]\(([^)]+)\)', content):
        path = m.group(1)
        if not path.startswith('http') and not path.startswith('#'):
            path = path.split('#')[0]  # Remove anchor
            paths.add(path)
    return paths

def get_exclusions():
    """Read exclusion file, return lists of excluded paths and patterns."""
    if not EXCLUSIONS.exists():
        return set(), [], []
    excluded = set()
    patterns = []  # (glob patterns for fnmatch)
    dir_prefixes = []  # directory prefixes ending with /
    for line in EXCLUSIONS.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.endswith('/*'):
            dir_prefixes.append(line[:-2])  # Strip /*
        elif '*' in line or '?' in line:
            patterns.append(line)
        else:
            excluded.add(line)
    return excluded, patterns, dir_prefixes

def is_excluded(path, excluded_set, patterns, dir_prefixes):
    """Check if path matches any exclusion rule."""
    import fnmatch
    if path in excluded_set:
        return True
    for pat in patterns:
        if fnmatch.fnmatch(path, pat):
            return True
    for prefix in dir_prefixes:
        if path.startswith(prefix + '/'):
            return True
    return False

def main():
    tracked = get_tracked_files()
    catalogued = get_readme_paths()
    excluded, patterns, dir_prefixes = get_exclusions()

    # Apply exclusions
    tracked_remaining = {f for f in tracked if not is_excluded(f, excluded, patterns, dir_prefixes)}

    # Check catalogued paths exist in repo
    broken_links = set()
    for p in catalogued:
        if p not in tracked:
            # Skip API paths (start with /), template vars {{}}, and other non-file references
            if p.startswith('/'):
                continue
            if '{{' in p or '}}' in p:
                continue
            if p.endswith('/*') or '*' in p:
                continue  # wildcard patterns are exclusions, not paths
            # If it's a directory reference (exists on disk or has tracked children), it's valid
            full_path = REPO_ROOT / p
            if full_path.is_dir():
                continue
            # If any tracked file starts with this prefix, it's a valid directory reference
            if any(t.startswith(p + '/') for t in tracked):
                continue
            # If it's excluded already, it's fine
            if is_excluded(p + '/dummy', excluded, patterns, dir_prefixes) or is_excluded(p, excluded, patterns, dir_prefixes):
                continue
            broken_links.add(p)

    # Check tracked files NOT in catalog
    missing = tracked_remaining - catalogued

    # Print report
    print(f"Tracked files:       {len(tracked)}")
    print(f"Catalogued in README: {len(catalogued)}")
    print(f"Documented exclusions: {len(excluded)}")
    print(f"Missing from catalog:  {len(missing)}")
    print(f"Broken links:          {len(broken_links)}")

    if missing:
        print("\nMISSING FILES (tracked but not in README):")
        for f in sorted(missing):
            print(f"  {f}")

    if broken_links:
        print("\nBROKEN LINKS (in README but not tracked):")
        for f in sorted(broken_links):
            print(f"  {f}")

    if missing or broken_links:
        print("\nRESULT: FAILED")
        sys.exit(1)
    else:
        print("\nRESULT: PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
