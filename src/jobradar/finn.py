"""Import FINN.no ads from a local inbox folder.

FINN's terms forbid automated crawling, so this tool never fetches finn.no.
Instead, set up a saved search with email alerts on FINN, and when an ad looks
interesting, save it as a .txt file in the inbox:

    line 1: the ad URL
    line 2: Title - Employer - Location
    rest:   the ad text, pasted

The bookmarklet in finn_inbox/bookmarklet.md copies an open ad in this format,
and `jobradar finn --paste` saves it from the clipboard.
"""
from __future__ import annotations

import hashlib
import re
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
