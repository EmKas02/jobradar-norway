"""Cheap pre-filters that decide which ads are worth fetching and keeping."""
from __future__ import annotations

import html
import re

# Municipalities in Rogaland county (2024 structure), uppercase as NAV returns them.
ROGALAND_MUNICIPALITIES = {
    "STAVANGER", "SANDNES", "SOLA", "RANDABERG", "KLEPP", "TIME", "HÅ", "GJESDAL",
    "STRAND", "HJELMELAND", "SULDAL", "SAUDA", "BJERKREIM", "EIGERSUND", "SOKNDAL",
    "LUND", "KARMØY", "HAUGESUND", "TYSVÆR", "BOKN", "VINDAFJORD", "UTSIRA", "KVITSØY",
}

# Title stems that suggest a data/analytics/tech or entry-level role (Norwegian + English).
_TITLE_PATTERN = re.compile(
    r"data|analy|statisti|python|\bsql\b|power ?bi|\bbi\b|business intelligence|"
    r"maskinlæring|machine learning|kunstig intelligens|\bai\b|\bml\b|"
    r"utvikler(?!\s+deg)|developer|software|programmer|rapportering|reporting|insight|innsikt|"
    r"trainee|graduate|nyutdannet|internship|\bintern\b|sommerstudent|summer student",
    re.IGNORECASE,
)

# Deliberately strict: "remote" alone also matches offshore "remote operations",
# and "hjemmekontor" is usually a perk, not a fully remote role.
_REMOTE_PATTERN = re.compile(
    r"fully remote|100 ?% remote|remote[- ]first|remote (?:work|position|role|job)|"
    r"work(?:ing)? remotely|fjernarbeid|heltid hjemmekontor|full(?:t)? hjemmekontor|"
    r"jobbe (?:fullt )?hjemmefra|hvor som helst i norge|anywhere in norway|fully distributed",
    re.IGNORECASE,
)


def is_rogaland(municipal: str | None) -> bool:
    return bool(municipal) and municipal.upper() in ROGALAND_MUNICIPALITIES


def title_is_relevant(title: str | None) -> bool:
    return bool(title) and bool(_TITLE_PATTERN.search(title))


def is_remote(text: str) -> bool:
    return bool(_REMOTE_PATTERN.search(text))


def strip_html(raw: str | None) -> str:
    if not raw:
        return ""
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()


# Towns and areas that appear in free-text locations but are not municipality names.
_ROGALAND_PLACES = ROGALAND_MUNICIPALITIES | {
    "ROGALAND", "FORUS", "TANANGER", "BRYNE", "EGERSUND", "KOPERVIK", "ÅKREHAMN",
    "JØRPELAND", "ÅLGÅRD", "RISAVIKA", "HINNA", "MADLA", "NÆRBØ", "VARHAUG",
}
_ROGALAND_PATTERN = re.compile(r"\b(" + "|".join(sorted(_ROGALAND_PLACES, key=len, reverse=True)) + r")\b", re.IGNORECASE)

_NORWAY_OK_PATTERN = re.compile(
    r"norway|norge|nordic|nordics|scandinavia|europe|emea|\beu\b|\beea\b|anywhere|worldwide|global|"
    r"oslo|bergen|trondheim|stavanger|fornebu|lysaker|kristiansand|tromsø",
    re.IGNORECASE,
)


def mentions_rogaland(location: str | None) -> bool:
    return bool(location) and bool(_ROGALAND_PATTERN.search(location))


def remote_open_to_norway(location: str | None) -> bool:
    """A remote job with no location limit, or one that names Norway or a wider region."""
    return not location or bool(_NORWAY_OK_PATTERN.search(location))


_NO_WORDS = {"og", "er", "du", "vi", "til", "med", "som", "på", "ikke", "har", "deg", "oss", "av", "kan", "det", "en", "et", "å", "eller", "hos"}
_EN_WORDS = {"and", "the", "you", "we", "to", "with", "of", "our", "is", "are", "will", "your", "in", "a", "for", "or", "at", "be"}


def detect_language(text: str) -> str:
    """'no' or 'en', by counting common function words - enough to pick a CV."""
    words = re.findall(r"[a-zæøå]+", text.lower())
    no = sum(w in _NO_WORDS for w in words)
    en = sum(w in _EN_WORDS for w in words)
    return "no" if no > en else "en"
