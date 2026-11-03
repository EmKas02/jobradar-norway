from jobradar import sources

RSS = b"""<?xml version="1.0"?>
<rss xmlns:tt="https://teamtailor.com/locations"><channel>
<item><title> Data Analyst </title><link>https://x.teamtailor.com/jobs/1</link>
<description>&lt;p&gt;Python og SQL&lt;/p&gt;</description><pubDate>Mon, 02 Nov 2026 10:00:00 +0100</pubDate>
<remoteStatus>none</remoteStatus><tt:locations><tt:location><tt:city>Stavanger</tt:city></tt:location></tt:locations></item>
<item><title>Engineer</title><link>https://x.teamtailor.com/jobs/2</link><description></description>
<remoteStatus>fully</remoteStatus><tt:locations><tt:location><tt:city>Oslo</tt:city></tt:location></tt:locations></item>
<item><title>Chef</title><link>https://x.teamtailor.com/jobs/3</link><description></description>
<remoteStatus>none</remoteStatus><tt:locations><tt:location><tt:city>Bergen</tt:city></tt:location></tt:locations></item>
</channel></rss>"""


class FakeResponse:
    content = RSS


def test_teamtailor_parse_and_keep(monkeypatch):
    monkeypatch.setattr(sources, "fetch", lambda url, **kw: FakeResponse())
    rows = sources.teamtailor({"name": "X", "host": "x.teamtailor.com"})
    assert [r["title"] for r in rows] == ["Data Analyst", "Engineer", "Chef"]
    assert rows[0]["location"] == "Stavanger" and rows[0]["text"] == "Python og SQL"
    assert rows[1]["remote"] == 1
    assert [sources.keep_company_job(r) for r in rows] == [True, True, False]
    assert len({r["uuid"] for r in rows}) == 3


def test_slug_candidates():
    assert sources.slug_candidates("European Payments Initiative (EPI)") == [
        "europeanpaymentsinitiative", "european-payments-initiative", "european", "epi"]
    assert sources.slug_candidates("Banco Plata, S.A.")[0] == "bancoplata"


def test_verify_remote_jobs(monkeypatch):
    postings = {
        "portcast": [{"title": "Data Analyst Intern", "location": "Singapore, Bangalore, Manila"}],
        "acme": [{"title": "Junior Data Analyst", "location": "Remote - Europe"}],
    }
    monkeypatch.setattr(sources, "ADAPTERS", {
        ats: (lambda c: postings.get(c["slug"], [])) for ats in sources.VERIFY_ATS})
    rows = [
        {"title": "Data Analyst Intern", "employer": "Portcast", "location": "Remote (open to Norway)"},
        {"title": "Junior Data Analyst", "employer": "Acme", "location": "Remote (open to Norway)"},
        {"title": "Data Scientist", "employer": "Unknown Co", "location": "Remote (worldwide)"},
    ]
    kept, dropped = sources.verify_remote_jobs(rows)
    assert [r["employer"] for r in kept] == ["Acme", "Unknown Co"]
    assert kept[0]["location"] == "Remote (verified: Remote - Europe)"
    assert kept[1]["location"].endswith("unverified")
    assert dropped[0][0]["employer"] == "Portcast"
