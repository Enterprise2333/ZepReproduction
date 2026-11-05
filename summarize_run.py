"""Rebuild a run's summaries from its immutable per-question predictions."""

import argparse
import csv
import json
from pathlib import Path

from evaluate import summarize


def refresh(run_dir: Path):
    rows = [json.loads(line) for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    summary = summarize(rows)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (run_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print(run_dir, "questions:", len(rows) // 3, "errors:", sum("error" in x for x in rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    refresh(parser.parse_args().run_dir)

