# Increment 6: Business rules per program (Stage 4)

## Goal
For every COBOL program, ask Grok to list its business rules in plain English.
Each rule points to real line numbers. This is the first increment that uses an LLM.

## Input
- The latest complete per-file IR run (`workspace/stage2_outputs/<name>_ir_<time>/`).
- The original source files (the IR stores line spans, not text).

## How it works
1. **Pick programs.** Only files whose IR has a `program` body. Programs with no
   paragraphs in the IR are recorded as `skipped`.
2. **Chunk.** Group consecutive paragraphs into chunks of at most 200 lines
   (`chunks.py`). One chunk = one Grok call.
3. **Build the prompt** (`prompts.py`) from three parts:
   - program facts: name, batch or online, header comment, parameters, files, tables
   - chunk facts: paragraphs, conditions, performs, calls, SQL, and the data items
     whose names appear in these lines (PIC, usage, value)
   - the source lines, numbered with their real line numbers
4. **Ask Grok** (`llm.py`) with temperature 0. Replies are cached in
   `workspace/stage4_cache/` (keyed by model + prompt), so a re-run costs nothing.
   The request is retried on HTTP 429 and 5xx errors.
5. **Check each rule** (`rules.py`). Its lines must fall inside the chunk, otherwise it
   gets `verified: false` (the rule is kept but flagged). Unknown kinds become `other`,
   and an unknown paragraph becomes `null`.
6. **Never stop on errors.** A failed chunk is recorded with its error, the program is marked
   `partial`, and the run continues.

## Output
`workspace/stage4_outputs/<name>_rules_<time>/`
- `files/<path>.rules.json`, one per program:
  `{schema_version, path, program, sha256, model, status, chunks[], rules[]}`
  - rule: `{id, paragraph, title, description, kind, condition, data[], line_span,
    claimed_lines, verified, confidence, chunk}`
  - kind: validation | calculation | decision | data_access | error_handling | flow | other
- `rules_run.json`, the manifest: per program the status, rule count, unverified count,
  chunk count and chunk errors.

## How to run
```powershell
$env:GROK_API_KEY = "<your key>"
$env:GROK_MODEL = "grok-3-mini"   # optional; check the model names on your xAI account
python app.py
# POST /api/stage4/business-rules  with body {}  (or {"ir_dir": "<run folder>"})
# poll GET /api/jobs/<job_id>, then GET /api/jobs/<job_id>/result
```

## Pass check
- `python -m pytest` passes (the tests use a fake LLM, with no network).
- On one small program, the rules match a list written by hand, and every `verified` rule's
  lines point to the code it describes.
- `unverified` and `chunk_errors` are near zero in `rules_run.json`.

## Known limits
- A single paragraph longer than 200 lines is cut at 200 lines (`truncated: true` on the chunk).
- Rules are only as good as the IR: the 5 CardDemo programs hit by the PROGRAM-ID-on-next-line
  bug are `skipped` until that bug is fixed.
- There is no UI button yet (API only, like Stage 3).
- Merging the rules across programs is Increment 7.
