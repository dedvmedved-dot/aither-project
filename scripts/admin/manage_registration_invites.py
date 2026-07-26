#!/usr/bin/env python3
"""
Aither Admin CLI — Manage Registration Invite Codes (R7-R4)

Usage:
  python3 manage_registration_invites.py create [--expires-in DAYS] [--model-scope SCOPE] [--description TEXT]
  python3 manage_registration_invites.py list
  python3 manage_registration_invites.py inspect <invite_id>
  python3 manage_registration_invites.py revoke <invite_id>

Requires: REDIS_URL env var or --redis-url
"""
import os
import sys
import json
import uuid
import hashlib
import secrets
import argparse
from datetime import datetime, timezone, timedelta

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://aither-redis-rate-limit.aither-inference.svc:6379/0")
INVITE_NS = "aither-auth:invite"

def _invite_key(invite_hash: str) -> str:
    return f"{INVITE_NS}:{invite_hash}"

def cmd_create(args):
    r = redis.from_url(args.redis_url, decode_responses=True)
    try:
        r.ping()
    except Exception as e:
        print(f"ERROR: Cannot connect to Redis at {args.redis_url}: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate cryptographically strong invite code
    raw_code = secrets.token_urlsafe(24)
    invite_hash = hashlib.sha256(raw_code.encode()).hexdigest()
    invite_id = uuid.uuid4().hex[:12]

    expires_days = args.expires_in or 30
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()

    model_scopes = args.model_scope or ["model:14b:chat", "model:32b:chat-adapter"]
    if isinstance(model_scopes, str):
        model_scopes = [s.strip() for s in model_scopes.split(",")]

    invite_data = {
        "invite_id": invite_id,
        "invite_hash": invite_hash,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at,
        "used_at": "",
        "revoked_at": "",
        "created_by": "cli",
        "model_scopes": model_scopes,
        "description": args.description or "",
        "use_limit": 1,
        "use_count": 0,
        "registered_user_id": "",
    }

    r.set(_invite_key(invite_hash), json.dumps(invite_data))

    print(f"✅ Invite created:")
    print(f"   Invite ID:  {invite_id}")
    print(f"   Invite Code: {raw_code}")
    print(f"   Expires:    {expires_at}")
    print(f"   Scopes:     {model_scopes}")
    print(f"")
    print(f"⚠️  SAVE THE INVITE CODE NOW — it will NOT be shown again.")

def cmd_list(args):
    r = redis.from_url(args.redis_url, decode_responses=True)
    try:
        r.ping()
    except Exception as e:
        print(f"ERROR: Cannot connect to Redis: {e}", file=sys.stderr)
        sys.exit(1)

    # Scan for invite keys
    invites = []
    for key in r.scan_iter(f"{INVITE_NS}:*"):
        data = r.get(key)
        if data:
            try:
                inv = json.loads(data)
                invites.append(inv)
            except (json.JSONDecodeError, TypeError):
                pass

    if not invites:
        print("No invites found.")
        return

    invites.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    print(f"{'ID':<14} {'Status':<10} {'Used':<6} {'Scopes':<40} {'Created':<20} {'Description'}")
    print("-" * 110)
    for inv in invites:
        scopes = ",".join(inv.get("model_scopes", []))[:38]
        created = (inv.get("created_at", "") or "")[:19]
        desc = (inv.get("description", "") or "")[:30]
        print(f"{inv.get('invite_id','?'):<14} {inv.get('status','?'):<10} {inv.get('use_count',0)}/{inv.get('use_limit',1):<4} {scopes:<40} {created:<20} {desc}")

def cmd_inspect(args):
    r = redis.from_url(args.redis_url, decode_responses=True)
    try:
        r.ping()
    except Exception as e:
        print(f"ERROR: Cannot connect to Redis: {e}", file=sys.stderr)
        sys.exit(1)

    # Find invite by ID
    for key in r.scan_iter(f"{INVITE_NS}:*"):
        data = r.get(key)
        if data:
            try:
                inv = json.loads(data)
                if inv.get("invite_id") == args.invite_id:
                    print(json.dumps(inv, indent=2))
                    return
            except (json.JSONDecodeError, TypeError):
                pass

    print(f"Invite {args.invite_id} not found.")

def cmd_revoke(args):
    r = redis.from_url(args.redis_url, decode_responses=True)
    try:
        r.ping()
    except Exception as e:
        print(f"ERROR: Cannot connect to Redis: {e}", file=sys.stderr)
        sys.exit(1)

    for key in r.scan_iter(f"{INVITE_NS}:*"):
        data = r.get(key)
        if data:
            try:
                inv = json.loads(data)
                if inv.get("invite_id") == args.invite_id:
                    if inv.get("status") == "used":
                        print(f"Cannot revoke: invite {args.invite_id} was already used.")
                        return
                    if inv.get("status") == "revoked":
                        print(f"Invite {args.invite_id} is already revoked.")
                        return
                    inv["status"] = "revoked"
                    inv["revoked_at"] = datetime.now(timezone.utc).isoformat()
                    r.set(key, json.dumps(inv))
                    print(f"✅ Invite {args.invite_id} revoked.")
                    return
            except (json.JSONDecodeError, TypeError):
                pass

    print(f"Invite {args.invite_id} not found.")

def main():
    parser = argparse.ArgumentParser(description="Aither Registration Invite Manager")
    parser.add_argument("--redis-url", default=REDIS_URL, help=f"Redis URL (default: {REDIS_URL})")
    sub = parser.add_subparsers(dest="command")

    p_create = sub.add_parser("create", help="Create a new invite code")
    p_create.add_argument("--expires-in", type=int, default=30, help="Days until expiry (default: 30)")
    p_create.add_argument("--model-scope", action="append", default=None, help="Model scope (repeatable, default: 14b+32b)")
    p_create.add_argument("--description", default="", help="Description/purpose")

    sub.add_parser("list", help="List all invites")

    p_inspect = sub.add_parser("inspect", help="Show invite details (no plaintext code)")
    p_inspect.add_argument("invite_id", help="Invite ID")

    p_revoke = sub.add_parser("revoke", help="Revoke an unused invite")
    p_revoke.add_argument("invite_id", help="Invite ID")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    {"create": cmd_create, "list": cmd_list, "inspect": cmd_inspect, "revoke": cmd_revoke}[args.command](args)

if __name__ == "__main__":
    main()
