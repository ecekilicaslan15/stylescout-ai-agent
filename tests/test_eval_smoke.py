"""Smoke test for the SCOUT-015 evaluation harness."""

from pathlib import Path

from eval.harness import load_fixtures, run_evaluation


def test_eval_fixtures_count_is_in_backlog_range():
    fixtures = load_fixtures()
    assert 20 <= len(fixtures) <= 40


def test_eval_harness_runs_end_to_end(tmp_path):
    report_path = tmp_path / "report.md"
    summary = run_evaluation(report_path=report_path, storage_dir=tmp_path / "scratch")

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "local, in-process" in content
    assert "Mode 1 compliance" in content
    assert summary["fixture_count"] >= 20
    assert "p50_latency_ms" in summary
    assert summary["latency_label"].startswith("local, in-process")
