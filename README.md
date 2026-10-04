# Discovery Response Tracker (Claude skill)

A Claude skill that reads litigation discovery request and response documents
(interrogatories, requests for production, requests for admission, requests for
disclosure) and builds or updates a structured CSV tracker: request topic,
objections, response summary, documents referenced, and follow-up flags. It can
also review, sign off on, verify, and export rows from an existing tracker.

## Contents

The skill lives in `gee-2026-discovery-response-tracker/`, and
`gee-2026-discovery-response-tracker.zip` is the same folder packaged for upload.

- `SKILL.md`: the skill's instructions and workflow.
- `references/field_definitions.md`: what belongs in each tracker field.
- `references/security_and_confidentiality.md`: handling rules for privileged material.
- `scripts/extract_text.py`: text extraction from .docx, text PDFs, and scanned PDFs (OCR).
- `scripts/csv_writer.py`: merges rows into the tracker CSV without overwriting existing data.
- `scripts/audit_log.py`: content hashing and sign-off audit trail.
- `scripts/export_xlsx.py`: exports the tracker to Excel.

## Requirements

Python 3 with `python-docx`, `pdfplumber`, `pdf2image`, and `pytesseract`, plus
the system packages `poppler` and `tesseract-ocr`.

## Try it

1. Download `gee-2026-discovery-response-tracker.zip` from the root of this repository
   (click the file, then the download button).
2. Install it in one of two ways:
   - **Claude (web or desktop):** open Settings, then Capabilities, and upload the ZIP
     under Skills. Skills must be enabled for your account.
   - **Claude Code:** unzip it into `~/.claude/skills/` so the folder sits at
     `~/.claude/skills/gee-2026-discovery-response-tracker/`.
3. Give Claude a folder of discovery requests and responses and ask it to build a
   discovery tracker. Use sample or public documents, never privileged material.

## Confidentiality

This repository holds tooling only. Do not commit discovery documents, generated
trackers, or audit logs from real matters.

## License

Licensed under the GNU Affero General Public License v3.0. See `LICENSE`.
