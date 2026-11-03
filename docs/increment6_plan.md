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

## LLM settings (same code on the laptop and the VM)
`llm.py` is one OpenAI-compatible client (`POST <base_url>/chat/completions`). Only the
values change between machines. They are read from `.env` in the project root
(git-ignored; copy `.env.example`), and real environment variables override them.

| Variable | Laptop (Grok) | VM (local Qwen) |
|---|---|---|
| `LLM_BASE_URL` | `https://api.x.ai/v1` | the local server's OpenAI URL, e.g. `http://localhost:8000/v1` |
| `LLM_MODEL` | `grok-3-mini` | the model name the local server reports |
| `LLM_API_KEY` | your xAI key | empty, or whatever the local server expects |
| `LLM_CONTEXT_TOKENS` | 64000 | 64000 |
| `LLM_MAX_OUTPUT_TOKENS` | 8000 | 8000 |

Token budget: before every call the prompt is estimated at ~3 characters per token and must
fit in `context_tokens - max_output_tokens`, otherwise that chunk is recorded as an error.
A 200-line chunk is about 4-7k tokens, far below the 56k budget.

## How to run
Laptop:
1. `pip install -r requirements.txt` (adds python-dotenv), then `copy .env.example .env`
   and put your xAI key in `LLM_API_KEY`.
2. `python app.py`
3. `POST /api/stage4/business-rules` with body `{}` (or `{"ir_dir": "<run folder>"}`).
4. Poll `GET /api/jobs/<job_id>`, then read `GET /api/jobs/<job_id>/result`.

VM (manual steps):
1. Start the local Qwen3 Coder server and note its OpenAI-compatible URL and model name
   (for example, open `<url>/models` in a browser or with curl).
2. `cp .env.example .env`, then set `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY`
   (the VM block in the file shows the shape).
3. Run steps 2-4 above.

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
