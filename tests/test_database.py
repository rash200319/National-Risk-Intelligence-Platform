from database_manager import DatabaseManager


def test_batch_insert_deduplicates_records(tmp_path):
    db_path = tmp_path / "modelx_test.db"
    manager = DatabaseManager(str(db_path))

    record = {
        "source": "SourceA",
        "signal": "Repeated signal",
        "risk_score": 6,
        "published": "2026-04-08T10:00:00",
    }

    first = manager.batch_insert_risks([record])
    second = manager.batch_insert_risks([record])

    assert first == 1
    assert second == 0


def test_get_risks_filters_by_sources(tmp_path):
    db_path = tmp_path / "modelx_test_filters.db"
    manager = DatabaseManager(str(db_path))

    manager.batch_insert_risks(
        [
            {"source": "NewsOne", "signal": "alpha", "risk_score": 4, "published": "2026-04-08T08:00:00"},
            {"source": "NewsTwo", "signal": "beta", "risk_score": 8, "published": "2026-04-08T09:00:00"},
        ]
    )

    filtered = manager.get_risks(sources=["NewsTwo"], limit=10)

    assert not filtered.empty
    assert set(filtered["source"].unique()) == {"NewsTwo"}
