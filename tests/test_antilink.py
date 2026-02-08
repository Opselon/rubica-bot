from app.utils.regex import contains_link


def test_contains_link():
    assert contains_link("https://example.com")
    assert contains_link("www.example.ir")
    assert contains_link("t.me/rubika")
    assert contains_link("bit.ly/abc")
    assert contains_link("example.dev/path")
    assert not contains_link("سلام دنیا")
    assert not contains_link("متن بدون لینک")
