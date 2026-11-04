import json

from jobradar import sources

# Same structure as FINN's pages, made-up content.
SEARCH = """
<w-card><article class="job-card" id="400000001"><div class="pl-16"></div>
<a class="job-card-link" href="https://www.finn.no/job/ad/400000001" id="card-anchor-400000001">Junior Data&shy;analytiker</a>
<div class="text-caption"><strong>Example Energi AS</strong></div>
<footer><ul><li class="min-w-0"><span class="block truncate">Stavanger</span></li>
<li><time dateTime="2026-11-02T08:00:00.000Z">2 dager siden</time></li></ul></footer></article></w-card>
<w-card><article class="job-card" id="400000002">
<a href="https://www.finn.no/job/ad/400000002" id="card-anchor-400000002">Sommerstudent 2027</a>
<div><strong>Example Bank</strong></div><span class="block truncate">Sandnes</span></article></w-card>
"""

POSTING = {"script:ld+json": {
    "@type": "JobPosting", "title": "Junior Dataanalytiker",
    "hiringOrganization": {"name": "Example Energi AS"},
    "jobLocation": {"address": {"addressLocality": "Stavanger"}},
    "description": "<p>Vi søker en nyutdannet analytiker med Python og SQL.</p>",
    "validThrough": None,
}}
AD = f"""<html><script type="application/ld+json">{json.dumps(POSTING)}</script>
<dl><dt>Søknadsfrist</dt><dd>20.11.2026</dd><dt>Hjemmekontor</dt><dd>Delvis hjemmekontor</dd></dl></html>"""


def test_parse_finn_search():
    cards = sources.parse_finn_search(SEARCH)
    assert [c["id"] for c in cards] == ["400000001", "400000002"]
    assert cards[0]["title"] == "Junior Data\xadanalytiker"
    assert (cards[0]["employer"], cards[0]["location"]) == ("Example Energi AS", "Stavanger")
    assert cards[0]["published"].startswith("2026-11-02")
    assert cards[1]["published"] == ""


def test_parse_finn_ad():
    info = sources.parse_finn_ad(AD)
    assert info["employer"] == "Example Energi AS"
    assert "Python og SQL" in info["text"]
    assert info["due"] == "20.11.2026"
    assert info["remote"] is False


class FakeResponse:
    def __init__(self, text):
        self.text = text


def test_finn_search_fetches_only_new_ads(monkeypatch):
    calls = []

    def fake_fetch(url, **params):
        calls.append(url)
        return FakeResponse(SEARCH if "search" in url else AD)

    monkeypatch.setattr(sources, "fetch", fake_fetch)
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    config = {"queries": ["data"], "location": "1.20001.20012", "max_new_ads": 5}
    rows = sources.finn_search(config, known={})
    assert len(rows) == 2 and rows[0]["due"] == "20.11.2026"
    assert sum("/job/ad/" in c for c in calls) == 2

    calls.clear()
    known = {r["uuid"]: r for r in rows}
    sources.finn_search(config, known)
    assert not any("/job/ad/" in c for c in calls)  # nothing new, so no ad pages
