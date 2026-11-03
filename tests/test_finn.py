import pytest

from jobradar.finn import parse_inbox_file, save_pasted_ad


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


def test_save_pasted_ad(tmp_path):
    text = "https://www.finn.no/job/ad/412345678\nData Analyst\nVi søker en analytiker i Stavanger.\n"
    path = save_pasted_ad(text, tmp_path)
    assert path.name == "412345678.txt"
    assert parse_inbox_file(path)["title"] == "Data Analyst"
    with pytest.raises(ValueError):
        save_pasted_ad("https://example.com\nnot finn\ntext", tmp_path)
