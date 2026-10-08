"""Split the Bulgarian working file into review batches for the QA audit.

Each batch is a small JSON document an auditor can read on its own, so the
review never has to load all 1155 rows at once. The row index `i` is preserved
and is the id every finding refers back to.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("working/Game.bg.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("qa/batches"))
    parser.add_argument("--size", type=int, default=55)
    args = parser.parse_args()

    rows = json.loads(args.input.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    batch_count = 0
    for start in range(0, len(rows), args.size):
        chunk = rows[start : start + args.size]
        batch_count += 1
        payload = {
            "batch": f"{batch_count:02d}",
            "range": [start, start + len(chunk) - 1],
            "rows": [
                {
                    "i": start + offset,
                    "key": row["key"],
                    "en": row["source"],
                    "bg": row["target"],
                }
                for offset, row in enumerate(chunk)
            ],
        }
        path = args.out_dir / f"batch-{batch_count:02d}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        total += len(chunk)

    print(f"Wrote {batch_count} batches covering {total} rows to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
