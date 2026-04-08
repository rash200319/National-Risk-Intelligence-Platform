from collector import RiskCollector


def test_analyze_context_boosts_crisis_and_detects_industry():
    collector = RiskCollector()
    score, _, industries = collector._analyze_context(
        "Emergency fuel crisis in Colombo after sudden grid shutdown"
    )
    assert score >= 8
    assert "Energy & Fuel" in industries


def test_analyze_context_defaults_to_general_when_no_keywords_found():
    collector = RiskCollector()
    _, _, industries = collector._analyze_context("Minor community event and local meetup")
    assert "General" in industries
