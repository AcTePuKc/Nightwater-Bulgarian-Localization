"""Create a Bulgarian translation draft using a local Ollama model.

The script never changes the input JSON. It writes a separate output file and
returns only key/target pairs from the model, then merges them into a copy of
the source working file.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import requests


OLLAMA_URL = "http://127.0.0.1:11434/api/chat"


def load_rows(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Input must be a JSON list")
    return data


def extract_json(text: str) -> list[dict[str, str]]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    value = json.loads(text)
    if not isinstance(value, list):
        raise ValueError("Model response must be a JSON array")
    result = []
    for item in value:
        if not isinstance(item, dict) or "key" not in item or "target" not in item:
            raise ValueError("Each model response item must contain key and target")
        result.append({"key": str(item["key"]), "target": str(item["target"])})
    return result


def translate_batch(
    rows: list[dict[str, str]],
    bosnian: dict[str, str],
    model: str,
    timeout: int,
) -> dict[str, str]:
    payload_rows = []
    for row in rows:
        payload_rows.append(
            {
                "key": row["key"],
                "english": row["source"],
                "bosnian_hint": bosnian.get(row["key"], ""),
            }
        )

    prompt = (
        "Преведи дадените игрови текстове от английски на естествен български. "
        "Това е локализация на игра: използвай кратки и ясни UI формулировки, "
        "а за сюжетните реплики запази тона. Полето bosnian_hint е само помощна "
        "референция и не трябва да се копира механично. Запази абсолютно точно "
        "всички плейсхолдъри като {Amount}, {AoERange}, {BerserkDuration}, "
        "скоби, тагове, caret-и и смислени нови редове. Върни само един JSON "
        "обект, в който ключовете са key, а стойностите са българските преводи. "
        "Не добавяй markdown или обяснения.\n\n"
        + json.dumps(payload_rows, ensure_ascii=False)
    )

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "stream": False,
            "format": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "target": {"type": "string"},
                    },
                    "required": ["key", "target"],
                },
            },
            "options": {"temperature": 0.15},
            "messages": [
                {
                    "role": "system",
                    "content": "Ти си професионален български локализатор на видеоигри.",
                },
                {"role": "user", "content": prompt},
            ],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    pairs = extract_json(body["message"]["content"])
    return {item["key"]: item["target"] for item in pairs}


def translate_resilient(
    rows: list[dict[str, str]],
    bosnian: dict[str, str],
    model: str,
    timeout: int,
) -> dict[str, str]:
    """Retry incomplete model output with smaller batches."""
    result = translate_batch(rows, bosnian, model, timeout)
    missing = {row["key"] for row in rows} - result.keys()
    if not missing:
        return result
    if len(rows) == 1:
        raise ValueError(f"Model omitted key {rows[0]['key']}")
    midpoint = max(1, len(rows) // 2)
    left = translate_resilient(rows[:midpoint], bosnian, model, timeout)
    right = translate_resilient(rows[midpoint:], bosnian, model, timeout)
    return left | right


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reference-bs", type=Path)
    parser.add_argument("--model", default="foundry-bg-bggpt:latest")
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    rows = load_rows(args.input)
    reference = {}
    if args.reference_bs and args.reference_bs.exists():
        for row in load_rows(args.reference_bs):
            reference[row["key"]] = row.get("source", "")

    end = len(rows) if args.limit is None else min(len(rows), args.start + args.limit)
    selected = rows[args.start:end]
    translations: dict[str, str] = {}
    output_rows = load_rows(args.output) if args.output.exists() else load_rows(args.input)

    def save_output() -> None:
        for output_row in output_rows:
            if output_row["key"] in translations:
                output_row["target"] = translations[output_row["key"]]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(output_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    for offset in range(0, len(selected), args.batch_size):
        batch = selected[offset : offset + args.batch_size]
        print(
            f"Translating {args.start + offset + 1}-{args.start + offset + len(batch)} "
            f"of {len(rows)}...",
            flush=True,
        )
        result = translate_resilient(batch, reference, args.model, args.timeout)
        expected = {row["key"] for row in batch}
        missing = expected - result.keys()
        if missing:
            raise ValueError(f"Model omitted {len(missing)} keys in batch")
        translations.update({key: result[key] for key in expected})
        save_output()
    print(f"Wrote {len(translations)} translations to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
