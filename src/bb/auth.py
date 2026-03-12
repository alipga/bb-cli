from __future__ import annotations

import json
import os
from pathlib import Path

SERVICE_NAME = "bb"
CONFIG_DIR = Path.home() / ".config" / "bb"
TOKEN_FILE = CONFIG_DIR / "tokens.json"


# --- Token storage (keyring with file fallback) ---

def _try_keyring_store(key: str, value: str) -> bool:
    try:
        import keyring as kr
        kr.set_password(SERVICE_NAME, key, value)
        return True
    except Exception:
        return False


def _try_keyring_get(key: str) -> str | None:
    try:
        import keyring as kr
        return kr.get_password(SERVICE_NAME, key)
    except Exception:
        return None


def _try_keyring_delete(key: str) -> bool:
    try:
        import keyring as kr
        kr.delete_password(SERVICE_NAME, key)
        return True
    except Exception:
        return False


def _file_store(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(data))
    TOKEN_FILE.chmod(0o600)


def _file_load() -> dict | None:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def _file_delete() -> None:
    TOKEN_FILE.unlink(missing_ok=True)


def store_credentials(email: str, api_token: str) -> None:
    payload = json.dumps({"email": email, "api_token": api_token})
    if not _try_keyring_store("credentials", payload):
        _file_store(json.loads(payload))


def load_credentials() -> dict | None:
    raw = _try_keyring_get("credentials")
    if raw:
        return json.loads(raw)
    return _file_load()


def clear_credentials() -> None:
    _try_keyring_delete("credentials")
    _file_delete()


def get_auth() -> tuple[str, str]:
    """Return (email, api_token) for Basic auth, or exit."""
    creds = load_credentials()
    if not creds:
        raise SystemExit("Not logged in. Run: bb auth login")
    return creds["email"], creds["api_token"]


# --- CLI actions ---

def login() -> None:
    """Prompt for email and API token, verify, then store."""
    import click
    import httpx
    click.echo("Tip: Create an API token at https://id.atlassian.com/manage-profile/security/api-tokens")
    click.echo("     Required permissions: read:{project,pullrequest,repository,runner,workspace,user}")
    click.echo("                           write:{pullrequest,issue}")
    click.echo()
    email = click.prompt("Bitbucket account email")
    api_token = click.prompt("API token", hide_input=True)
    resp = httpx.get(
        "https://api.bitbucket.org/2.0/user",
        auth=(email, api_token),
        timeout=10.0,
    )
    if resp.status_code != 200:
        raise SystemExit(f"Authentication failed (HTTP {resp.status_code}). Check your email and API token.")
    user = resp.json()
    store_credentials(email, api_token)
    click.echo(f"Logged in as {user.get('display_name', '')} ({email})")


def status() -> dict | None:
    """Check stored credentials and verify them against the API."""
    creds = load_credentials()
    if not creds:
        return None
    import httpx
    resp = httpx.get(
        "https://api.bitbucket.org/2.0/user",
        auth=(creds["email"], creds["api_token"]),
        timeout=10.0,
    )
    if resp.status_code == 200:
        user = resp.json()
        creds["display_name"] = user.get("display_name", "")
        creds["username"] = user.get("username", "")
        creds["valid"] = True
    else:
        creds["valid"] = False
    return creds


def logout() -> None:
    clear_credentials()
    print("Logged out.")
