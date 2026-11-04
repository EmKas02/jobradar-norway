"""Import FINN.no ads from a local inbox folder.

The main FINN source is the job search in sources.py (finn_search), used with
FINN's written permission. This module covers the other ways in: ads you save
by hand, the bookmarklet, and FINN's alert emails. To save an ad by hand, put a
.txt file in the inbox:

    line 1: the ad URL
    line 2: Title - Employer - Location
    rest:   the ad text, pasted

The bookmarklet in finn_inbox/bookmarklet.md copies an open ad in this format,
and `jobradar finn --paste` saves it from the clipboard.

`jobradar finn --mail` reads FINN's job alert emails in Mail.app and adds each
job as a short entry (employer, title, teaser and the email's link). The links
are FINN's click-tracking redirects; they are stored as-is and never followed.
"""
from __future__ import annotations

import email
import hashlib
import re
import subprocess
from datetime import datetime, timedelta, timezone
from email import policy
from email.utils import parsedate_to_datetime
from pathlib import Path

from .filters import is_remote


def parse_inbox_file(path: Path) -> dict | None:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) < 3:
        return None
    url, header, body = lines[0].strip(), lines[1].strip(), "\n".join(lines[2:]).strip()
    parts = [p.strip() for p in re.split(r"\s+[-–|]\s+", header)]
    finn_code = re.search(r"(\d{6,})", url)
    key = finn_code.group(1) if finn_code else hashlib.sha1(url.encode()).hexdigest()[:10]
    return {
        "uuid": f"finn-{key}",
        "source": "finn",
        "title": parts[0],
        "employer": parts[1] if len(parts) > 1 else "",
        "location": parts[2] if len(parts) > 2 else "",
        "remote": int(is_remote(body)),
        "url": url,
        "apply_url": url,
        "due": "",
        "published": "",
        "expires": "",
        "text": body,
    }


def save_pasted_ad(text: str, folder: Path) -> Path:
    """Save clipboard text (from the bookmarklet) as an inbox file."""
    lines = text.strip().splitlines()
    if len(lines) < 3 or not re.match(r"https://(www\.)?finn\.no/", lines[0].strip()):
        raise ValueError("clipboard does not look like a FINN ad copied with the bookmarklet")
    code = re.search(r"(\d{6,})", lines[0])
    name = code.group(1) if code else hashlib.sha1(lines[0].encode()).hexdigest()[:10]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.txt"
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def load_inbox(folder: Path) -> list[dict]:
    ads = []
    for path in sorted(folder.glob("*.txt")):
        ad = parse_inbox_file(path)
        if ad:
            ads.append(ad)
    return ads


# In the plain-text part of FINN's alert emails each job looks like:
#   Employer
#   ----------
#   Title
#   ( https://clicks.inspirasjon.finn.no/... )
#   ----------
#   One-line teaser
# with blank lines between some of the parts.
_ALERT_JOB = re.compile(
    r"^(?P<employer>[^\n]+?)[ \t]*\n\s*-{10,}\s*\n\s*(?P<title>[^\n]+?)[ \t]*\n\s*"
    r"\(\s*(?P<link>https://\S+)\s*\)\s*\n\s*-{10,}\s*\n\s*(?P<teaser>[^\n]*)",
    re.MULTILINE,
)


def parse_alert_email(raw: bytes, keep_days: int = 30) -> list[dict]:
    msg = email.message_from_bytes(raw, policy=policy.default)
    part = msg.get_body(preferencelist=("plain",))
    if part is None:
        return []
    try:
        received = parsedate_to_datetime(msg["Date"])
    except (TypeError, ValueError):
        received = datetime.now(timezone.utc)
    rows = []
    for m in _ALERT_JOB.finditer(part.get_content().replace("\r\n", "\n")):
        employer, title = m["employer"].strip(), m["title"].strip()
        # A plain hash id, so the first 8 characters work as a short id on the command line.
        key = hashlib.sha1(f"finn-mail|{employer}|{title}".lower().encode()).hexdigest()[:16]
        rows.append({
            "uuid": key,
            "source": "finn-mail",
            "title": title,
            "employer": employer,
            "location": "",
            "remote": 0,
            "url": m["link"],
            "apply_url": m["link"],
            "due": "",
            "published": received.isoformat(),
            # Alerts carry no deadline, so entries drop out of reports after keep_days.
            "expires": (received + timedelta(days=keep_days)).isoformat(),
            "text": m["teaser"].strip(),
        })
    return rows


_SEP = "=====JOBRADAR-MESSAGE====="


def mail_alert_sources(days: int) -> list[bytes]:
    """Raw source of FINN job alert emails from the last `days` days in Mail.app.
    Only messages from FINN's alert sender are read; nothing else is touched."""
    script = f'''
    tell application "Mail"
        set cutoff to (current date) - ({int(days)} * days)
        set msgs to (messages of inbox whose sender contains "inspirasjon.finn.no" and date received > cutoff)
        set out to ""
        repeat with m in msgs
            set out to out & (source of m) & "{_SEP}"
        end repeat
        return out
    end tell'''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True)
    return [chunk.strip().encode() for chunk in result.stdout.split(_SEP) if chunk.strip()]
