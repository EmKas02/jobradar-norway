"""Import jobs from LinkedIn's job alert emails in Mail.app.

LinkedIn's terms forbid scraping linkedin.com, so jobradar never opens it.
LinkedIn's own alert and recommendation emails list each job as:

    Title
    Company
    Location
    (optional extra lines, e.g. "Søk med CV og profil")
    Vis stilling: https://www.linkedin.com/comm/jobs/view/<id>/?...
    ---------------------------------------------------------

Each job is stored with a plain link to the job page for you to open.
"""
from __future__ import annotations

import email
import hashlib
import re
from datetime import datetime, timedelta, timezone
from email import policy
from email.utils import parsedate_to_datetime

from .finn import mail_sources

SENDERS = ("jobalerts-noreply@linkedin.com", "jobs-noreply@linkedin.com")

_VIEW = re.compile(r"^(?:Vis stilling|View job):\s*(https://\S+/jobs/view/(\d+)\S*)", re.MULTILINE)
_SEPARATOR = re.compile(r"^-{10,}\s*$", re.MULTILINE)
# Lines LinkedIn adds around a job that are not title, company or location.
_NOISE = re.compile(
    r"^(søk med cv og profil|easy apply|enkel søknad|aktivt rekrutterende|actively recruiting|fremmet|promoted|"
    r"dette firmaet ansetter|this company is hiring|"
    r"ny|new|\d+ (?:kontakter|connections|søkere|applicants).*|.*\b(?:alumn|tidligere ansatte)\b.*|"
    # Salary lines ("kr 700k–900k/år"). Not "/time": Time is also a municipality ("Klepp/Time").
    r".*(?:kr|nok|€|\$)\s?\d.*|.*/(?:år|yr|year)\b.*)$",
    re.IGNORECASE,
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
    for block in _SEPARATOR.split(part.get_content().replace("\r\n", "\n")):
        view = _VIEW.search(block)
        if not view:
            continue
        lines = [l.strip() for l in block[: view.start()].splitlines() if l.strip()]
        lines = [l for l in lines if not _NOISE.match(l)]
        if len(lines) < 3:
            continue
        title, employer, location = lines[-3], lines[-2], lines[-1]
        job_id = view.group(2)
        url = f"https://www.linkedin.com/jobs/view/{job_id}/"
        rows.append({
            # A plain hash id, so the first 8 characters work as a short id on the command line.
            "uuid": hashlib.sha1(f"linkedin|{job_id}".encode()).hexdigest()[:16],
            "source": "linkedin-mail",
            "title": title,
            "employer": employer,
            "location": location,
            "remote": int(bool(re.search(r"fjernarbeid|remote", location, re.I))),
            "url": url,
            "apply_url": url,
            "due": "",
            "published": received.isoformat(),
            # Alerts carry no deadline, so entries drop out of reports after keep_days.
            "expires": (received + timedelta(days=keep_days)).isoformat(),
            "text": "",
        })
    return rows


def load_alerts(days: int) -> list[dict]:
    rows: dict[str, dict] = {}
    for sender in SENDERS:
        for raw in mail_sources(days, sender):
            for row in parse_alert_email(raw):
                rows[row["uuid"]] = row
    return list(rows.values())
