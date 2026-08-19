#!/usr/bin/env python3
"""Run the SCOUT-015 evaluation harness and write eval/report.md."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.harness import run_evaluation


def main() -> None:
    summary = run_evaluation(report_path=Path(__file__).resolve().parent / "report.md")
    print(f"Wrote report to {summary['report_path']}")
    print(f"Mode 1 compliance: {summary['mode1_compliance_pct']}%")
    print(f"Schema validity: {summary['schema_validity_pct']}%")
    print(f"Provenance correctness: {summary['provenance_correctness_pct']}%")
    print(f"Cap adherence: {summary['cap_adherence_pct']}%")
    print(f"p50 latency (local, in-process): {summary['p50_latency_ms']:.2f} ms")
    if summary["mode1_failures"]:
        print("Mode 1 failures detected — see report for fixture ids.")


if __name__ == "__main__":
    main()
