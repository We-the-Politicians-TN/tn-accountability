"""Store project secrets in the macOS Keychain instead of a plaintext .env.

    python -m tn_accountability.secrets set DATABASE_URL     # prompts, no echo
    python -m tn_accountability.secrets list                 # names only, never values
    python -m tn_accountability.secrets check                # what resolves, and from where
    python -m tn_accountability.secrets import-env           # migrate an existing .env
    python -m tn_accountability.secrets delete LEGISCAN_API_KEY

Values are stored under the service name `tn-accountability`, encrypted at rest and
unlocked by your login. `config.require()` reads the environment first, then falls
back here, so nothing else in the codebase has to change.

This talks to the Keychain through the `keyring` library rather than the `security`
command. Both alternatives to that were bad: `security -w` reading from stdin silently
truncates at 128 characters (DATABASE_URL is longer than that), and passing the value
as an argument exposes it in `ps` output. The API has neither problem.
"""

from __future__ import annotations

import argparse
import getpass
import sys

SERVICE = "tn-accountability"

# Every secret the project uses, and where to get it. Shown by `check`.
KNOWN = {
    "DATABASE_URL": "Supabase -> Connect -> Session pooler (port 5432)",
    "LEGISCAN_API_KEY": "legiscan.com -> API key request",
    "SUPABASE_URL": "Supabase -> Project Settings -> API",
    "SUPABASE_ANON_KEY": "Supabase -> Project Settings -> API (browser-safe)",
    "SUPABASE_SERVICE_ROLE_KEY": "Supabase -> Project Settings -> API (server only, bypasses RLS)",
    "CLOUDFLARE_ACCOUNT_ID": "Cloudflare dashboard",
    "CLOUDFLARE_API_TOKEN": "Cloudflare -> My Profile -> API Tokens",
    "CLOUDFLARE_DEPLOY_HOOK_URL": "Cloudflare -> Worker -> Deploy hooks",
}


def available() -> bool:
    """True when a usable keyring backend is present."""
    try:
        import keyring
        from keyring.backends.fail import Keyring as FailKeyring
        return not isinstance(keyring.get_keyring(), FailKeyring)
    except Exception:
        return False


def get(name: str):
    """Return a secret, or None if it is not stored."""
    try:
        import keyring
        return keyring.get_password(SERVICE, name)
    except Exception:
        return None


def put(name: str, value: str) -> None:
    """Store a secret, replacing any existing entry.

    Always reads the value back and compares. A silently truncated secret is far
    worse than a failed write: it fails later, somewhere unrelated, looking like a
    credentials problem.
    """
    import keyring
    keyring.set_password(SERVICE, name, value)
    stored = get(name)
    if stored != value:
        raise RuntimeError(
            f"Keychain write for {name} did not round-trip "
            f"(stored {len(stored or '')} chars, expected {len(value)}).")


def delete(name: str) -> bool:
    try:
        import keyring
        keyring.delete_password(SERVICE, name)
        return True
    except Exception:
        return False


def names() -> list:
    """Names of stored secrets. Never returns values."""
    return sorted(n for n in KNOWN if get(n) is not None)


def _mask(v: str) -> str:
    """Enough to recognise a value, not enough to use it."""
    return f"{v[:4]}…{v[-2:]} ({len(v)} chars)" if len(v) > 12 else f"({len(v)} chars)"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for cmd, helptext in (("set", "store a secret (prompts)"),
                          ("delete", "remove a secret")):
        s = sub.add_parser(cmd, help=helptext)
        s.add_argument("name")
    sub.add_parser("list", help="names of stored secrets (never values)")
    sub.add_parser("check", help="show what resolves and from where")
    sub.add_parser("import-env", help="copy secrets from .env into the Keychain")
    args = p.parse_args(argv)

    if not available():
        print("No Keychain backend available here; keep using .env.", file=sys.stderr)
        return 1

    if args.cmd == "set":
        value = getpass.getpass(f"{args.name}: ")
        if not value:
            print("empty, nothing stored"); return 1
        put(args.name, value)
        print(f"stored {args.name} in the Keychain ({len(value)} chars)")

    elif args.cmd == "delete":
        print(f"deleted {args.name}" if delete(args.name) else f"{args.name} was not stored")

    elif args.cmd == "list":
        found = names()
        print("\n".join(f"  {n}" for n in found) if found else "  (nothing stored)")

    elif args.cmd == "check":
        import os
        from . import config  # loads .env as a side effect
        print(f"{'SECRET':<28} {'SOURCE':<10} VALUE")
        for n in KNOWN:
            kc, env = get(n), os.environ.get(n)
            # config.require() prefers the environment, so report that order.
            if env:
                print(f"{n:<28} {'env/.env':<10} {_mask(env)}")
            elif kc:
                print(f"{n:<28} {'keychain':<10} {_mask(kc)}")
            else:
                print(f"{n:<28} {'MISSING':<10} {KNOWN[n]}")

    elif args.cmd == "import-env":
        from . import config
        env_path = config.PROJECT_ROOT / ".env"
        if not env_path.exists():
            print("no .env to import"); return 1
        moved = 0
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k in KNOWN and v and not v.startswith("<"):
                put(k, v)
                print(f"  imported {k} ({len(v)} chars)")
                moved += 1
        print(f"\n{moved} secret(s) now in the Keychain.")
        print("`.env` is unchanged. Once `check` shows what you expect, you can delete it:")
        print("    rm .env")
        print("Keep `.env.example` — it documents what the project needs.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
