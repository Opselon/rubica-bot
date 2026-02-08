from app.utils.dedup import Deduplicator


def test_deduplicator():
    dedup = Deduplicator(10)
    assert not dedup.seen("1")
    assert dedup.seen("1")
