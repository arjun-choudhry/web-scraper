import pytest

from server.validation.url_list import parse_urls, validate_public_urls


def test_parse_urls_deduplicates_and_trims():
    values = parse_urls(
        ["https://example.com"],
        "https://example.com\nhttps://example.org\n\n",
    )
    assert values == ["https://example.com", "https://example.org"]


def test_validate_public_urls_rejects_localhost():
    with pytest.raises(ValueError):
        validate_public_urls(["http://localhost:8000"])
