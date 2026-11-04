from email.message import EmailMessage

from jobradar.linkedin import parse_alert_email

# Same layout as LinkedIn's job alert emails (Norwegian interface), made-up jobs.
PLAIN = """Stillingsvarselet ditt for Dataanalytiker i Stavanger
Nye stillinger passer til preferansene dine.
Junior Data Analyst
Example Energy AS
Klepp/Time

Dette firmaet ansetter
Vis stilling: https://www.linkedin.com/comm/jobs/view/4000000001/?trackingId=abc&refId=x
---------------------------------------------------------
Data Engineer
Example Remote Co
Norge (Fjernarbeid)
Søk med CV og profil
kr 600k–700k/år
Vis stilling: https://www.linkedin.com/comm/jobs/view/4000000002/?trk=eml
---------------------------------------------------------
Se alle stillinger på LinkedIn: https://www.linkedin.com/comm/jobs/search-results/
"""


def make_email() -> bytes:
    msg = EmailMessage()
    msg["From"] = "LinkedIn-stillingsvarsler <jobalerts-noreply@linkedin.com>"
    msg["Subject"] = "Example Energy AS ansetter en Junior Data Analyst"
    msg["Date"] = "Wed, 04 Nov 2026 09:46:30 +0100"
    msg.set_content(PLAIN)
    msg.add_alternative("<p>html version</p>", subtype="html")
    return bytes(msg)


def test_parse_linkedin_alert():
    rows = parse_alert_email(make_email())
    assert [(r["title"], r["employer"], r["location"]) for r in rows] == [
        ("Junior Data Analyst", "Example Energy AS", "Klepp/Time"),
        ("Data Engineer", "Example Remote Co", "Norge (Fjernarbeid)"),
    ]
    assert rows[0]["url"] == "https://www.linkedin.com/jobs/view/4000000001/"  # tracking removed
    assert rows[0]["remote"] == 0 and rows[1]["remote"] == 1
    assert rows[0]["expires"].startswith("2026-12-04")
