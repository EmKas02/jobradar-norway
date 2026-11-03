"""Company career boards and remote job boards.

Only sources with public, documented feeds are used (ATS job feeds and job
board APIs), and every request is checked against the host's robots.txt.
Sites that forbid automated access - such as FINN.no - are not fetched.
"""
from __future__ import annotations

import hashlib
import html
import time
import urllib.robotparser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable
from urllib.parse import urlsplit

import requests

from .filters import mentions_rogaland, remote_open_to_norway, strip_html

USER_AGENT = "jobradar-norway (personal job search tool)"
_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def allowed(url: str) -> bool:
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin not in _robots:
        parser = urllib.robotparser.RobotFileParser()
        try:
            resp = _session.get(origin + "/robots.txt", timeout=15)
            # No robots.txt means no restrictions.
            parser.parse(resp.text.splitlines() if resp.status_code == 200 else [])
        except requests.RequestException:
            parser = None
        _robots[origin] = parser
    parser = _robots[origin]
    return parser is None or parser.can_fetch(USER_AGENT, url)


def fetch(url: str, **params) -> requests.Response | None:
    if not allowed(url):
        print(f"  skipped (robots.txt disallows): {url}")
        return None
    resp = _session.get(url, params=params or None, timeout=30)
    resp.raise_for_status()
    time.sleep(0.5)
    return resp


def _iso(value) -> str:
    if not value:
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, timezone.utc).isoformat()
    return str(value)


def _row(source: str, key: str, **fields) -> dict:
    # A plain hash id, so the first 8 characters work as a short id on the command line.
    row = {"uuid": hashlib.sha1(f"{source}|{key}".encode()).hexdigest()[:16], "source": source,
           "title": "", "employer": "", "location": "", "remote": 0, "url": "", "apply_url": "",
           "due": "", "published": "", "expires": "", "text": ""}
    row.update(fields)
    row["remote"] = int(bool(row["remote"]))
    return row


# --- Company boards (one function per applicant tracking system) ---

TT = "{https://teamtailor.com/locations}"


def teamtailor(company: dict) -> list[dict]:
    resp = fetch(f"https://{company['host']}/jobs.rss")
    if not resp:
        return []
    rows = []
    for item in ET.fromstring(resp.content).iter("item"):
        cities = sorted({c.text for c in item.iter(TT + "city") if c.text})
        link = item.findtext("link") or ""
        rows.append(_row(
            f"teamtailor:{company['host'].split('.')[0]}", link,
            title=(item.findtext("title") or "").strip(),
            employer=company["name"],
            location=", ".join(cities),
            remote=(item.findtext("remoteStatus") or "").lower() == "fully",
            url=link, apply_url=link,
            published=parsedate_to_datetime(item.findtext("pubDate")).isoformat() if item.findtext("pubDate") else "",
            text=strip_html(item.findtext("description")),
        ))
    return rows


def greenhouse(company: dict) -> list[dict]:
    resp = fetch(f"https://boards-api.greenhouse.io/v1/boards/{company['slug']}/jobs", content="true")
    if not resp:
        return []
    rows = []
    for job in resp.json().get("jobs", []):
        location = (job.get("location") or {}).get("name", "")
        rows.append(_row(
            f"greenhouse:{company['slug']}", str(job["id"]),
            title=job["title"], employer=company["name"], location=location,
            remote="remote" in location.lower(),
            url=job["absolute_url"], apply_url=job["absolute_url"],
            published=job.get("first_published") or "",
            due=job.get("application_deadline") or "",
            text=strip_html(html.unescape(job.get("content") or "")),
        ))
    return rows


def ashby(company: dict) -> list[dict]:
    resp = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{company['slug']}")
    if not resp:
        return []
    rows = []
    for job in resp.json().get("jobs", []):
        places = [job.get("location") or ""] + [s.get("location", "") for s in job.get("secondaryLocations") or []]
        rows.append(_row(
            f"ashby:{company['slug']}", job["id"],
            title=job["title"], employer=company["name"], location="; ".join(p for p in places if p),
            remote=job.get("isRemote") or job.get("workplaceType") == "Remote",
            url=job["jobUrl"], apply_url=job.get("applyUrl") or job["jobUrl"],
            published=job.get("publishedAt") or "",
            text=job.get("descriptionPlain") or "",
        ))
    return rows


def lever(company: dict) -> list[dict]:
    resp = fetch(f"https://api.lever.co/v0/postings/{company['slug']}", mode="json")
    if not resp:
        return []
    rows = []
    for job in resp.json():
        cats = job.get("categories") or {}
        rows.append(_row(
            f"lever:{company['slug']}", job["id"],
            title=job["text"], employer=company["name"],
            location=", ".join(cats.get("allLocations") or [cats.get("location", "")]),
            remote=job.get("workplaceType") == "remote",
            url=job["hostedUrl"], apply_url=job.get("applyUrl") or job["hostedUrl"],
            published=_iso(job.get("createdAt")),
            text=" ".join([job.get("descriptionPlain") or "", job.get("additionalPlain") or ""]),
        ))
    return rows


def workable(company: dict) -> list[dict]:
    resp = fetch(f"https://apply.workable.com/api/v1/widget/accounts/{company['slug']}")
    if not resp:
        return []
    rows = []
    for job in resp.json().get("jobs", []):
        # The widget feed has no description; title and department still score.
        rows.append(_row(
            f"workable:{company['slug']}", job["shortcode"],
            title=job["title"], employer=company["name"],
            location=", ".join(p for p in (job.get("city"), job.get("country")) if p),
            remote=job.get("telecommuting"),
            url=job["url"], apply_url=job.get("application_url") or job["url"],
            published=job.get("published_on") or "",
            text=" ".join(p for p in (job.get("department"), job.get("function"), job.get("experience")) if p),
        ))
    return rows


ADAPTERS: dict[str, Callable[[dict], list[dict]]] = {
    "teamtailor": teamtailor,
    "greenhouse": greenhouse,
    "ashby": ashby,
    "lever": lever,
    "workable": workable,
}


def keep_company_job(row: dict) -> bool:
    """Rogaland jobs, or remote jobs that someone living in Norway can take."""
    if mentions_rogaland(row["location"]):
        return True
    return bool(row["remote"]) and remote_open_to_norway(row["location"])


# --- Remote job boards ---

HIMALAYAS_SEARCH = "https://himalayas.app/jobs/api/search"


def himalayas(queries: list[str], seniority: str = "Entry-level", max_pages: int = 5) -> list[dict]:
    """Remote jobs open to people in Norway. Himalayas asks for a visible
    credit and that applications go through its applicationLink."""
    rows: dict[str, dict] = {}
    for query in queries:
        for page in range(1, max_pages + 1):
            resp = fetch(HIMALAYAS_SEARCH, q=query, country="Norway", seniority=seniority, page=page)
            jobs = resp.json().get("jobs", []) if resp else []
            for job in jobs:
                worldwide = not job.get("locationRestrictions")
                rows[job["guid"]] = _row(
                    "himalayas", job["guid"],
                    title=job["title"], employer=job.get("companyName", ""),
                    location="Remote (worldwide)" if worldwide else "Remote (open to Norway)",
                    remote=True,
                    url=job["guid"], apply_url=job.get("applicationLink") or job["guid"],
                    published=_iso(job.get("pubDate")), expires=_iso(job.get("expiryDate")),
                    text=strip_html(job.get("description")),
                )
            if len(jobs) < 20:
                break
    return list(rows.values())
