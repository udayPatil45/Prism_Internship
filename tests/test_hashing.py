from utils.hashing import article_hash, normalize_url, url_hash


def test_normalize_url_variants_match():
    a = url_hash("https://www.Example.com/path/")
    b = url_hash("https://example.com/path")
    assert a == b


def test_url_hash_distinct():
    assert url_hash("https://a.com/x") != url_hash("https://a.com/y")


def test_article_hash_whitespace_insensitive():
    assert article_hash("Hello   World\n") == article_hash("hello world")
