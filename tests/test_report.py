from jobradar.report import _link
from jobradar.store import Store


def test_links_only_allow_http_and_escape_text():
    assert _link("Data [Analyst]", "https://example.com/job/1") == "[Data \\[Analyst\\]](https://example.com/job/1)"
    assert _link("Click", "javascript:alert(1)") == "Click"
    assert _link("Job", "https://x.com/a) [evil](https://y.com") == "Job"


def test_store_rejects_unknown_columns(tmp_path):
    store = Store(tmp_path / "t.db")
    try:
        store.upsert_ad({"uuid": "1", "source": "x", "title": "t", "evil) --": "x"})
    except ValueError:
        return
    raise AssertionError("unknown column was accepted")
