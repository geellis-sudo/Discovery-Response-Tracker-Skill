#!/usr/bin/env python3
"""
csv_writer.py — merge newly-extracted discovery rows into the tracker CSVs
without clobbering anything.

Given a JSON file of rows (schema: see references/field_definitions.md in the
skill), this writes/updates:
  - <output-dir>/<entity-slug>.csv       (one per entity, no Entity column)
  - <output-dir>/master.csv               (all entities, with an Entity column)
  - <output-dir>/<entity-slug>_review_needed.csv   (conflicts only, if any)

Dedupe key: (entity, discovery_type, set, request_no).
  - New key                -> appended, Verification Status = unverified.
  - Existing key, same substantive content -> left untouched.
  - Existing key, different substantive content -> NOT overwritten. The new
    version is appended to the entity's _review_needed.csv (old vs new side
    by side) for a human to resolve.

Usage:
    python csv_writer.py --rows rows.json --output-dir ./output
"""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

COLUMNS = [
    "Discovery Type",
    "Set",
    "Request No.",
    "Request Topic",
    "Topic Category",
    "Objections",
    "Objection Type",
    "Response Summary",
    "Documents Referenced",
    "Follow-Up Needed?",
    "Follow-Up Rationale",
    "Notes",
    "Source Files",
    "Source Locator",
    "Request Text Source",
    "Verification Status",
    "Verified By",
    "Verified Date",
]
MASTER_COLUMNS = ["Entity"] + COLUMNS

# Topic Category and Objection Type are short, controlled-vocabulary columns
# whose entire purpose is filtering (see references/field_definitions.md) --
# they're derived from request_topic/objections respectively, so a change to
# either underlying field should be treated as substantive too.
SUBSTANTIVE_FIELDS = [
    "request_topic",
    "topic_category",
    "objections",
    "objection_type",
    "response_summary",
    "documents_referenced",
    "follow_up_needed",
    "follow_up_rationale",
    "notes",
]

FIELD_TO_COLUMN = {
    "discovery_type": "Discovery Type",
    "set": "Set",
    "request_no": "Request No.",
    "request_topic": "Request Topic",
    "topic_category": "Topic Category",
    "objections": "Objections",
    "objection_type": "Objection Type",
    "response_summary": "Response Summary",
    "documents_referenced": "Documents Referenced",
    "follow_up_needed": "Follow-Up Needed?",
    "follow_up_rationale": "Follow-Up Rationale",
    "notes": "Notes",
    "source_files": "Source Files",
    "source_locator": "Source Locator",
    "request_text_source": "Request Text Source",
}


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip()).strip("_").lower()
    return slug or "entity"


def content_hash(row: dict) -> str:
    payload = {k: str(row.get(k, "")).strip() for k in SUBSTANTIVE_FIELDS}
    blob = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def row_key(row: dict) -> tuple:
    return (row["discovery_type"], row["set"], str(row["request_no"]))


def read_csv_as_dict(path: Path, columns) -> dict:
    """Returns {row_key: dict-of-columns} keyed by (Discovery Type, Set, Request No.)."""
    out = {}
    if not path.exists():
        return out
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            key = (r.get("Discovery Type", ""), r.get("Set", ""), r.get("Request No.", ""))
            out[key] = r
    return out


def write_csv(path: Path, columns, rows_by_key: dict):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows_by_key.values():
            writer.writerow({c: row.get(c, "") for c in columns})


def to_row_dict(row: dict) -> dict:
    d = {FIELD_TO_COLUMN[k]: row.get(k, "") for k in FIELD_TO_COLUMN}
    d["Verification Status"] = "unverified"
    d["Verified By"] = ""
    d["Verified Date"] = ""
    return d


def existing_row_content_hash(existing_row: dict) -> str:
    reverse = {v: k for k, v in FIELD_TO_COLUMN.items()}
    payload = {}
    for col, field in reverse.items():
        if field in SUBSTANTIVE_FIELDS:
            payload[field] = str(existing_row.get(col, "")).strip()
    blob = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, required=True, help="JSON file: list of row dicts")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = json.loads(args.rows.read_text())
    if not isinstance(rows, list):
        raise SystemExit("--rows file must contain a JSON list of row objects")

    by_entity = {}
    for row in rows:
        by_entity.setdefault(row["entity"], []).append(row)

    added, unchanged, conflicts = 0, 0, 0
    master_path = args.output_dir / "master.csv"
    master_rows = read_csv_as_dict(master_path, MASTER_COLUMNS)
    # master keyed by (entity, discovery_type, set, request_no) since it spans entities
    master_by_key = {}
    if master_path.exists():
        with open(master_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                k = (r.get("Entity", ""), r.get("Discovery Type", ""), r.get("Set", ""), r.get("Request No.", ""))
                master_by_key[k] = r

    for entity, entity_rows in by_entity.items():
        slug = slugify(entity)
        entity_csv = args.output_dir / f"{slug}.csv"
        review_csv = args.output_dir / f"{slug}_review_needed.csv"

        existing = read_csv_as_dict(entity_csv, COLUMNS)
        review_entries = []
        if review_csv.exists():
            with open(review_csv, newline="", encoding="utf-8") as f:
                review_entries = list(csv.DictReader(f))

        for row in entity_rows:
            key = row_key(row)
            new_hash = content_hash(row)

            if key not in existing:
                existing[key] = to_row_dict(row)
                master_by_key[(entity,) + key] = {"Entity": entity, **existing[key]}
                added += 1
                continue

            old_hash = existing_row_content_hash(existing[key])
            if old_hash == new_hash:
                unchanged += 1
                continue

            # conflict: don't overwrite, log for human review
            conflicts += 1
            new_row_dict = to_row_dict(row)
            review_entries.append(
                {
                    "Discovery Type": key[0],
                    "Set": key[1],
                    "Request No.": key[2],
                    "Old Response Summary": existing[key].get("Response Summary", ""),
                    "New Response Summary": new_row_dict.get("Response Summary", ""),
                    "Old Objections": existing[key].get("Objections", ""),
                    "New Objections": new_row_dict.get("Objections", ""),
                    "New Source Files": new_row_dict.get("Source Files", ""),
                }
            )

        write_csv(entity_csv, COLUMNS, existing)
        if review_entries:
            review_columns = [
                "Discovery Type",
                "Set",
                "Request No.",
                "Old Response Summary",
                "New Response Summary",
                "Old Objections",
                "New Objections",
                "New Source Files",
            ]
            with open(review_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=review_columns)
                writer.writeheader()
                writer.writerows(review_entries)

    write_csv(master_path, MASTER_COLUMNS, master_by_key)

    print(f"Added: {added}  Unchanged: {unchanged}  Flagged for review (not overwritten): {conflicts}")
    if conflicts:
        print("See *_review_needed.csv for conflicting rows that need a human decision.")


if __name__ == "__main__":
    main()
