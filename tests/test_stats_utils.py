from app.utils.formatting import format_duration
from app.utils.safe_math import safe_eval
from app.utils.stats import StatsCollector


def test_stats_collector_records_metrics() -> None:
    stats = StatsCollector()
    stats.record_enqueue(3)
    stats.record_dispatch(12.5)
    assert stats.total_updates == 1
    assert stats.last_queue_size == 3
    assert stats.average_dispatch_ms == 12.5


def test_format_duration() -> None:
    assert format_duration(59) == "59s"
    assert format_duration(61) == "1m 1s"


def test_safe_eval_basic() -> None:
    assert safe_eval("10 / 2") == 5.0
