from jobradar.filters import is_remote, is_rogaland, strip_html, title_is_relevant


def test_rogaland_municipalities():
    assert is_rogaland("STAVANGER")
    assert is_rogaland("Klepp")
    assert not is_rogaland("BERGEN")
    assert not is_rogaland(None)


def test_title_relevance():
    assert title_is_relevant("Dataanalytiker")
    assert title_is_relevant("Junior BI Developer")
    assert title_is_relevant("Graduate Programme 2027")
    assert not title_is_relevant("Kokk")
    assert not title_is_relevant("Sjåfør og montør")
    assert not title_is_relevant("Tømrerjobb der du trives, utvikler deg")


def test_remote_detection():
    assert is_remote("This is a fully remote position")
    assert is_remote("Du kan jobbe hjemmefra hvor som helst i Norge")
    assert not is_remote("Vi tilbyr hjemmekontor og fleksibel arbeidstid")
    assert not is_remote("Remote operations centre offshore")


def test_strip_html():
    assert strip_html("<p>Hei &amp; velkommen</p><ul><li>SQL</li></ul>") == "Hei & velkommen\n SQL"


def test_rogaland_in_free_text_locations():
    from jobradar.filters import mentions_rogaland
    assert mentions_rogaland("Stavanger, Oslo")
    assert mentions_rogaland("Forus")
    assert not mentions_rogaland("Bergen")
    assert not mentions_rogaland("Haugalandet Vest")  # no false hits inside other words


def test_remote_open_to_norway():
    from jobradar.filters import remote_open_to_norway
    assert remote_open_to_norway("")
    assert remote_open_to_norway("Remote - Europe")
    assert remote_open_to_norway("Oslo")
    assert not remote_open_to_norway("Remote in the United States")
    assert remote_open_to_norway("Remote")
    assert remote_open_to_norway("Virtual")
    assert not remote_open_to_norway("USA (remote)")
    assert not remote_open_to_norway("Singapore, Bangalore, Manila")
    assert not remote_open_to_norway("Remote-First in France, Remote-First in Netherlands")


def test_detect_language():
    from jobradar.filters import detect_language
    assert detect_language("Vi søker en analytiker som har erfaring med SQL og Python") == "no"
    assert detect_language("We are looking for an analyst with experience in SQL and Python") == "en"
