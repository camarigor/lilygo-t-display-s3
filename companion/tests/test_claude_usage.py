"""Tests for claude_usage poller."""
from claude_usage import (
    aggregate_session,
    compute_rate_bucket,
    parse_transcript_tokens,
)


def test_compute_rate_bucket_thresholds():
    assert compute_rate_bucket(0) == "idle"
    assert compute_rate_bucket(50) == "idle"
    assert compute_rate_bucket(500) == "low"
    assert compute_rate_bucket(1500) == "low"
    assert compute_rate_bucket(3000) == "medium"
    assert compute_rate_bucket(7000) == "high"


def test_parse_transcript_tokens(tmp_path):
    f = tmp_path / "transcript.jsonl"
    f.write_text(
        '{"type":"user","tokens_in":100,"tokens_out":0}\n'
        '{"type":"assistant","tokens_in":0,"tokens_out":2000,"model":"claude-opus-4-7"}\n'
        '{"type":"user","tokens_in":50,"tokens_out":0}\n'
    )
    total, model = parse_transcript_tokens(f)
    assert total == 2150
    assert model == "claude-opus-4-7"


def test_parse_transcript_missing_returns_zero(tmp_path):
    f = tmp_path / "nonexistent.jsonl"
    total, model = parse_transcript_tokens(f)
    assert total == 0
    assert model == ""


def test_aggregate_session_with_one_dir(tmp_path):
    proj = tmp_path / "session-1"
    proj.mkdir()
    (proj / "transcript.jsonl").write_text(
        '{"type":"assistant","tokens_in":0,"tokens_out":5000,"model":"claude-opus-4-7"}\n'
    )
    result = aggregate_session(tmp_path)
    assert result["tokens_used"] == 5000
    assert result["model"] == "claude-opus-4-7"


def test_aggregate_session_empty_dir(tmp_path):
    result = aggregate_session(tmp_path)
    assert result["tokens_used"] == 0
    assert result["model"] == ""
