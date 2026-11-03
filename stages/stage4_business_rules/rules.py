import hashlib
import json
import os
from typing import Callable

from stages.stage4_business_rules.chunks import build_chunks, chunk_facts, chunk_source
from stages.stage4_business_rules.prompts import (
    CONFIDENCES,
    RULE_KINDS,
    SYSTEM_PROMPT,
    build_prompt,
    parse_rules,
    program_context,
)

Ask = Callable[[str, str], str]


def cached_ask(ask: Ask, cache_dir: str | None, model: str, prompt: str) -> str:
    """Call the LLM, reusing a cached reply for the same model and prompt."""
    if not cache_dir:
        return ask(SYSTEM_PROMPT, prompt)
    key = hashlib.sha256(f"{model}\n{SYSTEM_PROMPT}\n{prompt}".encode("utf-8")).hexdigest()
    path = os.path.join(cache_dir, f"{key}.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as source:
            return json.load(source)["reply"]
    reply = ask(SYSTEM_PROMPT, prompt)
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as output:
        json.dump({"model": model, "reply": reply}, output, ensure_ascii=False)
    return reply


def clean_rule(raw: dict, chunk: dict) -> dict:
    """Normalize one LLM rule and check its lines against the chunk span."""
    start, end = chunk["line_span"]
    line_start = raw.get("line_start")
    line_end = raw.get("line_end", line_start)
    verified = (
        isinstance(line_start, int) and isinstance(line_end, int)
        and start <= line_start <= line_end <= end
    )
    paragraph = str(raw.get("paragraph") or "").upper()
    kind = str(raw.get("kind") or "other").lower()
    confidence = str(raw.get("confidence") or "low").lower()
    data = raw.get("data") if isinstance(raw.get("data"), list) else []
    return {
        "paragraph": paragraph if paragraph in chunk["paragraphs"] else None,
        "title": str(raw.get("title") or "").strip()[:120],
        "description": str(raw.get("description") or "").strip(),
        "kind": kind if kind in RULE_KINDS else "other",
        "condition": raw.get("condition") or None,
        "data": [str(item).upper() for item in data][:20],
        "line_span": [line_start, line_end] if verified else None,
        "claimed_lines": None if verified else [line_start, line_end],
        "verified": verified,
        "confidence": confidence if confidence in CONFIDENCES else "low",
        "chunk": chunk["id"],
    }


def build_program_rules(file_ir: dict, raw_lines: list[str], ask: Ask, model: str,
                        cache_dir: str | None = None) -> dict:
    """Extract business rules for one program, one chunk at a time."""
    program = file_ir["program"]
    result = {
        "schema_version": "1.0",
        "path": file_ir["path"],
        "program": program["id"],
        "sha256": file_ir["sha256"],
        "model": model,
        "status": "complete",
        "chunks": [],
        "rules": [],
    }
    chunks = build_chunks(program)
    if not chunks:
        result["status"] = "skipped"
        result["reason"] = "no paragraphs in IR"
        return result
    context = program_context(program)
    for chunk in chunks:
        source = chunk_source(raw_lines, chunk)
        prompt = build_prompt(context, chunk_facts(program, chunk, source), source)
        entry = dict(chunk, status="ok", error=None, rules=0)
        try:
            raw_rules = parse_rules(cached_ask(ask, cache_dir, model, prompt))
        except (OSError, ValueError, KeyError) as error:
            entry.update(status="error", error=str(error)[:300])
            result["status"] = "partial"
            result["chunks"].append(entry)
            continue
        for raw in raw_rules:
            rule = clean_rule(raw, chunk)
            rule = {"id": f"rule:{program['name']}.{len(result['rules']) + 1}", **rule}
            result["rules"].append(rule)
            entry["rules"] += 1
        result["chunks"].append(entry)
    return result
