#!/usr/bin/env python3
"""
audit_log.py — append-only audit trail + hash-based sign-off verification
for the discovery response tracker.

Subcommands:

  record-source <file> --entity E --discovery-type T --set S --output-dir D
      Hash a source document and log it (does not touch the file itself).

  record-signoff <csv_path> --row-key "entity|discovery_type|set|request_no"
                  --reviewer "Name" --output-dir D
      Hash the row's current substantive content, log reviewer + timestamp +
      hash, and mark the row Verified in the CSV.

  check <csv_path> --output-dir D
      Recompute every row's content hash and compare against the most recent
      sign-off on record for that row. Updates Verification Status in the
      CSV: "verified" (hash matches last sign-off), "stale (edited after
      sign-off)" (hash no longer matches — something changed since sign-off),
      or "unverified" (no sign-off on record).

  export-check <csv_path> --output-dir D
      Same as `check`, but exits non-zero and prints a blocked-rows list if
      anything is not currently "verified" — use before handing a copy of
      the tracker to anyone outside the immediate review process.

The audit log itself (<output-dir>/audit_log.jsonl) is append-only: nothing
is ever rewritten, only added to, so it stays a reliable record even if rows
are edited or reprocessed later.
"""
import argparse
import csv as csv_module
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SUBSTANTIVE_COLUMNS = [
    "Request Topic",
    "Topic Category",
    "Objections",
    "Objection Type",
    "Response Summary",
    "Documents Referenced",
    "Follow-Up Needed?",
    "Follow-Up Rationale",
    "Notes",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def row_content_hash(row: dict) -> str:
    payload = {c: str(row.get(c, "")).strip() for c in SUBSTANTIVE_COLUMNS}
    blob = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def audit_log_path(output_dir: Path) -> Path:
    return output_dir / "audit_log.jsonl"


def append_log(output_dir: Path, entry: dict):
    path = audit_log_path(output_dir)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_log(output_dir: Path) -> list:
    path = audit_log_path(output_dir)
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def row_key_of(row: dict) -> str:
    entity = row.get("Entity", "")
    parts = [entity, row.get("Discovery Type", ""), row.get("Set", ""), row.get("Request No.", "")]
    return "|".join(parts)


def cmd_record_source(args):
    sha = sha256_file(args.file)
    entry = {
        "type": "source",
        "file": str(args.file),
        "sha256": sha,
        "entity": args.entity,
        "discovery_type": args.discovery_type,
        "set": args.set,
        "timestamp": now_iso(),
    }
    append_log(args.output_dir, entry)
    print(f"Logged source: {args.file.name} (sha256 {sha[:12]}...)")


def load_csv_rows(csv_path: Path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv_module.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    return rows, fieldnames


def write_csv_rows(csv_path: Path, fieldnames, rows):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv_module.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def cmd_record_signoff(args):
    rows, fieldnames = load_csv_rows(args.csv_path)
    target = None
    for row in rows:
        if row_key_of(row) == args.row_key or "|".join(
            [row.get("Discovery Type", ""), row.get("Set", ""), row.get("Request No.", "")]
        ) == args.row_key:
            target = row
            break
    if target is None:
        raise SystemExit(f"Row key not found in {args.csv_path}: {args.row_key}")

    h = row_content_hash(target)
    entry = {
        "type": "signoff",
        "row_key": args.row_key,
        "content_hash": h,
        "reviewer": args.reviewer,
        "timestamp": now_iso(),
    }
    append_log(args.output_dir, entry)

    target["Verification Status"] = "verified"
    target["Verified By"] = args.reviewer
    target["Verified Date"] = entry["timestamp"]
    write_csv_rows(args.csv_path, fieldnames, rows)
    print(f"Signed off {args.row_key} by {args.reviewer}.")


def latest_signoff_for(entries, key_candidates):
    latest = None
    for e in entries:
        if e.get("type") != "signoff":
            continue
        if e.get("row_key") in key_candidates:
            if latest is None or e["timestamp"] > latest["timestamp"]:
                latest = e
    return latest


def evaluate_rows(csv_path: Path, output_dir: Path):
    rows, fieldnames = load_csv_rows(csv_path)
    entries = read_log(output_dir)
    results = []
    for row in rows:
        full_key = row_key_of(row)
        short_key = "|".join(
            [row.get("Discovery Type", ""), row.get("Set", ""), row.get("Request No.", "")]
        )
        signoff = latest_signoff_for(entries, {full_key, short_key})
        current_hash = row_content_hash(row)
        if signoff is None:
            status = "unverified"
        elif signoff["content_hash"] == current_hash:
            status = "verified"
        else:
            status = "stale (edited after sign-off)"
        row["Verification Status"] = status
        results.append((full_key or short_key, status))
    write_csv_rows(csv_path, fieldnames, rows)
    return results


def cmd_check(args):
    results = evaluate_rows(args.csv_path, args.output_dir)
    counts = {}
    for _, status in results:
        counts[status] = counts.get(status, 0) + 1
    print(f"Checked {len(results)} rows in {args.csv_path}:")
    for status, n in counts.items():
        print(f"  {status}: {n}")


def cmd_export_check(args):
    results = evaluate_rows(args.csv_path, args.output_dir)
    blocked = [k for k, status in results if status != "verified"]
    if blocked:
        print(f"BLOCKED: {len(blocked)} row(s) are not verified:")
        for k in blocked:
            print(f"  - {k}")
        print(
            "\nResolve these (sign off, or explicitly export as a labeled draft) before sharing this file externally."
        )
        raise SystemExit(1)
    print("OK: all rows verified. Safe to export.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("record-source")
    p.add_argument("file", type=Path)
    p.add_argument("--entity", required=True)
    p.add_argument("--discovery-type", required=True)
    p.add_argument("--set", required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.set_defaults(func=cmd_record_source)

    p = sub.add_parser("record-signoff")
    p.add_argument("csv_path", type=Path)
    p.add_argument("--row-key", required=True, help="entity|discovery_type|set|request_no (entity optional)")
    p.add_argument("--reviewer", required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.set_defaults(func=cmd_record_signoff)

    p = sub.add_parser("check")
    p.add_argument("csv_path", type=Path)
    p.add_argument("--output-dir", type=Path, required=True)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("export-check")
    p.add_argument("csv_path", type=Path)
    p.add_argument("--output-dir", type=Path, required=True)
    p.set_defaults(func=cmd_export_check)

    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.func(args)


if __name__ == "__main__":
    main()
