#!/usr/bin/env python3
"""
export_xlsx.py — assemble the tracker CSVs for a case into a single formatted
Excel workbook: one worksheet per entity/defendant plus a "Master" rollup,
bold header rows, matching the look of a hand-built multi-tab tracker.

This reads master.csv (the source of truth already produced by csv_writer.py)
rather than the individual per-entity CSVs, so it always reflects whatever
the CSVs currently say — including verification status. It does not do any
merge/dedupe logic itself; that all already happened when the CSVs were
written. This script is presentation only.

If a *_review_needed.csv file (or files) exist in the output directory, their
contents are combined into a "Review Needed" sheet too, so open conflicts are
visible in the same workbook rather than a separate file someone has to
remember to check.

Entity display names are auto-shortened into worksheet tab names, since Excel
limits sheet names to 31 characters and full legal entity names ("Example
Holdings Company of North America, Inc.") don't fit. This is a mechanical heuristic
(strip common corporate suffixes, trim to fit, disambiguate collisions) —
it will not reliably reproduce the short names a human would choose by hand
(e.g. distinguishing two related-but-different entities isn't something a
generic algorithm can know). Treat the generated names as a reasonable
starting point, not a final answer — rename tabs in Excel afterward if they
don't read well.

Usage:
    python export_xlsx.py --output-dir ./output --xlsx-path ./tracker.xlsx
"""
import argparse
import csv
import glob
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

HEADER_FONT = Font(bold=True)
HEADER_ALIGN = Alignment(vertical="top", wrap_text=True)
CELL_ALIGN = Alignment(vertical="top", wrap_text=True)
MAX_SHEET_NAME_LEN = 31
INVALID_SHEET_CHARS = re.compile(r"[\[\]:*?/\\]")

# Corporate suffixes / filler words stripped when auto-shortening an entity
# name for a tab. Ordered longest-first so e.g. "L.L.C." is stripped before "LLC".
SUFFIXES = [
    ", incorporated", " incorporated",
    ", corporation", " corporation",
    ", l.l.c.", " l.l.c.",
    ", llc", " llc",
    ", inc.", " inc.", ", inc", " inc",
    ", corp.", " corp.", ", corp", " corp",
    ", co.", " co.",
    ", ltd.", " ltd.", ", ltd", " ltd",
    ", p.a.", " p.a.",
    ", p.c.", " p.c.",
]


def shorten_entity_name(name: str, taken: set) -> str:
    """Auto-generate a short, Excel-safe, unique worksheet tab name."""
    short = name.strip()
    lowered = short.lower()
    for suffix in SUFFIXES:
        if lowered.endswith(suffix):
            short = short[: len(short) - len(suffix)]
            lowered = short.lower()
    short = INVALID_SHEET_CHARS.sub("", short).strip()
    if not short:
        short = "Entity"
    if len(short) > MAX_SHEET_NAME_LEN:
        short = short[:MAX_SHEET_NAME_LEN].rsplit(" ", 1)[0] or short[:MAX_SHEET_NAME_LEN]

    candidate = short
    n = 2
    while candidate.lower() in taken or candidate.lower() == "master":
        suffix = f" ({n})"
        candidate = short[: MAX_SHEET_NAME_LEN - len(suffix)] + suffix
        n += 1
    taken.add(candidate.lower())
    return candidate


def read_csv(path: Path):
    if not path.exists():
        return [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    return rows, fieldnames


def write_sheet(wb, title: str, fieldnames, rows):
    ws = wb.create_sheet(title=title)
    ws.append(fieldnames)
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN
    for row in rows:
        ws.append([row.get(col, "") for col in fieldnames])
        for cell in ws[ws.max_row]:
            cell.alignment = CELL_ALIGN
    ws.freeze_panes = "A2"
    # enable the header dropdown arrows (Excel AutoFilter) so columns like
    # Set, Discovery Type, Follow-Up Needed?, etc. can be filtered/sorted
    # directly, even on an empty sheet (0 data rows still gets a filterable header)
    last_col_letter = get_column_letter(len(fieldnames))
    ws.auto_filter.ref = f"A1:{last_col_letter}{max(ws.max_row, 1)}"
    # reasonable default column widths, capped so nothing runs off-screen
    for i, col in enumerate(fieldnames, start=1):
        header_len = len(col)
        sample_len = max((len(str(r.get(col, ""))) for r in rows), default=0)
        width = min(max(header_len, min(sample_len, 60)) + 2, 60)
        ws.column_dimensions[get_column_letter(i)].width = width
    return ws


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--xlsx-path", type=Path, required=True)
    args = parser.parse_args()

    master_rows, master_fields = read_csv(args.output_dir / "master.csv")
    if not master_fields:
        raise SystemExit(f"No master.csv found in {args.output_dir} — run csv_writer.py first.")

    wb = Workbook()
    wb.remove(wb.active)  # drop the default blank sheet

    # Master sheet first
    write_sheet(wb, "Master", master_fields, master_rows)

    # One sheet per entity, in the order entities first appear in master.csv
    per_entity_fields = [c for c in master_fields if c != "Entity"]
    seen_entities = []
    for r in master_rows:
        ent = r.get("Entity", "")
        if ent and ent not in seen_entities:
            seen_entities.append(ent)

    taken_names = set()
    for entity in seen_entities:
        tab_name = shorten_entity_name(entity, taken_names)
        entity_rows = [r for r in master_rows if r.get("Entity", "") == entity]
        write_sheet(wb, tab_name, per_entity_fields, entity_rows)

    # Review-needed sheet, if any conflicts are outstanding
    review_files = sorted(glob.glob(str(args.output_dir / "*_review_needed.csv")))
    if review_files:
        review_fields = None
        review_rows = []
        for rf in review_files:
            rows, fields = read_csv(Path(rf))
            if fields and review_fields is None:
                review_fields = fields
            review_rows.extend(rows)
        if review_fields:
            write_sheet(wb, "Review Needed", review_fields, review_rows)

    args.xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(args.xlsx_path)
    print(f"Wrote {args.xlsx_path} with sheets: {', '.join(ws.title for ws in wb.worksheets)}")


if __name__ == "__main__":
    main()
