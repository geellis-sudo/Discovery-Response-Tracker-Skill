# Field definitions

These are working definitions, not a rigid template — the point of doing this extraction with real reading rather than a regex pattern is that you can apply judgment where these documents don't fit the mold. If a case's discovery practice doesn't match something described here, use your judgment and note the deviation in `notes` rather than forcing a bad fit.

## discovery_type

Classify from the document's own title/caption: Interrogatories → `ROG`, Requests for Production → `RFP`, Requests for Admission → `RFA`, Requests for Disclosure → `RFD`. If a document mixes types (some jurisdictions combine interrogatories and requests for production in one set), split it into separate rows per type rather than forcing one label.

## set

The numbered set as stated in the document's own title/caption (First, Second, Third, ...). Don't infer this from filename conventions alone if the document text states it — the caption is authoritative.

## request_no

The number as it appears next to this specific request in the source document.

## request_topic

A short paraphrase — roughly one sentence — of what's being asked. This is **not** a verbatim copy of the request text; it requires actually understanding the request, including any definitions section it depends on (discovery requests routinely say things like "As used herein, 'the Facility' means..." and then rely on that definition throughout — read the definitions before paraphrasing a request that uses them).

**Example:** Request text: *"Identify every legal name, former name, trade name, or DBA you have used during the Relevant Period."* → `request_topic`: "Legal, former, and trade names (DBAs) used by the entity during the relevant period."

## topic_category

`request_topic` is deliberately specific (one sentence, no detail lost) — which means it's not useful as a spreadsheet filter column, since it produces close to as many distinct values as there are requests. `topic_category` exists purely to make the tracker filterable: assign exactly **one** of the following broad buckets per row, whichever is the most central subject of the request. Don't try to multi-tag a request across categories — if it genuinely spans more than one, pick the one a reader would search for first.

- Entity Identity & Formation (legal name, DBAs, incorporation, corporate status)
- Locations & Addresses
- Purpose & Operations
- Personnel & Leadership (directors, administrators, staff, employment)
- Policies & Procedures
- Incidents, Complaints & Claims History
- Licensing & Regulatory
- Insurance & Coverage
- Financial & Corporate Records (board minutes, financial statements)
- Communications
- Other

This list is meant to hold up across different matters, not just one case — if a request genuinely doesn't fit any bucket well, use "Other" rather than stretching one of the others to fit; a bad-fit category is worse than an honest "Other," and a pattern of "Other" rows in one matter might mean this list needs a case-specific addition (flag that to the user rather than silently forcing categories).

**Example:** `request_topic`: "Physical addresses, mailing addresses, and other locations used by the entity, and the dates each was used." → `topic_category`: "Locations & Addresses"

## objections

Record what was actually raised, in a way that preserves the legally significant language rather than paraphrasing it away:

- If the response incorporates "General Objections" stated once at the top of the response document by reference (nearly all responses do this — look for language like "Defendant incorporates the foregoing General Objections into each response below"), say so plainly, e.g. "General Objections incorporated by reference."
- If there's an objection specific to this request (relevance, overbroad, unduly burdensome, vague, privilege, work product, etc.), **quote it verbatim** rather than summarizing it. Objection language is the actual legal argument being made — paraphrasing risks changing its meaning or waiving nuance a follow-up motion might turn on. If there's no specific objection beyond the general ones, say so ("None specific to this request") rather than leaving the field ambiguous.

## objection_type

Same problem as `request_topic`: the verbatim quotes in `objections` are exactly right for the substantive record but make for an unfilterable column (every row's text is close to unique). `objection_type` is a short, controlled-vocabulary companion column built from two independent yes/no facts about the row:

1. Did the response invoke general objections (incorporated by reference or otherwise) as applying to this response? → include the tag **"General objection (incorporated by reference)"**.
2. Is there an objection specific to this particular request, beyond the general ones? → include the tag **"Specific objection"**. If not, include **"None specific to this request"** instead (these two are mutually exclusive — exactly one of them applies to every row).

Join whichever tags apply with `"; "`. Most rows in a response document that opens with a General Objections section will end up as `"General objection (incorporated by reference); None specific to this request"` — that's expected, not a bug; it's the common case. A row with a genuine, particularized objection becomes `"General objection (incorporated by reference); Specific objection"`. This lets someone filter for "every request that got a specific objection" in one filter action regardless of whether general objections also applied — they select the "Specific objection" checkbox and get all of them, combined rows included.

**Example:** `objections`: "Defendant objects that this Request is overly broad in temporal scope and not proportional to the needs of the case." → `objection_type`: "General objection (incorporated by reference); Specific objection"

## response_summary

A concise summary of the substantive answer actually given, after any objections — including whether the response was given "subject to and without waiving" the stated objections (extremely common phrasing, and worth flagging since it means the objecting party reserved the right to argue the objection later even though they answered), and whether the answer was a **full answer**, a **partial answer**, or **objection only** (no substantive answer given at all). This last distinction is often the single most useful thing in the whole tracker — it's what tells an attorney where a motion to compel might be worth filing.

**This looks different depending on discovery_type — don't apply the ROG pattern above to RFAs or RFPs by default, they don't answer in prose the same way.**

### RFA (Requests for Admission)

An RFA response isn't a narrative answer — it's a request to admit or deny a specific factual statement, and the responding party is required to use one of a small set of controlled responses. Lead `response_summary` with that status, verbatim, before anything else: **Admitted** / **Denied** / **Admitted in part and denied in part** / **Cannot admit or deny after reasonable inquiry**. For anything other than a clean "Admitted" or "Denied," include the qualifying language — a partial admission that's heavily qualified can functionally be closer to a denial, and an attorney needs to see the qualification to know which it is, not just the headline word.

**Example:** `response_summary`: "Admitted in part and denied in part. Admits no written policy on the topic existed before a stated date, but denies that no procedures existed, citing informal practices then in use."

Follow-up candidates specific to RFAs: a "cannot admit or deny" response that doesn't actually state a reasonable inquiry was made (Federal Rule 36 and most state analogs require the responding party to say so — its absence is itself a deficiency worth flagging); an objection used in place of an actual admit/deny where the request seems like a legitimate factual question; or a qualification so broad it effectively denies what it claims to admit.

### RFP (Requests for Production)

An RFP response is about production status, not a narrative answer either. Lead `response_summary` with the status: **Will produce** (responsive documents exist and will be/were produced, cite Bates range in `documents_referenced` if given) / **Already produced** (points to a prior production, cite Bates range) / **No responsive documents located** (searched, nothing found) / **Withholding** (state the stated basis — privilege, not in the responding party's possession/custody/control, equally available to the requesting party, etc.).

**Example:** `response_summary`: "Subject to and without waiving objections, Defendant states no responsive documents were located for the earliest years requested after a reasonable search; documents for the remaining period will be produced." `documents_referenced`: "Documents Bates stamped ABC000100–ABC000150."

Follow-up candidates specific to RFPs: "will produce" language with no Bates range ever cited (a promise not yet delivered — check later documents in the folder to see if a range showed up in a later-dated response before flagging this, since it may have simply been supplemented since); a withholding response with no accompanying privilege log reference when privilege is the stated basis; or a scope/temporal objection that narrows what's produced without saying what was excluded, which makes it impossible to tell how much was left out.

## documents_referenced

Bates ranges or exhibit numbers cited in the response (e.g., "Documents Bates stamped ABC000001–ABC000450" or "See Exhibit C"). If the response promises documents but doesn't cite specific Bates numbers yet ("responsive documents will be produced"), note that explicitly — it's a different situation from documents already identified.

## follow_up_needed / follow_up_rationale

This is a **suggested flag with reasoning attached, not a determination** — an attorney makes the actual call about whether something needs follow-up. Flag candidates where: the response is objection-only with no substantive answer, the response doesn't actually address what was asked (evasive or non-responsive), the answer is vague or clearly incomplete, or documents were promised but not yet produced (check the audit trail / prior rows for whether they showed up later). Explain your reasoning briefly in `follow_up_rationale` so the attorney reviewing it doesn't have to reconstruct why you flagged it.

## notes

Leave this sparse — it's a human catch-all field. Don't invent content here to fill space; an empty `notes` field is a fine and normal outcome.

## request_text_source

`original_request_document` if you had the actual request document to work from, `restated_in_response` if you only had the response's restatement of the request. This matters because a response's paraphrase of a request is drafted by the responding party's counsel and may subtly reframe what was actually asked.

## source_files / source_locator

The filename(s) you extracted this row from, plus a page or paragraph reference if you can determine one (the `--- page N ---` markers from `extract_text.py` help here). This is what lets an attorney pull up the original document and check a specific row without re-reading the whole thing — treat it as load-bearing, not optional metadata.

## Row schema (JSON, for handing to `scripts/csv_writer.py`)

```json
{
  "entity": "Example Holdings Company, Inc.",
  "discovery_type": "ROG",
  "set": "First",
  "request_no": "1",
  "request_topic": "Physical addresses, mailing addresses, and other locations used by the entity, and dates used.",
  "topic_category": "Locations & Addresses",
  "objections": "None specific to this request.",
  "objection_type": "General objection (incorporated by reference); None specific to this request",
  "response_summary": "Entity identifies two addresses: 123 Example Street, Anytown, ST 00000 and 456 Sample Avenue, Anytown, ST 00000.",
  "documents_referenced": "None cited.",
  "follow_up_needed": "No",
  "follow_up_rationale": "",
  "notes": "",
  "request_text_source": "original_request_document",
  "source_files": "Example Defendant Response to First ROG.docx",
  "source_locator": "p. 3"
}
```
