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
