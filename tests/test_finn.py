from jobradar.finn import parse_inbox_file


def test_parse_inbox_file(tmp_path):
    f = tmp_path / "ad.txt"
    f.write_text(
        "https://www.finn.no/job/ad/412345678\n"
        "Junior Data Analyst - Example AS - Stavanger\n"
        "Vi søker en nyutdannet analytiker. Fully remote is possible.\n",
        encoding="utf-8",
    )
    ad = parse_inbox_file(f)
    assert ad["uuid"] == "finn-412345678"
    assert (ad["title"], ad["employer"], ad["location"]) == ("Junior Data Analyst", "Example AS", "Stavanger")
    assert ad["remote"] == 1


def test_too_short_file_is_skipped(tmp_path):
    f = tmp_path / "ad.txt"
    f.write_text("https://www.finn.no/job/ad/1\n", encoding="utf-8")
    assert parse_inbox_file(f) is None
