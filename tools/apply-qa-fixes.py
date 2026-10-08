"""Apply the QA audit findings to the Bulgarian working file.

Every suggestion is validated before it is written: a fix that would break a
placeholder, a rich-text tag or the newline layout is rejected instead of
applied. One suggestion per row is taken (highest severity, then the category
that changes meaning most), and every skipped finding is recorded so nothing
disappears silently.

The result is written to working/Game.bg.json, with:
  qa/applied-fixes.json     what was applied and what was skipped
  qa/remaining-findings.json findings that were not applied

A curated map (qa/curated-fixes.json) is applied last and overrides both, for
the terminology decisions that no single finding can express.
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import re
from pathlib import Path

WORKING = Path("working/Game.bg.json")
FINDINGS_GLOB = "qa/findings/batch-*.json"
CURATED = Path("qa/curated-fixes.json")
APPLIED = Path("qa/applied-fixes.json")
REMAINING = Path("qa/remaining-findings.json")

SEVERITY_RANK = {"critical": 0, "major": 1, "minor": 2}
CATEGORY_RANK = {
    "untranslated": 0,
    "foreign": 1,
    "mistranslation": 2,
    "terminology": 3,
    "consistency": 4,
    "grammar": 5,
    "style": 6,
    "length": 7,
}

PLACEHOLDER = re.compile(r"\{[^{}]*\}")
TAG = re.compile(r"<[^<>]*>")
CYRILLIC = re.compile(r"[\u0400-\u04FF]")
ASCII_LETTER = re.compile(r"[A-Za-z]")


def validate(source: str, current: str, suggestion: str) -> str | None:
    """Return a rejection reason, or None when the suggestion is safe."""
    if not suggestion.strip():
        return "празно предложение"
    if suggestion == current:
        return "предложението е идентично с текущия превод"
    if sorted(PLACEHOLDER.findall(source)) != sorted(PLACEHOLDER.findall(suggestion)):
        return "счупени плейсхолдъри"
    if sorted(TAG.findall(source)) != sorted(TAG.findall(suggestion)):
        return "счупени rich-text тагове"
    if source.count("\n") != suggestion.count("\n"):
        return "различен брой нови редове"
    if ASCII_LETTER.search(source) and not CYRILLIC.search(suggestion):
        return "предложението не съдържа кирилица"
    if len(suggestion) > 2.5 * len(source) + 20:
        return "предложението е неоправдано дълго"
    return None


def load_findings(rows: list[dict]) -> list[dict]:
    findings = []
    for path in sorted(glob.glob(FINDINGS_GLOB)):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        for item in payload.get("findings", []):
            index = item.get("i")
            if not isinstance(index, int) or not 0 <= index < len(rows):
                continue
            findings.append(
                {
                    "i": index,
                    "severity": item.get("severity", "minor"),
                    "category": item.get("category", "style"),
                    "issue": str(item.get("issue", "")).strip(),
                    "suggestion": str(item.get("suggestion", "")).strip(),
                    "batch": payload.get("batch", ""),
                }
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input", type=Path, default=WORKING)
    args = parser.parse_args()

    rows = json.loads(args.input.read_text(encoding="utf-8"))
    findings = load_findings(rows)

    by_index: dict[int, list[dict]] = collections.defaultdict(list)
    for finding in findings:
        by_index[finding["i"]].append(finding)

    applied, skipped = [], []
    for index in sorted(by_index):
        candidates = sorted(
            by_index[index],
            key=lambda f: (SEVERITY_RANK.get(f["severity"], 3), CATEGORY_RANK.get(f["category"], 9)),
        )
        source, current = rows[index]["source"], rows[index]["target"]
        chosen = None
        for candidate in candidates:
            if chosen is None:
                reason = validate(source, current, candidate["suggestion"])
                if reason is None:
                    chosen = candidate
                    continue
                skipped.append({**candidate, "reason": reason})
            else:
                skipped.append({**candidate, "reason": "редът вече е поправен от по-приоритетна находка"})
        if chosen is None:
            continue
        rows[index]["target"] = chosen["suggestion"]
        applied.append(
            {
                "i": index,
                "key": rows[index]["key"],
                "severity": chosen["severity"],
                "category": chosen["category"],
                "en": source,
                "old": current,
                "new": chosen["suggestion"],
                "issue": chosen["issue"],
            }
        )

    curated_applied = []
    if CURATED.exists():
        curated = json.loads(CURATED.read_text(encoding="utf-8"))
        for entry in curated:
            index = entry.get("index")
            if index is None and "key" in entry:
                match = [i for i, r in enumerate(rows) if r["key"] == entry["key"]]
                index = match[0] if match else None
            if index is None or not 0 <= index < len(rows):
                raise SystemExit(f"Curated fix does not match any row: {entry}")
            old = rows[index]["target"]
            if old == entry["target"]:
                continue
            reason = validate(rows[index]["source"], old, entry["target"])
            if reason is not None:
                raise SystemExit(f"Curated fix for row {index} is invalid ({reason}): {entry}")
            rows[index]["target"] = entry["target"]
            curated_applied.append(
                {
                    "i": index,
                    "key": rows[index]["key"],
                    "severity": "curated",
                    "category": entry.get("category", "terminology"),
                    "en": rows[index]["source"],
                    "old": old,
                    "new": entry["target"],
                    "issue": entry.get("reason", ""),
                }
            )

    changes = applied + curated_applied
    print(f"Rows: {len(rows)}")
    print(f"Findings read: {len(findings)} across {len(by_index)} rows")
    print(f"Applied from findings: {len(applied)}")
    print(f"Applied from curated map: {len(curated_applied)}")
    print(f"Skipped findings: {len(skipped)}")
    print(f"Rows changed in total: {len({c['i'] for c in changes})}")

    reasons = collections.Counter(s["reason"] for s in skipped)
    for reason, count in reasons.most_common():
        print(f"   skipped: {reason} — {count}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    args.input.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    APPLIED.write_text(
        json.dumps(changes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REMAINING.write_text(
        json.dumps(skipped, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nWrote {args.input}")
    print(f"Wrote {APPLIED} and {REMAINING}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
