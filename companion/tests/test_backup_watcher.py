"""Tests for backup_watcher: parser rsync log + batch detection."""
from pathlib import Path

from backup_watcher import BatchAggregator, RsyncEvent, parse_log_line


def test_parse_line_building_file_list():
    line = "2026/05/15 13:30:00 [953001] building file list"
    ev = parse_log_line(line)
    assert ev is not None
    assert ev.kind == "start"
    assert ev.pid == "953001"
    assert ev.ts == "2026/05/15 13:30:00"


def test_parse_line_total_size_ok():
    line = "2026/05/15 13:30:01 [953001] total size is 1.00M  speedup is 6,666.67"
    ev = parse_log_line(line)
    assert ev is not None
    assert ev.kind == "ok"
    assert ev.pid == "953001"


def test_parse_line_error():
    line = (
        "2026/05/15 13:30:04 [953004] rsync error: some files/attrs were not transferred "
        "(see previous errors) (code 23) at main.c(1338) [sender=3.2.7]"
    )
    ev = parse_log_line(line)
    assert ev is not None
    assert ev.kind == "error"
    assert ev.pid == "953004"
    assert ev.error_code == 23


def test_parse_line_unrelated():
    assert parse_log_line("random text") is None
    assert parse_log_line(
        "2026/05/15 13:30:00 [953001] sent 100 bytes received 50 bytes"
    ) is None


def test_batch_aggregator_collects_5_ok():
    agg = BatchAggregator(batch_size=5, idle_seconds=999)
    fixture = Path(__file__).parent / "fixtures" / "backup_log_18_ok.txt"
    for line in fixture.read_text().splitlines():
        ev = parse_log_line(line)
        if ev:
            agg.process(ev, now_ts=1715798400)
    summary = agg.close()
    assert summary is not None
    assert summary["rsyncs_total"] == 5
    assert summary["rsyncs_ok"] == 5
    assert summary["rsyncs_error"] == 0


def test_batch_aggregator_with_errors():
    agg = BatchAggregator(batch_size=5, idle_seconds=999)
    fixture = Path(__file__).parent / "fixtures" / "backup_log_with_errors.txt"
    for line in fixture.read_text().splitlines():
        ev = parse_log_line(line)
        if ev:
            agg.process(ev, now_ts=1715798400)
    summary = agg.close()
    assert summary is not None
    assert summary["rsyncs_total"] == 5
    assert summary["rsyncs_ok"] == 3
    assert summary["rsyncs_error"] == 2
    assert len(summary["errors"]) == 2
    assert summary["errors"][0]["code"] == 23


def test_batch_aggregator_idle_timeout():
    agg = BatchAggregator(batch_size=999, idle_seconds=30)
    agg.process(RsyncEvent(kind="start", pid="1", ts="2026/05/15 13:30:00"), now_ts=1715798400)
    agg.process(RsyncEvent(kind="ok", pid="1", ts="2026/05/15 13:30:01"), now_ts=1715798405)
    summary = agg.maybe_close(now_ts=1715798450)
    assert summary is not None
    assert summary["rsyncs_total"] == 1
