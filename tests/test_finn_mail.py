from email.message import EmailMessage

from jobradar.finn import parse_alert_email

# Same layout as FINN's weekly alert emails, with made-up content.
PLAIN = """Ukens stillinger basert på din Jobbprofil
Example Energy AS
-----------------------------------------------------------------
Sommerstudent 2027 - Data Science
( https://clicks.inspirasjon.finn.no/f/a/abc~~/def~/ghi )
-----------------------------------------------------------------
Bli med på sommerens dataprosjekter.
Example Consulting

-----------------------------------------------------------------
Nyutdannet 2027 - Stavanger
( https://clicks.inspirasjon.finn.no/f/a/jkl~~/mno~/pqr )
-----------------------------------------------------------------
Vi søker flere nyutdannede!
Se alle stillinger
( https://clicks.inspirasjon.finn.no/f/a/all )
"""


def make_email() -> bytes:
    msg = EmailMessage()
    msg["From"] = "FINN <FINN@inspirasjon.finn.no>"
    msg["Subject"] = "Ukens stillinger basert på din Jobbprofil"
    msg["Date"] = "Wed, 28 Oct 2026 13:00:19 +0100"
    msg.set_content(PLAIN)
    msg.add_alternative("<p>html version</p>", subtype="html")
    return bytes(msg)


def test_parse_alert_email():
    rows = parse_alert_email(make_email())
    assert [(r["employer"], r["title"]) for r in rows] == [
        ("Example Energy AS", "Sommerstudent 2027 - Data Science"),
        ("Example Consulting", "Nyutdannet 2027 - Stavanger"),
    ]
    assert rows[0]["url"].startswith("https://clicks.inspirasjon.finn.no/")
    assert rows[0]["text"] == "Bli med på sommerens dataprosjekter."
    assert rows[0]["expires"].startswith("2026-11-27")
    assert len({r["uuid"] for r in rows}) == 2
