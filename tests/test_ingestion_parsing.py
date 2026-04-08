from modules.news import parse_date


def test_parse_date_returns_iso_string_for_valid_rss_date():
    result = parse_date("Fri, 08 Apr 2026 10:00:00 GMT")
    assert result is not None
    assert "T" in result


def test_parse_date_returns_none_for_empty_input():
    assert parse_date("") is None
