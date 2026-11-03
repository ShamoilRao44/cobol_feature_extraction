import re

MAX_CHUNK_LINES = 200
MAX_DATA_ITEMS = 40
NAME_RE = re.compile(r"[A-Z0-9][A-Z0-9-]*")


def build_chunks(program: dict) -> list[dict]:
    """Group consecutive paragraphs into chunks of at most MAX_CHUNK_LINES lines."""
    chunks = []
    current = []
    for paragraph in program.get("paragraphs", []):
        size = paragraph["line_end"] - paragraph["line_start"] + 1
        current_size = (
            current[-1]["line_end"] - current[0]["line_start"] + 1 if current else 0
        )
        if current and current_size + size > MAX_CHUNK_LINES:
            chunks.append(current)
            current = []
        current.append(paragraph)
    if current:
        chunks.append(current)
    return [_chunk(program["name"], number, group) for number, group in enumerate(chunks, 1)]


def _chunk(program_name: str, number: int, paragraphs: list[dict]) -> dict:
    """Describe one chunk by its paragraphs and line span."""
    start = paragraphs[0]["line_start"]
    end = paragraphs[-1]["line_end"]
    truncated = end - start + 1 > MAX_CHUNK_LINES
    return {
        "id": f"chunk:{program_name}.{number}",
        "paragraphs": [paragraph["name"] for paragraph in paragraphs],
        "line_span": [start, start + MAX_CHUNK_LINES - 1 if truncated else end],
        "truncated": truncated,
    }


def chunk_source(raw_lines: list[str], chunk: dict) -> list[tuple[int, str]]:
    """Return the chunk's original (line number, text) pairs."""
    start, end = chunk["line_span"]
    return [
        (number, raw_lines[number - 1].rstrip())
        for number in range(start, min(end, len(raw_lines)) + 1)
    ]


def chunk_facts(program: dict, chunk: dict, source: list[tuple[int, str]]) -> dict:
    """Collect the IR facts that belong to one chunk."""
    names = set(chunk["paragraphs"])
    paragraphs = [p for p in program.get("paragraphs", []) if p["name"] in names]
    words = {word for _, text in source for word in NAME_RE.findall(text.upper())}
    return {
        "paragraphs": [
            {"name": p["name"], "lines": [p["line_start"], p["line_end"]],
             "comment": p.get("comment")}
            for p in paragraphs
        ],
        "conditions": [
            {"kind": c["kind"], "text": c["text"], "line": c["line_span"][0]}
            for c in program.get("conditions", []) if c.get("paragraph") in names
        ],
        "performs": sorted({
            e["target"] for p in paragraphs for e in p.get("events", [])
            if e["kind"] in {"perform", "goto"}
        }),
        "calls": sorted({
            c["target"] for c in program.get("calls", []) if c.get("paragraph") in names
        }),
        "sql": [
            {"kind": s["kind"], "tables": s["tables"], "access": s["access"]}
            for s in program.get("sql", []) if s.get("paragraph") in names
        ],
        "data_items": [
            {key: item.get(key) for key in ("name", "level", "pic", "usage", "value")}
            for item in program.get("data_items", []) if item["name"] in words
        ][:MAX_DATA_ITEMS],
    }
