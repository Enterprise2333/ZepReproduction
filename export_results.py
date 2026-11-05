"""Export compact public result tables without copied benchmark conversations."""

import csv
import json
from pathlib import Path

from runtime import ROOT

RUNS = {
    "synthetic-trial1": "20261105-100527-synthetic",
    "synthetic-trial2": "20261105-102247-synthetic",
    "synthetic-trial3": "20261105-103305-synthetic",
    "longmemeval": "20261105-101232-longmemeval",
}
FIELDS = [
    "suite", "case_id", "question_type", "method", "question", "gold", "prediction",
    "correct", "retrieved_facts", "input_tokens", "latency_s",
]


def main():
    out = ROOT / "artifacts"
    out.mkdir(exist_ok=True)
    for name, run_id in RUNS.items():
        rows = [json.loads(line) for line in (ROOT / "results" / run_id / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
        with (out / f"{name}-predictions.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows({key: row.get(key) for key in FIELDS} for row in rows)
        print(name, len(rows))


if __name__ == "__main__":
    main()

