from __future__ import annotations

from typing import Iterator

import click
import httpx

from bbcli.auth import get_auth

BASE_URL = "https://api.bitbucket.org/2.0"

_FRIENDLY_ERRORS = {
    401: "Authentication failed. Run: bb auth login",
    403: "Permission denied. Check your API token has the required scopes.",
    404: "Not found. Check your workspace, repo slug, and resource ID.",
}


class BitbucketClient:
    """HTTP client for Bitbucket Cloud API using app password (Basic auth)."""

    def __init__(self) -> None:
        email, api_token = get_auth()
        self._client = httpx.Client(
            base_url=BASE_URL,
            auth=(email, api_token),
            follow_redirects=True,
            timeout=30.0,
        )

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code in _FRIENDLY_ERRORS:
            msg = _FRIENDLY_ERRORS[resp.status_code]
            # Try to extract a more specific message from the API response
            try:
                detail = resp.json().get("error", {}).get("message", "")
                if detail:
                    msg = f"{detail} ({resp.status_code})"
            except Exception:
                pass
            raise click.ClickException(msg)
        resp.raise_for_status()
        return resp

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> httpx.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        return self.request("DELETE", path, **kwargs)

    def paginate(self, path: str, params: dict | None = None, limit: int = 0) -> Iterator[dict]:
        """Yield items from all pages. If limit > 0, stop after that many items."""
        params = dict(params or {})
        count = 0
        # First request uses relative path
        resp = self.get(path, params=params)
        while True:
            data = resp.json()
            for item in data.get("values", []):
                yield item
                count += 1
                if limit and count >= limit:
                    return
            next_url = data.get("next")
            if not next_url:
                break
            # Subsequent requests use the full URL directly (bypass base_url)
            resp = self._client.get(next_url)
            resp.raise_for_status()

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
