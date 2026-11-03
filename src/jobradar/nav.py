"""Client for NAV's job vacancy feed (pam-stilling-feed).

Docs: https://navikt.github.io/pam-stilling-feed/
The feed is a paginated change log: every edit to an ad creates a new item,
so the newest item for a given uuid holds the ad's current status.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Iterator

import requests

BASE_URL = "https://pam-stilling-feed.nav.no"
TOKEN_URL = f"{BASE_URL}/api/publicToken"


class NavFeed:
    def __init__(self, token: str | None = None, delay: float = 0.1):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "jobradar-norway (personal job search tool)"
        self.delay = delay
        # A private token (NAV_FEED_TOKEN) is preferred; the public one rotates.
        self._static_token = token or os.environ.get("NAV_FEED_TOKEN")
        self._set_token(self._static_token or self._fetch_public_token())

    def _fetch_public_token(self) -> str:
        resp = self.session.get(TOKEN_URL, timeout=30)
        resp.raise_for_status()
        # The endpoint returns a short description followed by the JWT on the last line.
        return resp.text.strip().splitlines()[-1].strip()

    def _set_token(self, token: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _get(self, path: str, headers: dict | None = None) -> dict:
        resp = self.session.get(BASE_URL + path, headers=headers, timeout=30)
        if resp.status_code == 401 and not self._static_token:
            self._set_token(self._fetch_public_token())
            resp = self.session.get(BASE_URL + path, headers=headers, timeout=30)
        resp.raise_for_status()
        time.sleep(self.delay)
        return resp.json()

    def iter_items(self, since: datetime) -> Iterator[dict]:
        """Yield feed items modified after `since`, oldest first."""
        headers = {"If-Modified-Since": format_datetime(since.astimezone(timezone.utc), usegmt=True)}
        page = self._get("/api/v1/feed", headers)
        while True:
            yield from page["items"]
            if not page.get("next_id"):
                return
            page = self._get(page["next_url"])

    def get_ad(self, entry_url: str) -> dict | None:
        return self._get(entry_url).get("ad_content")


def latest_by_uuid(items: Iterator[dict]) -> dict[str, dict]:
    """Collapse the change log so each uuid maps to its most recent item."""
    latest: dict[str, dict] = {}
    for item in items:
        latest[item["_feed_entry"]["uuid"]] = item
    return latest
