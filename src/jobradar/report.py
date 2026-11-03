"""Render scored ads as a Markdown report, with Rogaland and remote jobs apart."""
from __future__ import annotations

import re
from datetime import date

from .filters import detect_language, mentions_rogaland
from .matcher import Match

CV = {"no": "NO", "en": "EN"}


def _cell(text: str | None) -> str:
    return (text or "").replace("|", "/").replace("\n", " ")


def _link(text: str | None, url: str | None) -> str:
    """Markdown link from feed data: escape the text and allow only http(s) URLs."""
    label = re.sub(r"([\\`*_\[\]<>])", r"\\\1", _cell(text))
    if url and re.match(r"https?://[^\s()<>]+$", url):
        return f"[{label}]({url})"
    return label


def _source(source: str) -> str:
    # Himalayas' API terms ask for a visible credit.
    return "Himalayas (himalayas.app)" if source == "himalayas" else source


def is_local(ad: dict) -> bool:
    return mentions_rogaland(ad["location"]) or not ad["remote"]


def _table(scored: list[tuple[dict, Match]]) -> list[str]:
    lines = [
        "| Score | Title | Employer | Location | Due | CV | Flags | ID |",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for ad, m in scored:
        place = "Remote" if ad["remote"] and not ad["location"] else _cell(ad["location"])
        status = f" **[{ad['status']}]**" if ad.get("status") else ""
        lines.append(
            f"| {m.score} | {_link(ad['title'], ad['url'])}{status} | {_cell(ad['employer'])} "
            f"| {place} | {_cell(ad['due'])} | {CV[detect_language(ad['title'] + ' ' + ad['text'])]} "
            f"| {', '.join(m.flags)} | `{ad['uuid'][:8]}` |"
        )
    return lines


def render(scored: list[tuple[dict, Match]], top: int) -> str:
    local = [p for p in scored if is_local(p[0])][:top]
    remote = [p for p in scored if not is_local(p[0])][:top]
    lines = [
        f"# Job matches - {date.today().isoformat()}",
        "",
        f"{len(scored)} open ads scored. CV column: which CV to send, based on the language of the ad.",
        "",
        f"## Rogaland (top {len(local)})",
        "",
        *_table(local),
        "",
        f"## Remote, open to Norway (top {len(remote)})",
        "",
        *_table(remote),
        "",
        "## Details",
        "",
    ]
    for ad, m in local + remote:
        lines += [
            f"### {m.score} - {_cell(ad['title'])} ({_cell(ad['employer'])})",
            f"- Source: {_source(ad['source'])} - {_link('ad', ad['url'])}"
            + (f" - {_link('apply', ad['apply_url'])}" if ad["apply_url"] and ad["apply_url"] != ad["url"] else ""),
            f"- Matched skills: {', '.join(m.skills) or 'none'}",
            f"- Flags: {', '.join(m.flags) or 'none'}",
            "",
        ]
    return "\n".join(lines)
