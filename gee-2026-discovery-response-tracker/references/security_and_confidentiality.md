# Security & confidentiality

This is engineering/workflow guidance, not legal advice. The documents this skill touches are privileged litigation material, and may include especially sensitive content such as information about minors or health records. The deploying firm's ethics/compliance counsel and IT security should have signed off on using an AI tool for this before it touches a real matter. Your job while running this skill is to behave consistently with that expectation, not to certify compliance yourself.

## Before starting work on a new matter

Ask the user (once per matter, not every run) whether the account you're operating under is covered by an appropriate data handling agreement for privileged material — ideally one with a zero-data-retention commitment (the vendor doesn't retain or train on submitted content). If they don't know, say plainly that this is worth confirming with their firm's IT/compliance function before proceeding on anything privileged, rather than assuming it's fine. This isn't something you can verify from inside a session.

## While working

- Treat every source document and every extracted field as confidential by default. Don't restate large verbatim excerpts of sensitive material back to the user in chat when a summary or the CSV row would do — the CSV, not the conversation transcript, should be the durable record.
- Never modify source documents. Open and read them, never edit or overwrite them. All output goes to the tracker CSVs, the audit log, and the `_review_needed` file.
- If a source document contains redactions, don't try to infer or reconstruct what's underneath them. If a request or response appears to depend on redacted material in a way that affects extraction, flag it rather than guessing.
- Keep work scoped to one matter at a time. Don't carry context, cached text, or extracted rows from a different case into the current session's output — each matter's tracker should be traceable to only that matter's documents.
- Don't log API keys, credentials, or anything else sensitive beyond document content into the audit trail — the audit log should contain hashes, filenames, timestamps, and reviewer names, not raw document text or secrets.

## Regulatory/ethics context worth surfacing to the firm (not something you can certify)

- ABA Model Rules of Professional Conduct 1.1 (competence, including technology competence), 1.6 (confidentiality — sending client information to a third-party AI vendor), and 5.3 (supervision of nonlawyer/technology assistance), plus the analogous state bar rules and ethics opinions on generative AI use, which vary by jurisdiction.
- HIPAA, if source documents contain protected health information (plausible for matters involving treatment facilities) — including whether a Business Associate Agreement is needed with the AI vendor.
- Heightened handling for minors' identifying information — consider whether a masking pass is needed on `response_summary`/`notes` before content leaves firm infrastructure, particularly if the tracker will be shared outside the immediate case team.
- Litigation hold / preservation obligations — this skill's strictly read-only handling of source files is designed to be consistent with preservation duties, but confirm that's sufficient for the specific matter's hold order.

## What this skill deliberately does not do

It doesn't decide what's privileged, doesn't make final objection or production-strategy calls, and doesn't replace attorney review — see the sign-off workflow in `SKILL.md`. The AI-generated fields most likely to need correction are `objections`, `response_summary`, and `follow_up_needed`; treat those as a first-pass read for attorney verification, not a finished product.
