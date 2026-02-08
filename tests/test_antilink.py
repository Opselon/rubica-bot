from app.utils.regex import contains_link


def test_contains_link():
    assert contains_link("https://example.com")
    assert contains_link("www.example.ir")
    assert not contains_link("سلام دنیا")
