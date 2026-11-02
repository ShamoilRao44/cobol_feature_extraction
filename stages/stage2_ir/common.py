import re

STATEMENT_START = re.compile(
    r"^\s*(?:MOVE|PERFORM|IF|ELSE|EVALUATE|WHEN|COMPUTE|ADD|SUBTRACT|MULTIPLY|"
    r"DIVIDE|DISPLAY|ACCEPT|READ|WRITE|REWRITE|OPEN|CLOSE|CALL|GO|STOP|GOBACK|"
    r"INITIALIZE|STRING|UNSTRING|INSPECT|SET|EXEC|END-\w+|CONTINUE|EXIT|SORT|"
    r"MERGE|RETURN|RELEASE|DELETE|START|CANCEL|COPY|SELECT|FD)\b|"
    r"^\s*(?:0[1-9]|[1-4][0-9]|66|77|88)\s+",
    re.IGNORECASE,
)
EXEC_START = re.compile(r"\bEXEC\s+(SQL|CICS)\b", re.IGNORECASE)
EXEC_END = re.compile(r"\bEND-EXEC\b", re.IGNORECASE)
WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Strip text and collapse consecutive whitespace."""
    return WHITESPACE.sub(" ", text).strip()


def statement_text(
    code_lines: list[tuple[int, str]],
    i: int,
    max_lines: int = 6,
) -> tuple[str, int]:
    """Join a statement until it ends or another statement begins."""
    if i >= len(code_lines):
        return "", 0
    parts = []
    end_line = code_lines[i][0]
    for index in range(i, min(i + max_lines, len(code_lines))):
        line_number, text = code_lines[index]
        if index > i and STATEMENT_START.match(text):
            break
        parts.append(text.strip())
        end_line = line_number
        joined = normalize(" ".join(parts))
        if joined.endswith("."):
            break
    return normalize(" ".join(parts)), end_line


def find_exec_blocks(code_lines: list[tuple[int, str]]) -> list[dict]:
    """Find and normalize bounded EXEC SQL and EXEC CICS blocks."""
    blocks = []
    index = 0
    while index < len(code_lines):
        line_number, line = code_lines[index]
        match = EXEC_START.search(line)
        if not match:
            index += 1
            continue
        kind = match.group(1).upper()
        parts = []
        end_index = min(index + 14, len(code_lines) - 1)
        closed = False
        for current_index in range(index, min(index + 15, len(code_lines))):
            parts.append(code_lines[current_index][1])
            end_index = current_index
            if EXEC_END.search(code_lines[current_index][1]):
                closed = True
                break
        text = normalize(" ".join(parts)).upper()
        text = EXEC_START.sub("", text, count=1)
        text = EXEC_END.sub("", text)
        text = text.strip()
        if text.endswith("."):
            text = text[:-1].rstrip()
        blocks.append(
            {
                "kind": kind,
                "start": line_number,
                "end": code_lines[end_index][0],
                "text": text,
                "closed": closed,
            }
        )
        index = end_index + 1
    return blocks


def paragraph_of(paragraphs: list[dict], line: int) -> str | None:
    """Return the paragraph name containing a source line."""
    for paragraph in paragraphs:
        if paragraph["line_start"] <= line <= paragraph["line_end"]:
            return paragraph["name"]
    return None


def find_candidates(
    code_lines: list[tuple[int, str]],
    data_items: list[dict],
    variable: str,
) -> list[dict]:
    """Find literal values assigned to a COBOL variable."""
    variable = variable.split()[0].upper() if variable else ""
    candidates = []
    for index, (line_number, text) in enumerate(code_lines):
        if not re.match(r"^\s*MOVE\b", text, re.IGNORECASE):
            continue
        statement, _ = statement_text(code_lines, index)
        match = re.match(
            r"""^\s*MOVE\s+(["'])(.*?)\1\s+TO\s+(.+)$""",
            statement,
            re.IGNORECASE,
        )
        if not match:
            continue
        targets = re.findall(r"[A-Z0-9][A-Z0-9-]*", match.group(3), re.IGNORECASE)
        target_names = set()
        skip_next = False
        for target in targets:
            if skip_next:
                skip_next = False
            elif target.upper() == "OF":
                skip_next = True
            else:
                target_names.add(target.upper())
        if variable in target_names:
            value = match.group(2).strip().upper()[:40]
            candidates.append({"value": value, "line": line_number, "how": "move"})

    for item in data_items:
        value = item.get("value")
        if item.get("name") != variable or not value:
            continue
        literal = re.match(r"""^["'](.*?)["']""", value)
        if literal:
            candidates.append({
                "value": literal.group(1).upper()[:40],
                "line": item.get("line", 0),
                "how": "value",
            })
        break
    candidates.sort(key=lambda item: item["line"])
    unique = []
    seen = set()
    for candidate in candidates:
        if candidate["value"] in seen:
            continue
        unique.append(candidate)
        seen.add(candidate["value"])
    return unique[:10]
