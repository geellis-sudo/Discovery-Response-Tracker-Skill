---
name: "gee-2026-discovery-response-tracker"
description: "Build or update a structured CSV tracker of litigation discovery requests and responses (interrogatories/ROG, requests for production/RFP, requests for admission/RFA) by reading the actual request and response documents and extracting request topic, objections, response summary, documents referenced, and follow-up flags. Use whenever the user mentions discovery responses, interrogatories, RFPs, RFAs, or a discovery log/tracker, or wants a folder of discovery documents turned into a spreadsheet — even without naming a file format. Also use to review, sign off on, verify, or export rows from a tracker already built with this skill. Trigger proactively any time discovery request/response documents are involved."
---

# Discovery Response Tracker

## What this does and why it's built this way

Litigation teams track every discovery request and response in a spreadsheet so anyone on the case can see, at a glance, what was asked, what was objected to, what was actually answered, and what still needs follow-up — without re-reading the underlying filings every time. Building that tracker by hand means reading dense, inconsistently-formatted legal documents and making real judgment calls: paraphrasing what a request is actually asking, distinguishing boilerplate objections from ones specific to a request, and deciding whether a response actually answered the question.

That's the part worth doing with real reading and reasoning, not a rigid extraction template — which is why this is a skill rather than a script. You (the model running this skill) should actually read each document the way a careful paralegal would, not pattern-match on keywords. The bundled scripts in `scripts/` handle the purely mechanical parts (pulling text out of files, merging rows into a CSV without clobbering existing data, hashing content for the sign-off trail) so you can spend your reasoning on the parts that need it.

**Before doing anything else, read `references/security_and_confidentiality.md`.** These are privileged, often highly sensitive litigation documents (which may involve minors, medical records, or other sensitive facts) — how you handle them matters as much as getting the extraction right.

## Prerequisites

- `scripts/extract_text.py` needs `python-docx`, `pdfplumber`, `pdf2image`, and `pytesseract` for full format coverage (docx, text PDFs, and scanned/image PDFs respectively), plus the system package `poppler` for `pdf2image` and `tesseract-ocr` for OCR. If a document type fails to extract, tell the user which dependency is missing rather than silently skipping the file — a silently-skipped discovery response is a missed deadline waiting to happen.
- Confirm with the user (once, not every run) whether their Claude/Cowork account is covered by a data processing agreement appropriate for privileged material. See the security reference file — this isn't something the skill can verify on its own.

## Workflow

Work through one **group** at a time — a group is `(entity/defendant, discovery type, set number)`, e.g. "Example Holdings Company — Interrogatories — First Set." Don't try to hold an entire case's documents in context at once; extract and write a group's rows to the CSV before moving to the next group. This keeps quality high on each group and means a run that gets interrupted partway still leaves a correct, current CSV rather than nothing.

### 1. Gather and prepare source documents

Find the discovery documents in the folder the user points you to (recurse subfolders — many cases organize one subfolder per entity/defendant). For each file, extract plain text with the bundled script rather than trying to read binary formats yourself:

```
python scripts/extract_text.py <file> --out <file>.txt
```

This handles `.docx`, text-layer PDFs, and scanned/image PDFs (falling back to OCR automatically when a PDF page has no extractable text layer), and inserts `--- page N ---` markers so you can cite page numbers later. Plain `.txt`/`.md` files pass through unchanged. If a file fails to convert, say so explicitly to the user rather than quietly moving on.

### 2. Classify each document

Before extracting content, read enough of each document to determine: which entity/party it concerns, whether it's a **request** document (e.g., "Plaintiff's Second Set of Interrogatories to Defendant X") or a **response** document (e.g., "Defendant X's Responses and Objections to Plaintiff's Second Set of Interrogatories"), the discovery type (Interrogatories → ROG, Requests for Production → RFP, Requests for Admission → RFA, Requests for Disclosure → RFD — classify from the document's own title/caption, don't guess from content if the caption states it), and the set number. Different firms format these headers differently ("INTERROGATORY NO. 3", "Interrogatory No. 3:", "3.") — read for meaning, not a fixed pattern.

### 3. Pair request documents with response documents

Group documents by `(entity, discovery_type, set)`. Requests and responses are usually **separate documents served weeks apart**, not one combined file — don't assume both exist together.

- If both exist, use the request document for the actual question text and the response document for the answer — a response's restatement of the request can be paraphrased by drafting counsel and isn't always exact.
- If only a response exists (common — many responses quote the request before answering), extract from the response alone, but record `request_text_source = restated_in_response` rather than `original_request_document`, so anyone reviewing later knows the question text wasn't independently verified.
- If a request exists with no response yet, still create rows for it with `response_summary` blank and `follow_up_needed = Yes` ("response outstanding") — a missing response is itself worth tracking, not an error to skip past.

### 4. Extract structured fields, per request

For each numbered request/response pair in the current group, read the full text — including any "General Objections" or "Definitions" section stated once at the top of the response, since most responses incorporate those into every numbered answer by reference — and produce one row with the fields below. **Read `references/field_definitions.md` before doing this step the first time in a session** — it has the full guidance on what belongs in each field and, critically, where a paraphrase is appropriate versus where a verbatim quote is required (objections are legally load-bearing language; paraphrasing them risks distorting what was actually argued).

Fields to produce per row: `entity`, `discovery_type`, `set`, `request_no`, `request_topic`, `topic_category`, `objections`, `objection_type`, `response_summary`, `documents_referenced`, `follow_up_needed`, `follow_up_rationale`, `notes`, `request_text_source`, `source_files`, `source_locator`. `topic_category` and `objection_type` are short, controlled-vocabulary companions to `request_topic`/`objections` — they exist purely so the tracker (and the Excel export's header filters) stay usable at a glance instead of every row being a unique filter value. Read the guidance for both carefully in the reference file; getting the controlled vocabulary right matters more here than anywhere else in the schema, since a made-up category defeats the entire point.

#### Objection consistency check (critical — do this before finalizing every row)

This came directly out of attorney review of a real tracker, so treat it as load-bearing, not optional polish.

1. **Never let `objections`/`objection_type` say "no objection" while the response text reserves objections.** Before finalizing a row, check the response text for reservation language like *"subject to and without waiving [the above/these] objection(s)"* or equivalent phrasing. If that phrase is present and you were about to write `objections = "None specific to this request."`, stop — that combination is a contradiction until you've specifically reread the language immediately preceding the reservation phrase.

2. **When reservation language is present, this is always a judgment call — resolve it explicitly, in either direction:**
   - If the substantive language right before the reservation phrase reads as a factual or legal basis for resisting the request (disclaiming ownership, control, involvement, relevance, custody, etc.) even though it isn't labeled "Objection," treat it as a presumptive specific objection. Summarize it briefly in `objections` (a short summary is fine, doesn't need to be verbatim — e.g., "Objection on grounds of lack of control: defendant states it did not own or control the records or activity the request asks about.").
   - If, after specifically checking, the preceding language genuinely contains no objection-like basis, it's fine to record `objections = "None specific to this request."` — but only as a deliberate conclusion reached after checking, never as an unexamined default just because no objection happened to be explicitly labeled.

3. **Either way, tag the row so the attorney knows a presumption call was made.** Append the tag **"Objection classification inferred — attorney confirm"** to `objection_type` whenever reservation language triggered this analysis — regardless of which way you resolved it (found an inferred objection, or affirmatively concluded there wasn't one). This is a third, independent fact joined onto the existing two facts in that column (general objection incorporated by reference: yes/no; specific objection to this request: yes/no), using the same `"; "` join convention. A fully-tagged row might read: `"General objection (incorporated by reference); Specific objection; Objection classification inferred — attorney confirm"`. Only add this tag when the reservation-language trigger actually fired this judgment call — don't add it to rows where a specific objection was stated explicitly and unambiguously (no inference needed), and don't add it where no reservation language appears at all.

The failure mode this fixes: a row showing `objection_type = "...None specific to this request"` while `response_summary` (correctly) notes the response was given "subject to and without waiving objections" — an internal contradiction — plus a missed specific objection stated in narrative/denial form rather than a labeled "Objection:" sentence. The tag ensures an attorney can filter for and specifically re-check every row where the tool had to make this presumption call, in either direction, rather than trusting a silent judgment they never get to see.

### 5. Completeness check

Within each group, check that the request numbers you extracted are sequential and complete against what the document implies (e.g., if the response references "Interrogatory No. 18" but you only produced rows 1–15, something was missed). Don't silently under-report — go back and find the missing ones, or flag clearly in your summary to the user that a gap exists and why.

### 6. Write the rows to the CSV

Once you have a group's rows as a JSON list matching the schema in `references/field_definitions.md`, hand them to the merge script rather than editing the CSV by hand — it applies the dedupe/conflict logic consistently, which matters more here than it would for a one-off document:

```
python scripts/csv_writer.py --rows <group_rows>.json --output-dir <output_dir>
```

This writes/updates one CSV per entity plus a master rollup (with an `Entity` column) in `<output_dir>`, using `(entity, discovery_type, set, request_no)` as the row key. On a first run everything is new. On a later run against updated or supplemental documents:
- A new key → appended as a new row.
- An existing key with unchanged substantive content → left alone.
- An existing key with **different** content (e.g., a supplemental response was served) → the new version is *not* written over the old one. It's appended to `<entity>_review_needed.csv` showing old vs. new side by side, and the original row stays put until a human resolves it. Tell the user when this happens — it usually means something genuinely changed in the case, worth their attention rather than a silent overwrite.

### 7. Log source documents to the audit trail

For traceability — so an attorney can later confirm a row wasn't altered from what the source document actually said — record each source file processed:

```
python scripts/audit_log.py record-source <file> --entity "<entity>" --discovery-type <type> --set <set> --output-dir <output_dir>
```

This appends a hash + timestamp entry to `<output_dir>/audit_log.jsonl`; it does not touch the source file itself. Never modify source documents — always treat them as read-only.

## Verification & sign-off

Extracted rows start life as `Verification Status = unverified`. That's intentional — the tracker should be usable immediately, but nothing should be treated as attorney-confirmed until an attorney actually looks at it. When the user (or an attorney working through the tracker) tells you a row or set of rows has been reviewed and is correct, record the sign-off rather than just editing the status column by hand:

```
python scripts/audit_log.py record-signoff <csv_path> --row-key "<entity>|<discovery_type>|<set>|<request_no>" --reviewer "<name>" --output-dir <output_dir>
```

This hashes the row's current substantive content and logs reviewer + timestamp + hash to the audit trail, then updates `Verification Status`/`Verified By`/`Verified Date` on the row itself. The reason to route sign-off through the hash rather than just flipping a column value: if that row's content changes later — a re-run picks up a supplemental response, or someone hand-edits the CSV — the stored hash won't match the new content anymore, and a status check will surface it as stale instead of silently showing a false "verified."

To check status (and catch anything that's gone stale since it was signed off):

```
python scripts/audit_log.py check <csv_path> --output-dir <output_dir>
```

## Exporting a clean copy

When the user wants a copy of the tracker to actually send somewhere — co-counsel, a partner, attached to a filing — run the export check first, on the master CSV (or each entity CSV if the user only wants one):

```
python scripts/audit_log.py export-check <csv_path> --output-dir <output_dir>
```

If any included row is unverified or stale, don't hand over a copy that looks clean without saying so. Either help the user get the outstanding rows signed off first, or, if they explicitly want a draft copy anyway, produce it clearly labeled (e.g., a "DRAFT — CONTAINS UNVERIFIED AI EXTRACTIONS" note at the top) so it's never mistaken for a reviewed version downstream.

The actual thing people want to look at and share is usually not a raw CSV — it's a formatted workbook, one tab per defendant/entity plus a rollup, the way a hand-built tracker looks. Once the CSVs reflect what you want to hand over, assemble the workbook:

```
python scripts/export_xlsx.py --output-dir <output_dir> --xlsx-path <path>/tracker.xlsx
```

This reads `master.csv` (already the source of truth — no separate merge logic here) and produces one worksheet per entity plus a `Master` sheet, bold header rows, frozen header, header dropdown filters (Excel AutoFilter) on every sheet, and a `Review Needed` sheet if any `*_review_needed.csv` files exist. **Worksheet tab names are auto-shortened from the full legal entity name** (stripping corporate suffixes, trimming to Excel's 31-character sheet-name limit, disambiguating collisions) — this is a mechanical heuristic, not a reproduction of how a person would actually choose to abbreviate related entity names, so tell the user the tab names are a starting point and may need a manual rename if they don't read well, particularly where two related entities shorten to something confusingly similar.

## CSV columns

`Entity, Discovery Type, Set, Request No., Request Topic, Topic Category, Objections, Objection Type, Response Summary, Documents Referenced, Follow-Up Needed?, Follow-Up Rationale, Notes, Source Files, Source Locator, Request Text Source, Verification Status, Verified By, Verified Date`

`Topic Category` and `Objection Type` are the two filter-friendly columns — see `references/field_definitions.md` for their base controlled vocabularies before populating them, and see the "Objection consistency check" above (which adds a third `Objection Type` tag, "Objection classification inferred — attorney confirm") before finalizing either one. Because this column drives the Excel AutoFilter header dropdown on export, that third tag is what lets an attorney filter directly for every row where the tool had to make an objection-presence judgment call, separate from general follow-up flags.

(The per-entity CSVs and per-entity worksheet tabs omit `Entity`; the master rollup/sheet includes it.)

## Multiple defendants / entities in one case

Nothing extra is required to handle a case with many defendants — the `entity` field on every extracted row (Step 4) is what drives everything downstream. Point the workflow at a case folder with one subfolder per entity (Step 1 already recurses subfolders), classify entity correctly per document (Step 2), and `csv_writer.py` naturally groups rows into one CSV per entity plus the master rollup with no special handling needed. For a case with a large number of related-facility defendants, work through them one entity/group at a time (see "A note on scale" below) rather than trying to hold the whole case in context — the CSVs accumulate correctly across turns either way, and `export_xlsx.py` reads whatever's in `master.csv` at the time it's run, so the workbook can be regenerated at any point without needing every entity to be finished first.

## A note on scale

For a case with a handful of discovery sets, this whole workflow fits comfortably in one pass. For a case with many entities and many sets — the kind of matter with a dozen related-facility defendants each with several sets of interrogatories — work through it group by group across multiple turns if needed, writing to the CSV as you go rather than trying to extract everything before writing anything. The CSV itself is the source of truth for what's done; if a session ends partway through, the next run can pick up by checking which groups already have rows.

