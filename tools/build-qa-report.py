"""Build the QA audit report for the Bulgarian translation.

Combines two independent passes:

1. deterministic checks over every row (placeholders, tags, newlines, script,
   diacritics, reused targets, terminology variants);
2. the editorial findings written by the review agents into qa/findings/.

The result is written to qa/translation-audit.md.
"""

from __future__ import annotations

import collections
import glob
import json
import re
from pathlib import Path

WORKING = Path("working/Game.bg.json")
FINDINGS_GLOB = "qa/findings/batch-*.json"
REPORT = Path("qa/translation-audit.md")

SEVERITY_ORDER = ["critical", "major", "minor"]
SEVERITY_BG = {"critical": "Критични", "major": "Сериозни", "minor": "Дребни"}
CATEGORY_BG = {
    "untranslated": "непреведен текст",
    "foreign": "чужд език",
    "mistranslation": "грешен превод",
    "terminology": "терминология",
    "consistency": "несъответствие",
    "grammar": "граматика",
    "style": "стил",
    "length": "дължина за UI",
}

CYRILLIC = re.compile(r"[\u0400-\u04FF]")
LATIN = re.compile(r"[A-Za-z]")
PLACEHOLDER = re.compile(r"\{[^{}]*\}")
TAG = re.compile(r"<[^<>]*>")
DIACRITICS = re.compile(r"[čćžšđ]")

TERM_PROBES = {
    "Milestone": ["етап", "постижен", "междинна цел", "преметниц"],
    "Dark Thicket": ["мрачн", "тъмн", "гъсталак", "гъст лес"],
    "run": ["рунд", "бягане"],
    "Harvester": ["автоматичен събирач", "дървосекач", "секач", "фермер"],
}


def md_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", " ⏎ ")
        .replace("\n", " ⏎ ")
    )


def deterministic_checks(rows: list[dict]) -> dict:
    non_cyrillic, diacritic_rows = [], []
    placeholder_bad, tag_bad, newline_bad = [], [], []
    punctuation_bad, dash_label_bad = [], []
    length_outliers: list[tuple[int, int, int, float]] = []
    reused: dict[str, set[str]] = collections.defaultdict(set)

    for index, row in enumerate(rows):
        source, target = row["source"], row["target"]
        if LATIN.search(target) and not CYRILLIC.search(target):
            non_cyrillic.append(index)
        if DIACRITICS.search(target):
            diacritic_rows.append(index)
        if sorted(PLACEHOLDER.findall(source)) != sorted(PLACEHOLDER.findall(target)):
            placeholder_bad.append(index)
        if sorted(TAG.findall(source)) != sorted(TAG.findall(target)):
            tag_bad.append(index)
        if source.count("\n") != target.count("\n"):
            newline_bad.append(index)
        reused[target].add(source)

        stripped_src, stripped_tgt = source.rstrip(), target.rstrip()
        if len(stripped_src) > 3 and len(stripped_tgt) > 3:
            if stripped_src[-1] in ".!?" or stripped_tgt[-1] in ".!?":
                if stripped_src[-1] != stripped_tgt[-1]:
                    punctuation_bad.append(index)

        if source.startswith("- ") and not target.startswith("- "):
            dash_label_bad.append(index)

        if len(source) >= 20:
            ratio = len(target) / len(source)
            if ratio > 1.4:
                length_outliers.append((index, len(source), len(target), ratio))

    length_outliers.sort(key=lambda item: item[3], reverse=True)

    collisions = {
        target: sources
        for target, sources in reused.items()
        if len(sources) > 1 and target.strip()
    }

    term_counts = {
        name: {probe: sum(r["target"].lower().count(probe) for r in rows) for probe in probes}
        for name, probes in TERM_PROBES.items()
    }

    return {
        "non_cyrillic": non_cyrillic,
        "diacritics": diacritic_rows,
        "placeholder_bad": placeholder_bad,
        "tag_bad": tag_bad,
        "newline_bad": newline_bad,
        "punctuation_bad": punctuation_bad,
        "dash_label_bad": dash_label_bad,
        "length_outliers": length_outliers,
        "collisions": collisions,
        "term_counts": term_counts,
    }


def load_findings(rows: list[dict]) -> tuple[list[dict], list[str]]:
    findings, problems = [], []
    for path in sorted(glob.glob(FINDINGS_GLOB)):
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{path}: невалиден JSON ({exc})")
            continue
        batch = payload.get("batch", Path(path).stem)
        for item in payload.get("findings", []):
            index = item.get("i")
            if not isinstance(index, int) or not 0 <= index < len(rows):
                problems.append(f"{path}: находка с невалиден индекс {index!r}")
                continue
            severity = item.get("severity", "minor")
            if severity not in SEVERITY_ORDER:
                severity = "minor"
            findings.append(
                {
                    "batch": batch,
                    "i": index,
                    "key": rows[index]["key"],
                    "en": rows[index]["source"],
                    "bg": rows[index]["target"],
                    "severity": severity,
                    "category": item.get("category", "style"),
                    "issue": str(item.get("issue", "")).strip(),
                    "suggestion": str(item.get("suggestion", "")).strip(),
                }
            )
    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["i"]))
    return findings, problems


def render(rows: list[dict], checks: dict, findings: list[dict], problems: list[str]) -> str:
    out: list[str] = []
    add = out.append

    add("# QA одит на българския превод — Nightwater")
    add("")
    add(f"Обхват: **{len(rows)} реда** от `working/Game.bg.json` (пълен ред-по-ред преглед).")
    add("")
    add("Одитът е само диагностичен — **по превода не са правени промени**.")
    add("")

    add("## 1. Обобщение")
    add("")
    by_severity = collections.Counter(f["severity"] for f in findings)
    by_category = collections.Counter(f["category"] for f in findings)
    add(f"- Реда с находки: **{len({f['i'] for f in findings})}** от {len(rows)}")
    add(f"- Общо находки: **{len(findings)}**")
    for severity in SEVERITY_ORDER:
        add(f"  - {SEVERITY_BG[severity]}: {by_severity.get(severity, 0)}")
    add("")
    if by_category:
        add("| Категория | Брой |")
        add("|---|---|")
        for category, count in by_category.most_common():
            label = CATEGORY_BG.get(category, category)
            add(f"| {label} | {count} |")
        add("")

    add("## 2. Автоматични проверки")
    add("")
    add("| Проверка | Резултат |")
    add("|---|---|")
    add(f"| Плейсхолдъри (`{{...}}`) | {len(checks['placeholder_bad'])} разминавания |")
    add(f"| Rich-text тагове (`<...>`) | {len(checks['tag_bad'])} разминавания |")
    add(f"| Брой нови редове | {len(checks['newline_bad'])} разминавания |")
    add(f"| Редове без кирилица | {len(checks['non_cyrillic'])} |")
    add(f"| Редове с диакритика (č/ć/ž/š/đ) | {len(checks['diacritics'])} |")
    add(f"| Еднакъв превод за различни английски текстове | {len(checks['collisions'])} |")
    add(f"| Разминаване в крайна пунктуация (. ! ?) | {len(checks['punctuation_bad'])} |")
    add(f"| Загубен етикет `- ` в началото | {len(checks['dash_label_bad'])} |")
    add(f"| Превод над 1.4× дължината на източника | {len(checks['length_outliers'])} |")
    add("")

    add("### 2.1 Терминологични варианти")
    add("")
    add("| Термин | Срещания в превода |")
    add("|---|---|")
    for name, counts in checks["term_counts"].items():
        parts = [f"„{probe}“ {count}" for probe, count in counts.items() if count]
        add(f"| {name} | {'; '.join(parts) if parts else '—'} |")
    add("")

    if checks["collisions"]:
        add("### 2.2 Различни английски текстове с еднакъв превод")
        add("")
        add("| Английски | Превод | Редове |")
        add("|---|---|---|")
        index_by_text = {r["source"]: i for i, r in enumerate(rows)}
        for target, sources in sorted(checks["collisions"].items()):
            idx = [str(i) for i, r in enumerate(rows) if r["target"] == target]
            add(
                f"| {' / '.join(sorted(sources))[:120]} | {md_escape(target)[:90]} "
                f"| {', '.join(idx)} |"
            )
        add("")

    if checks["punctuation_bad"]:
        add("### 2.3 Разминаване в крайна пунктуация")
        add("")
        add("| Ред | Английски | Текущ превод |")
        add("|---|---|---|")
        for index in checks["punctuation_bad"]:
            row = rows[index]
            add(f"| {index} | {md_escape(row['source'])[:110]} | {md_escape(row['target'])[:110]} |")
        add("")

    if checks["length_outliers"]:
        add("### 2.4 Подозрителна дължина за UI")
        add("")
        add("Преводът е над 1.4× по-дълъг от английския текст — риск от отрязване в интерфейса.")
        add("")
        add("| Ред | Английски (знаци) | Превод (знаци) | Съотношение | Превод |")
        add("|---|---|---|---|---|")
        for index, src_len, tgt_len, ratio in checks["length_outliers"][:30]:
            row = rows[index]
            add(
                f"| {index} | {src_len} | {tgt_len} | {ratio:.2f}× "
                f"| {md_escape(row['target'])[:110]} |"
            )
        if len(checks["length_outliers"]) > 30:
            add(f"| … | | | | _още {len(checks['length_outliers']) - 30} реда_ |")
        add("")

    if problems:
        add("### 2.5 Проблеми при четене на находките")
        add("")
        for problem in problems:
            add(f"- {problem}")
        add("")

    add("## 3. Находки от редакторския преглед")
    add("")
    if not findings:
        add("_Няма записани находки._")
        add("")
    for severity in SEVERITY_ORDER:
        group = [f for f in findings if f["severity"] == severity]
        if not group:
            continue
        add(f"### 3.{SEVERITY_ORDER.index(severity) + 1} {SEVERITY_BG[severity]} ({len(group)})")
        add("")
        add("| Ред | Английски | Текущ превод | Проблем | Предложение | Категория |")
        add("|---|---|---|---|---|---|")
        for item in group:
            add(
                f"| {item['i']} | {md_escape(item['en'])[:110]} "
                f"| {md_escape(item['bg'])[:110]} | {md_escape(item['issue'])[:220]} "
                f"| {md_escape(item['suggestion'])[:150] or '—'} "
                f"| {CATEGORY_BG.get(item['category'], item['category'])} |"
            )
        add("")

    add("## 4. Ред на поправките")
    add("")
    add("1. Критичните находки — те чупят смисъла или оставят чужд език в играта.")
    add("2. Утвърждаване на предложените термини от `qa/GLOSSARY.md` (раздел 2).")
    add("3. Сериозните находки по утвърдените термини и обръщението.")
    add("4. Дребните стилистични находки — накрая, на един проход.")
    add("")

    return "\n".join(out)


def main() -> int:
    rows = json.loads(WORKING.read_text(encoding="utf-8"))
    checks = deterministic_checks(rows)
    findings, problems = load_findings(rows)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render(rows, checks, findings, problems), encoding="utf-8")

    by_severity = collections.Counter(f["severity"] for f in findings)
    print(f"Report: {REPORT}")
    print(f"Rows: {len(rows)}  Findings: {len(findings)}  Rows with findings: {len({f['i'] for f in findings})}")
    for severity in SEVERITY_ORDER:
        print(f"  {severity}: {by_severity.get(severity, 0)}")
    print(f"Deterministic: no-cyrillic={len(checks['non_cyrillic'])} "
          f"diacritics={len(checks['diacritics'])} collisions={len(checks['collisions'])} "
          f"placeholder={len(checks['placeholder_bad'])} tag={len(checks['tag_bad'])} "
          f"newline={len(checks['newline_bad'])}")
    if problems:
        print(f"Problems: {len(problems)}")
        for problem in problems:
            print("  " + problem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
