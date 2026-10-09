from __future__ import annotations

import argparse
import copy
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge selected Unicode glyphs from a donor font into a base font. "
            "Existing base glyphs win, so Latin artwork stays unchanged."
        )
    )
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--donor", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--ranges",
        nargs="+",
        default=["0400-052F"],
        help="Unicode ranges to import, for example 0400-052F 1C80-1C8A.",
    )
    parser.add_argument(
        "--family-name",
        default="",
        help="Rename the merged font family to avoid a reserved name in a modified font.",
    )
    return parser.parse_args()


def parse_ranges(values: list[str]) -> set[int]:
    codepoints: set[int] = set()
    for value in values:
        if "-" in value:
            start, end = value.split("-", 1)
            codepoints.update(range(int(start, 16), int(end, 16) + 1))
        else:
            codepoints.add(int(value, 16))
    return codepoints


def subset_donor(path: Path, codepoints: set[int]) -> TTFont:
    donor = TTFont(str(path), recalcBBoxes=False, recalcTimestamp=False)
    options = Options()
    options.retain_gids = True
    options.notdef_glyph = True
    options.recommended_glyphs = True
    subsetter = Subsetter(options=options)
    subsetter.populate(unicodes=codepoints)
    subsetter.subset(donor)
    return donor


def graft_missing_glyphs(base: TTFont, donor: TTFont) -> None:
    """Copy donor glyphs without replacing anything already in the base font."""
    base_order = list(base.getGlyphOrder())
    donor_order = donor.getGlyphOrder()

    if "glyf" not in base or "glyf" not in donor:
        raise RuntimeError("This prototype merger currently requires TrueType glyf tables")

    for glyph_name in donor_order:
        if glyph_name in base["glyf"]:
            continue
        base["glyf"][glyph_name] = copy.deepcopy(donor["glyf"][glyph_name])
        base["hmtx"].metrics[glyph_name] = donor["hmtx"].metrics[glyph_name]
        if "vmtx" in base and "vmtx" in donor and glyph_name in donor["vmtx"].metrics:
            base["vmtx"].metrics[glyph_name] = donor["vmtx"].metrics[glyph_name]
        base_order.append(glyph_name)

    base.setGlyphOrder(base_order)

    base_cmaps = [table.cmap for table in base["cmap"].tables if hasattr(table, "cmap")]
    donor_cmaps = [table.cmap for table in donor["cmap"].tables if hasattr(table, "cmap")]
    donor_mapping: dict[int, str] = {}
    for cmap in donor_cmaps:
        for codepoint, glyph_name in cmap.items():
            donor_mapping.setdefault(codepoint, glyph_name)

    for cmap in base_cmaps:
        for codepoint, glyph_name in donor_mapping.items():
            if codepoint not in cmap:
                cmap[codepoint] = glyph_name


def rename_font_family(font: TTFont, family_name: str) -> None:
    """Rename the public family/full/PostScript names of a modified font."""
    name_table = font["name"]
    replacements = {
        1: family_name,
        4: family_name,
        6: "".join(ch for ch in family_name if ch.isalnum()) + "-Regular",
    }
    for record in name_table.names:
        if record.nameID not in replacements:
            continue
        value = replacements[record.nameID]
        if record.platformID == 1:
            record.string = value.encode("mac_roman", errors="replace")
        else:
            record.string = value.encode("utf-16-be")


def main() -> None:
    args = parse_args()
    if not args.base.is_file():
        raise FileNotFoundError(args.base)
    if not args.donor.is_file():
        raise FileNotFoundError(args.donor)

    codepoints = parse_ranges(args.ranges)
    donor = subset_donor(args.donor, codepoints)
    base = TTFont(str(args.base), recalcBBoxes=False, recalcTimestamp=False)
    scale_upem(donor, base["head"].unitsPerEm)

    merged = base
    graft_missing_glyphs(merged, donor)
    if args.family_name:
        rename_font_family(merged, args.family_name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.save(str(args.output))

    merged_check = TTFont(str(args.output), recalcBBoxes=False, recalcTimestamp=False)
    cmap = set().union(*(table.cmap.keys() for table in merged_check["cmap"].tables))
    missing = sorted(codepoint for codepoint in codepoints if codepoint not in cmap)
    if missing:
        raise RuntimeError(
            "Merged font is still missing: "
            + ", ".join(f"U+{codepoint:04X}" for codepoint in missing[:20])
        )

    print(f"output={args.output}")
    print(f"glyphs={len(cmap)}")
    print(f"imported_range_count={len(codepoints)}")


if __name__ == "__main__":
    main()
