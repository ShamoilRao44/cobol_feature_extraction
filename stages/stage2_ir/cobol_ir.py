import re

from stages.stage1_inventory.models import FileContent
from stages.stage2_ir.common import (
    find_exec_blocks,
    normalize,
    paragraph_of,
    statement_text,
)

PROGRAM_ID = re.compile(
    r"^\s*PROGRAM-ID\.?\s+['\"]?([A-Z0-9][A-Z0-9-]*)",
    re.IGNORECASE,
)
DIVISION_PATTERNS = {
    "identification": re.compile(r"^\s*(IDENTIFICATION|ID)\s+DIVISION", re.IGNORECASE),
    "environment": re.compile(r"^\s*ENVIRONMENT\s+DIVISION", re.IGNORECASE),
    "data": re.compile(r"^\s*DATA\s+DIVISION", re.IGNORECASE),
    "procedure": re.compile(r"^\s*PROCEDURE\s+DIVISION", re.IGNORECASE),
}
DATA_ENTRY = re.compile(
    r"^\s*(\d{1,2})\s+([A-Z0-9][A-Z0-9-]*|FILLER)\b",
    re.IGNORECASE,
)
USAGE = re.compile(
    r"(?<![A-Z0-9-])(COMP-3|COMP-1|COMP-2|COMP-4|COMP-5|COMP|"
    r"COMPUTATIONAL-3|COMPUTATIONAL|BINARY|PACKED-DECIMAL|DISPLAY|INDEX|"
    r"POINTER)(?![A-Z0-9-])",
    re.IGNORECASE,
)
PIC = re.compile(r"\bPIC(?:TURE)?\s+(?:IS\s+)?(\S+)", re.IGNORECASE)
REDEFINES = re.compile(r"\bREDEFINES\s+([A-Z0-9-]+)", re.IGNORECASE)
OCCURS = re.compile(r"\bOCCURS\s+(\d+)", re.IGNORECASE)
VALUE = re.compile(
    r"\bVALUE\s+(?:IS\s+)?(\"[^\"]*\"|'[^']*'|[^\s.]+)",
    re.IGNORECASE,
)
SELECT = re.compile(r"^\s*SELECT\s+(?:OPTIONAL\s+)?([A-Z0-9-]+)", re.IGNORECASE)
ASSIGN = re.compile(
    r"\bASSIGN(?:\s+TO)?\s+(['\"]?)([A-Z0-9#@$._-]+)\1",
    re.IGNORECASE,
)
ORGANIZATION = re.compile(
    r"\bORGANIZATION\s+(?:IS\s+)?(LINE\s+SEQUENTIAL|SEQUENTIAL|INDEXED|RELATIVE)\b",
    re.IGNORECASE,
)
ACCESS_MODE = re.compile(
    r"\bACCESS\s+(?:MODE\s+)?(?:IS\s+)?(SEQUENTIAL|RANDOM|DYNAMIC)\b",
    re.IGNORECASE,
)
FILE_STATUS = re.compile(r"\bFILE\s+STATUS\s+(?:IS\s+)?([A-Z0-9-]+)", re.IGNORECASE)
FD = re.compile(r"^\s*(FD|SD)\s+([A-Z0-9-]+)", re.IGNORECASE)
LEVEL_01 = re.compile(r"^\s*01\s+([A-Z0-9-]+)\b", re.IGNORECASE)
SECTION = re.compile(r"^\s*(?:WORKING-STORAGE|LOCAL-STORAGE|LINKAGE)\s+SECTION\b", re.IGNORECASE)
COPY = re.compile(r"^\s*COPY\s+[\"']?([A-Z0-9][A-Z0-9_-]*)", re.IGNORECASE)
COPY_REPLACING = re.compile(r"\bREPLACING\b", re.IGNORECASE)
PARAGRAPH = re.compile(r"^[A-Z0-9][A-Z0-9-]*\.$", re.IGNORECASE)
SECTION_HEADER = re.compile(r"^[A-Z0-9][A-Z0-9-]*\s+SECTION\.$", re.IGNORECASE)
NOT_PARAGRAPH = {
    "EXIT", "CONTINUE", "GOBACK", "END-IF", "END-EVALUATE", "END-PERFORM",
    "END-READ", "END-EXEC", "END-CALL", "STOP", "NEXT", "SENTENCE",
}
IF = re.compile(r"^\s*IF\s+(.+?)(?:\s+THEN)?\s*$", re.IGNORECASE)
EVALUATE = re.compile(r"^\s*EVALUATE\s+(.+)", re.IGNORECASE)
WHEN = re.compile(r"^\s*WHEN\s+(.+)", re.IGNORECASE)
PERFORM = re.compile(
    r"^\s*PERFORM\s+([A-Z0-9-]+)(?:\s+(?:THRU|THROUGH)\s+([A-Z0-9-]+))?",
    re.IGNORECASE,
)
INLINE_PERFORM = re.compile(
    r"^\s*PERFORM\s+(UNTIL|VARYING|WITH\s+TEST|\d+\s+TIMES|FOREVER)\b",
    re.IGNORECASE,
)
UNTIL = re.compile(r"\bUNTIL\s+(.+)", re.IGNORECASE)
GOTO = re.compile(r"^\s*GO\s+TO\s+([A-Z0-9-]+)", re.IGNORECASE)
CALL = re.compile(
    r"\bCALL\s+(?:(['\"])([A-Z0-9#@$_-]+)\1|([A-Z][A-Z0-9-]*))",
    re.IGNORECASE,
)
DISPLAY = re.compile(r"^\s*DISPLAY\s+(.+)", re.IGNORECASE)
QUOTED = re.compile(r"(['\"])(.*?)\1")
OPEN = re.compile(r"^\s*OPEN\s+(.+)", re.IGNORECASE)
CLOSE = re.compile(r"^\s*CLOSE\s+(.+)", re.IGNORECASE)
READ = re.compile(r"^\s*READ\s+([A-Z0-9-]+)", re.IGNORECASE)
WRITE = re.compile(r"^\s*WRITE\s+([A-Z0-9-]+)", re.IGNORECASE)
REWRITE = re.compile(r"^\s*REWRITE\s+([A-Z0-9-]+)", re.IGNORECASE)
DELETE = re.compile(r"^\s*DELETE\s+([A-Z0-9-]+)", re.IGNORECASE)
START = re.compile(r"^\s*START\s+([A-Z0-9-]+)", re.IGNORECASE)
OPEN_MODES = re.compile(r"\b(INPUT|OUTPUT|I-O|EXTEND)\b", re.IGNORECASE)
USING = re.compile(r"\bUSING\b(.*)", re.IGNORECASE)
DROP_USING = re.compile(r"\b(BY|REFERENCE|CONTENT|VALUE|RETURNING)\b", re.IGNORECASE)
FROM_CLAUSE = re.compile(
    r"\bFROM\s+(.*?)(?=\bWHERE\b|\bGROUP\b|\bORDER\b|\bHAVING\b|\bUNION\b|"
    r"\bFETCH\b|\bFOR\b|\bWITH\b|$)",
    re.IGNORECASE,
)
TABLE_TOKEN = re.compile(r"^[A-Z0-9_.$#@]+", re.IGNORECASE)
JOIN = re.compile(r"\bJOIN\s+([A-Z0-9_.$#@]+)", re.IGNORECASE)
CURSOR_DECLARE = re.compile(r"\bDECLARE\s+([A-Z0-9-]+)\s+CURSOR", re.IGNORECASE)
CURSOR_OPEN = re.compile(r"\b(?:OPEN|CLOSE)\s+([A-Z0-9-]+)", re.IGNORECASE)
CURSOR_FETCH = re.compile(
    r"\bFETCH\s+(?:(?:NEXT|PRIOR|FIRST|LAST|FROM)\s+)*([A-Z0-9-]+)",
    re.IGNORECASE,
)
HOST_VAR = re.compile(r":([A-Z][A-Z0-9-]*)", re.IGNORECASE)
INCLUDE_NAME = re.compile(r"\bINCLUDE\s+([A-Z0-9_-]+)", re.IGNORECASE)
CICS_OPTION = {
    "map": re.compile(r"(?<![A-Z-])MAP\(\s*(['\"])?([A-Z0-9#@$_-]+)\1?\s*\)", re.IGNORECASE),
    "mapset": re.compile(r"(?<![A-Z-])MAPSET\(\s*(['\"])?([A-Z0-9#@$_-]+)\1?\s*\)", re.IGNORECASE),
    "program": re.compile(r"(?<![A-Z-])PROGRAM\(\s*(['\"])?([A-Z0-9#@$_-]+)\1?\s*\)", re.IGNORECASE),
    "transid": re.compile(r"(?<![A-Z-])TRANSID\(\s*(['\"])?([A-Z0-9#@$_-]+)\1?\s*\)", re.IGNORECASE),
    "file": re.compile(r"(?<![A-Z-])(?:FILE|DATASET)\(\s*(['\"])?([A-Z0-9#@$_-]+)\1?\s*\)", re.IGNORECASE),
    "queue": re.compile(r"(?<![A-Z-])(?:QUEUE|QNAME)\(\s*(['\"])?([A-Z0-9#@$_-]+)\1?\s*\)", re.IGNORECASE),
}
CICS_TWO_WORD_COMMAND = re.compile(
    r"^(SEND\s+(MAP|TEXT|CONTROL)|RECEIVE\s+MAP|"
    r"(?:READQ|WRITEQ|DELETEQ)\s+(TD|TS)|"
    r"HANDLE\s+(CONDITION|ABEND|AID)|IGNORE\s+CONDITION)\b",
    re.IGNORECASE,
)
CONDITION_ERROR_PATTERNS = [
    ("SQLCODE", re.compile(r"\bSQLCODE\b", re.IGNORECASE)),
    ("RETURN_CODE", re.compile(r"\bRETURN-CODE\b", re.IGNORECASE)),
    ("INVALID_KEY", re.compile(r"\bINVALID\s+KEY\b", re.IGNORECASE)),
    ("AT_END", re.compile(r"\bAT\s+END\b", re.IGNORECASE)),
    ("ON_SIZE_ERROR", re.compile(r"\bON\s+SIZE\s+ERROR\b", re.IGNORECASE)),
    ("ON_EXCEPTION", re.compile(r"\bON\s+(EXCEPTION|OVERFLOW)\b", re.IGNORECASE)),
]
END_IF_LINE = re.compile(r"^\s*END-IF\b", re.IGNORECASE)
END_EVALUATE_LINE = re.compile(r"^\s*END-EVALUATE\b", re.IGNORECASE)
END_PERFORM_LINE = re.compile(r"^\s*END-PERFORM\b", re.IGNORECASE)
END_STATEMENT = re.compile(r"^\s*(STOP\s+RUN|GOBACK|EXIT\s+PROGRAM)\b", re.IGNORECASE)
INLINE_ERROR_CONDITION = re.compile(
    r"\b(INVALID\s+KEY|AT\s+END|ON\s+SIZE\s+ERROR|ON\s+(EXCEPTION|OVERFLOW))\b",
    re.IGNORECASE,
)


def parse_data_items(code_lines: list[tuple[int, str]]) -> list[dict]:
    """Parse COBOL data declaration lines into normalized items."""
    items = []
    for index, (line_number, text) in enumerate(code_lines):
        match = DATA_ENTRY.match(text)
        if not match:
            continue
        level = int(match.group(1))
        if not (1 <= level <= 49 or level in {66, 77, 88}):
            continue
        entry_text, _ = statement_text(code_lines, index, 4)
        pic_match = PIC.search(entry_text)
        pic = pic_match.group(1).rstrip(".") if pic_match else None
        usage_match = USAGE.search(entry_text)
        redefines_match = REDEFINES.search(entry_text)
        occurs_match = OCCURS.search(entry_text)
        value_match = VALUE.search(entry_text)
        items.append(
            {
                "name": match.group(2).upper(),
                "level": level,
                "pic": pic,
                "usage": usage_match.group(1).upper() if usage_match else None,
                "redefines": redefines_match.group(1).upper() if redefines_match else None,
                "occurs": int(occurs_match.group(1)) if occurs_match else None,
                "value": value_match.group(1)[:40] if value_match else None,
                "line": line_number,
            }
        )
    return items


def build_program_ir(
    content: FileContent,
    rel_path: str,
    declared_names: list[str],
) -> tuple[dict, list[dict]]:
    """Build structured COBOL program data and unparsed ranges."""
    lines = content.code_lines
    divisions = {}
    for division, regex in DIVISION_PATTERNS.items():
        divisions[division] = next(
            (index for index, (_, text) in enumerate(lines) if regex.search(text)),
            None,
        )
    program_match = next(
        (
            (index, match)
            for index, (_, text) in enumerate(lines)
            if (match := PROGRAM_ID.search(text))
        ),
        None,
    )
    name = program_match[1].group(1).upper() if program_match else (
        declared_names[0] if declared_names else ""
    )
    first_line = lines[0][0] if lines else 0
    last_line = lines[-1][0] if lines else 0
    unparsed = []
    if program_match is None:
        unparsed.append(
            {"start": first_line or 1, "end": last_line or 1, "reason": "no PROGRAM-ID"}
        )
    if divisions["procedure"] is None:
        unparsed.append(
            {
                "start": first_line or 1,
                "end": last_line or 1,
                "reason": "no PROCEDURE DIVISION",
            }
        )

    exec_blocks = find_exec_blocks(lines)
    for block in exec_blocks:
        if not block["closed"]:
            unparsed.append(
                {
                    "start": block["start"],
                    "end": block["end"],
                    "reason": "EXEC block not closed",
                }
            )

    paragraphs = (
        _find_paragraphs(lines, divisions["procedure"], name, content.source_format)
        if program_match is not None and divisions["procedure"] is not None
        else []
    )
    files = _find_files(lines, divisions["environment"], divisions["data"])
    record_files = _find_record_files(lines, divisions["data"])
    copybooks = _find_copybooks(lines)
    data_items = []
    if divisions["data"] is not None:
        data_end = divisions["procedure"] or len(lines)
        data_lines = lines[divisions["data"]:data_end]
        data_items = parse_data_items(data_lines)
    linkage = _find_linkage(lines, divisions["procedure"])
    sql_items, cics_items = _build_exec_items(exec_blocks, name, paragraphs)
    calls = _find_calls(lines, exec_blocks, name, paragraphs)
    conditions, events = _build_paragraph_events(
        lines,
        paragraphs,
        exec_blocks,
        sql_items,
        cics_items,
        calls,
        files,
        record_files,
    )
    for file_info in files:
        _fill_file_usage(file_info, events)
    for paragraph in paragraphs:
        paragraph["events"] = events.get(paragraph["name"], [])

    dialect = _dialect(content, exec_blocks, lines)
    metrics = {
        "paragraphs": len(paragraphs),
        "conditions": len(conditions),
        "sql": len(sql_items),
        "cics": len(cics_items),
        "calls": len(calls),
        "lines": len(content.raw_lines),
    }
    program = {
        "id": f"pgm:{name}",
        "name": name,
        "line_span": [first_line, last_line],
        "dialect": dialect,
        "files": files,
        "copybooks": copybooks,
        "data_items": data_items,
        "linkage": linkage,
        "sql": sql_items,
        "cics": cics_items,
        "calls": calls,
        "conditions": conditions,
        "paragraphs": paragraphs,
        "metrics": metrics,
    }
    return program, unparsed


def _find_files(
    lines: list[tuple[int, str]],
    environment_index: int | None,
    data_index: int | None,
) -> list[dict]:
    """Parse SELECT clauses from FILE-CONTROL."""
    files = []
    start_index = environment_index if environment_index is not None else 0
    end_index = data_index if data_index is not None else len(lines)
    for index in range(start_index, end_index):
        match = SELECT.match(lines[index][1])
        if not match:
            continue
        text, end_line = statement_text(lines, index)
        logical_name = match.group(1).upper()
        assign_match = ASSIGN.search(text)
        ddname = assign_match.group(2).upper() if assign_match else None
        if ddname:
            for prefix in ("UT-S-", "DA-S-", "AS-S-", "UT-", "DA-", "AS-", "S-"):
                if ddname.startswith(prefix):
                    ddname = ddname[len(prefix):]
                    break
        organization_match = ORGANIZATION.search(text)
        access_match = ACCESS_MODE.search(text)
        status_match = FILE_STATUS.search(text)
        files.append(
            {
                "logical_name": logical_name,
                "ddname": ddname,
                "organization": (
                    normalize(organization_match.group(1)).upper()
                    if organization_match
                    else None
                ),
                "access_mode": access_match.group(1).upper() if access_match else None,
                "status_var": status_match.group(1).upper() if status_match else None,
                "open_modes": [],
                "operations": [],
                "access": "unknown",
                "lines": [],
                "_end_line": end_line,
            }
        )
    for file_info in files:
        file_info.pop("_end_line")
    return files


def _find_record_files(
    lines: list[tuple[int, str]],
    data_index: int | None,
) -> dict[str, str]:
    """Map FD record names to their associated logical file names."""
    if data_index is None:
        return {}
    in_file_section = False
    current_file = None
    record_files = {}
    for _, text in lines[data_index:]:
        if re.search(r"\bFILE\s+SECTION\b", text, re.IGNORECASE):
            in_file_section = True
            continue
        if in_file_section and SECTION.search(text):
            break
        if not in_file_section:
            continue
        fd_match = FD.match(text)
        if fd_match:
            current_file = fd_match.group(2).upper()
            continue
        record_match = LEVEL_01.match(text)
        if record_match and current_file:
            record_files[record_match.group(1).upper()] = current_file
    return record_files


def _find_copybooks(lines: list[tuple[int, str]]) -> list[dict]:
    """Extract COPY statements and REPLACING indicators."""
    copybooks = []
    for index, (line_number, text) in enumerate(lines):
        match = COPY.match(text)
        if not match:
            continue
        statement, _ = statement_text(lines, index, 3)
        copybooks.append(
            {
                "name": match.group(1).upper(),
                "line": line_number,
                "replacing": bool(COPY_REPLACING.search(statement)),
            }
        )
    return copybooks


def _find_linkage(
    lines: list[tuple[int, str]],
    procedure_index: int | None,
) -> dict:
    """Extract USING parameters from the PROCEDURE DIVISION statement."""
    if procedure_index is None:
        return {"is_subprogram": False, "params": []}
    statement, _ = statement_text(lines, procedure_index, 6)
    using_match = USING.search(statement)
    if not using_match:
        return {"is_subprogram": False, "params": []}
    params = re.findall(r"\b[A-Z][A-Z0-9-]*\b", using_match.group(1), re.IGNORECASE)
    dropped = {"BY", "REFERENCE", "CONTENT", "VALUE", "RETURNING"}
    return {
        "is_subprogram": True,
        "params": [param.upper() for param in params if param.upper() not in dropped],
    }


def _find_paragraphs(
    lines: list[tuple[int, str]],
    procedure_index: int,
    program_name: str,
    source_format: str | None,
) -> list[dict]:
    """Find paragraph and section boundaries after PROCEDURE DIVISION."""
    start_index = procedure_index + 1
    headers = []
    for index in range(start_index, len(lines)):
        line_number, text = lines[index]
        stripped = text.strip()
        if source_format == "fixed" and len(text) - len(text.lstrip()) > 3:
            continue
        is_header = bool(PARAGRAPH.match(stripped) or SECTION_HEADER.match(stripped))
        if is_header and stripped.rstrip(".").upper() not in NOT_PARAGRAPH:
            header_name = stripped.split()[0].rstrip(".").upper()
            headers.append((index, line_number, header_name))

    paragraphs = []
    code_before_first_header = lines[start_index:headers[0][0]] if headers else lines[start_index:]
    if any(text.strip() for _, text in code_before_first_header):
        first_code_line = next(number for number, text in code_before_first_header if text.strip())
        last_line = lines[headers[0][0] - 1][0] if headers else (
            lines[-1][0] if lines else first_code_line
        )
        paragraphs.append(
            {
                "id": f"para:{program_name}.(START)",
                "name": "(START)",
                "line_start": first_code_line,
                "line_end": last_line,
                "events": [],
                "_start_index": start_index,
            }
        )
    for header_number, (index, line_number, name) in enumerate(headers):
        next_index = headers[header_number + 1][0] if header_number + 1 < len(headers) else len(lines)
        end_line = lines[next_index - 1][0] if next_index > index else line_number
        paragraphs.append(
            {
                "id": f"para:{program_name}.{name}",
                "name": name,
                "line_start": line_number,
                "line_end": end_line,
                "events": [],
                "_start_index": index + 1,
            }
        )
    return paragraphs


def _build_exec_items(
    blocks: list[dict],
    program_name: str,
    paragraphs: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Build normalized SQL and CICS block records."""
    sql_items = []
    cics_items = []
    counts = {"SQL": 0, "CICS": 0}
    declared_cursors = {}
    pending = []
    for block in blocks:
        kind = block["kind"]
        counts[kind] += 1
        if kind == "SQL":
            item = _sql_item(block, program_name, counts[kind], paragraphs)
            sql_items.append(item)
            if item["kind"] == "declare_cursor" and item["cursor"]:
                declared_cursors[item["cursor"]] = item
            else:
                pending.append(item)
        else:
            cics_items.append(_cics_item(block, program_name, counts[kind], paragraphs))
    for item in pending:
        if item["kind"] not in {"open", "fetch", "close"} or not item["cursor"]:
            continue
        declaration = declared_cursors.get(item["cursor"])
        if declaration:
            item["tables"] = list(declaration["tables"])
            item["access"] = declaration["access"]
    return sql_items, cics_items


def _sql_item(
    block: dict,
    program_name: str,
    order: int,
    paragraphs: list[dict],
) -> dict:
    """Parse one SQL block into its IR fields."""
    text = block["text"]
    first = text.split(maxsplit=1)[0].upper() if text else ""
    if first == "DECLARE" and re.search(r"\bCURSOR\b", text, re.IGNORECASE):
        kind = "declare_cursor"
    else:
        kind = {
            "SELECT": "select",
            "INSERT": "insert",
            "UPDATE": "update",
            "DELETE": "delete",
            "OPEN": "open",
            "FETCH": "fetch",
            "CLOSE": "close",
            "INCLUDE": "include",
            "COMMIT": "commit",
            "ROLLBACK": "rollback",
        }.get(first, "other")
    dynamic = first in {"PREPARE", "EXECUTE"}
    cursor = None
    if kind == "declare_cursor":
        match = CURSOR_DECLARE.search(text)
        cursor = match.group(1).upper() if match else None
    elif kind in {"open", "close"}:
        match = CURSOR_OPEN.search(text)
        cursor = match.group(1).upper() if match else None
    elif kind == "fetch":
        match = CURSOR_FETCH.search(text)
        cursor = match.group(1).upper() if match else None

    tables = [] if dynamic else _sql_tables(kind, text)
    access = (
        "read"
        if kind in {"select", "declare_cursor"}
        else "write"
        if kind in {"insert", "update", "delete"}
        else None
    )
    include_match = INCLUDE_NAME.search(text) if kind == "include" else None
    host_vars = list(dict.fromkeys(match.group(1).upper() for match in HOST_VAR.finditer(text)))
    return {
        "id": f"sql:{program_name}.{order}",
        "kind": "other" if dynamic else kind,
        "tables": tables,
        "access": access,
        "cursor": cursor,
        "host_vars": host_vars,
        "include": include_match.group(1).upper() if include_match else None,
        "dynamic": dynamic,
        "paragraph": paragraph_of(paragraphs, block["start"]),
        "line_span": [block["start"], block["end"]],
    }


def _sql_tables(kind: str, text: str) -> list[str]:
    """Extract table names from supported SQL clauses."""
    names = []
    if kind == "insert":
        match = re.search(r"\bINTO\s+([A-Z0-9_.$#@]+)", text, re.IGNORECASE)
        if match:
            names.append(match.group(1).upper())
    elif kind == "update":
        match = re.search(r"\bUPDATE\s+([A-Z0-9_.$#@]+)", text, re.IGNORECASE)
        if match:
            names.append(match.group(1).upper())
    elif kind == "delete":
        match = re.search(r"\bDELETE\s+FROM\s+([A-Z0-9_.$#@]+)", text, re.IGNORECASE)
        if match:
            names.append(match.group(1).upper())
    elif kind in {"select", "declare_cursor"}:
        from_match = FROM_CLAUSE.search(text)
        if from_match:
            for part in from_match.group(1).split(","):
                part = part.strip()
                if not part or part.startswith(("(", ":")):
                    continue
                token = TABLE_TOKEN.match(part)
                if token:
                    names.append(token.group(0).upper())
        names.extend(match.group(1).upper() for match in JOIN.finditer(text))
    return list(dict.fromkeys(names))


def _cics_item(
    block: dict,
    program_name: str,
    order: int,
    paragraphs: list[dict],
) -> dict:
    """Parse one CICS block into command and option fields."""
    text = block["text"]
    words = text.split()
    command_match = CICS_TWO_WORD_COMMAND.match(text)
    command = (
        command_match.group(0).upper()
        if command_match
        else words[0].upper() if words else ""
    )
    values = {}
    dynamic = False
    for key, regex in CICS_OPTION.items():
        match = regex.search(text)
        values[key] = match.group(2).upper() if match else None
        if match and not match.group(1):
            dynamic = True
    return {
        "id": f"cics:{program_name}.{order}",
        "command": command,
        "map": values["map"],
        "mapset": values["mapset"],
        "program": values["program"],
        "transid": values["transid"],
        "file": values["file"],
        "queue": values["queue"],
        "dynamic": dynamic,
        "paragraph": paragraph_of(paragraphs, block["start"]),
        "line": block["start"],
    }


def _find_calls(
    lines: list[tuple[int, str]],
    blocks: list[dict],
    program_name: str,
    paragraphs: list[dict],
) -> list[dict]:
    """Extract CALL statements and their USING arguments."""
    blocked = _blocked_line_numbers(blocks)
    calls = []
    for index, (line_number, text) in enumerate(lines):
        if line_number in blocked:
            continue
        match = CALL.search(text)
        if not match:
            continue
        target = (match.group(2) or match.group(3)).upper()
        joined, _ = statement_text(lines, index, 6)
        using_match = USING.search(joined)
        args_text = using_match.group(1) if using_match else ""
        args_text = re.split(
            r"\b(?:ON\s+EXCEPTION|ON\s+OVERFLOW|END-CALL|RETURNING)\b",
            args_text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        args_text = DROP_USING.sub("", args_text)
        args = list(
            dict.fromkeys(
                name.upper()
                for name in re.findall(r"\b[A-Z][A-Z0-9-]*\b", args_text, re.IGNORECASE)
                if name.upper() not in {"USING", "BY", "REFERENCE", "CONTENT", "VALUE"}
            )
        )
        calls.append(
            {
                "id": f"call:{program_name}.{len(calls) + 1}",
                "target": target,
                "dynamic": bool(match.group(3)),
                "args": args,
                "paragraph": paragraph_of(paragraphs, line_number),
                "line": line_number,
            }
        )
    return calls


def _build_paragraph_events(
    lines: list[tuple[int, str]],
    paragraphs: list[dict],
    blocks: list[dict],
    sql_items: list[dict],
    cics_items: list[dict],
    calls: list[dict],
    files: list[dict],
    record_files: dict[str, str],
) -> tuple[list[dict], dict[str, list[dict]]]:
    """Build conditions and ordered events for every paragraph."""
    all_conditions = []
    events_by_paragraph = {}
    block_by_start = {block["start"]: block for block in blocks}
    block_lines = _blocked_line_numbers(blocks)
    sql_by_line = {item["line_span"][0]: item for item in sql_items}
    cics_by_line = {item["line"]: item for item in cics_items}
    calls_by_line = {call["line"]: call for call in calls}
    file_names = {file_info["logical_name"] for file_info in files}
    status_vars = {
        file_info["status_var"]: file_info["logical_name"]
        for file_info in files
        if file_info["status_var"]
    }

    for paragraph in paragraphs:
        paragraph_events = []
        stack = []
        seq = 0
        for line_number, text in lines:
            if not (paragraph["line_start"] <= line_number <= paragraph["line_end"]):
                continue
            if line_number in block_lines:
                if line_number in block_by_start:
                    block = block_by_start[line_number]
                    item = sql_by_line.get(line_number) if block["kind"] == "SQL" else cics_by_line.get(line_number)
                    if item:
                        event_kind = "sql" if block["kind"] == "SQL" else "cics"
                        _append_event(
                            paragraph_events,
                            seq,
                            event_kind,
                            line_number,
                            _under(stack),
                            ref=item["id"],
                        )
                        seq += 1
                        if event_kind == "cics" and item["command"] == "RETURN":
                            _append_event(
                                paragraph_events,
                                seq,
                                "end",
                                line_number,
                                _under(stack),
                                how="CICS_RETURN",
                            )
                            seq += 1
                continue

            condition_match = IF.match(text)
            if condition_match:
                condition = _new_condition(
                    all_conditions,
                    program_name=paragraph["id"].split(":", 1)[-1].split(".", 1)[0],
                    kind="IF",
                    text=condition_match.group(1),
                    paragraph=paragraph["name"],
                    parent=_under(stack),
                    line_number=line_number,
                )
                stack.append({"type": "IF", "condition": condition})
            evaluate_match = EVALUATE.match(text)
            if evaluate_match:
                condition = _new_condition(
                    all_conditions,
                    program_name=paragraph["id"].split(":", 1)[-1].split(".", 1)[0],
                    kind="EVALUATE",
                    text=evaluate_match.group(1),
                    paragraph=paragraph["name"],
                    parent=_under(stack),
                    line_number=line_number,
                )
                stack.append({"type": "EVALUATE", "condition": condition})
            when_match = WHEN.match(text)
            if when_match and stack and stack[-1]["type"] == "EVALUATE":
                previous_when = stack[-1].get("when")
                if previous_when:
                    previous_when["line_span"][1] = max(
                        previous_when["line_span"][0],
                        line_number - 1,
                    )
                condition = _new_condition(
                    all_conditions,
                    program_name=paragraph["id"].split(":", 1)[-1].split(".", 1)[0],
                    kind="WHEN",
                    text=when_match.group(1),
                    paragraph=paragraph["name"],
                    parent=stack[-1]["condition"]["id"],
                    line_number=line_number,
                )
                stack[-1]["when"] = condition
            current_under = _under(stack)

            perform_match = PERFORM.match(text)
            if perform_match and perform_match.group(1).upper() not in {
                "UNTIL", "VARYING", "WITH", "TEST", "FOREVER"
            } and not perform_match.group(1).isdigit():
                thru_match = re.search(
                    r"\b(?:THRU|THROUGH)\s+([A-Z0-9-]+)",
                    text,
                    re.IGNORECASE,
                )
                _append_event(
                    paragraph_events,
                    seq,
                    "perform",
                    line_number,
                    current_under,
                    target=perform_match.group(1).upper(),
                    thru=thru_match.group(1).upper() if thru_match else None,
                    loop=bool(re.search(r"\b(UNTIL|VARYING|TIMES)\b", text, re.IGNORECASE)),
                )
                seq += 1
            goto_match = GOTO.search(text)
            if goto_match:
                _append_event(
                    paragraph_events,
                    seq,
                    "goto",
                    line_number,
                    current_under,
                    target=goto_match.group(1).upper(),
                )
                seq += 1

            file_events = _file_events(
                lines,
                line_number,
                text,
                files,
                file_names,
                record_files,
            )
            for file_event in file_events:
                _append_event(
                    paragraph_events,
                    seq,
                    "file_op",
                    line_number,
                    current_under,
                    **file_event,
                )
                seq += 1

            error = (
                _condition_error(text, status_vars)
                if current_under or INLINE_ERROR_CONDITION.search(text)
                else None
            )
            if error:
                _append_event(
                    paragraph_events,
                    seq,
                    "error_check",
                    line_number,
                    current_under,
                    what=error[0],
                    var=error[1],
                )
                seq += 1

            call = calls_by_line.get(line_number)
            if call:
                _append_event(
                    paragraph_events,
                    seq,
                    "call",
                    line_number,
                    current_under,
                    ref=call["id"],
                )
                seq += 1
                if call["target"] in {"ABEND", "CEE3ABD", "ILBOABN0"}:
                    _append_event(
                        paragraph_events,
                        seq,
                        "end",
                        line_number,
                        current_under,
                        how="ABEND",
                    )
                    seq += 1

            display_match = DISPLAY.match(text)
            if display_match:
                literal = QUOTED.search(display_match.group(1))
                display_text = (
                    literal.group(2)
                    if literal
                    else display_match.group(1).split()[0]
                )
                _append_event(
                    paragraph_events,
                    seq,
                    "display",
                    line_number,
                    current_under,
                    text=display_text[:80],
                )
                seq += 1

            end_match = END_STATEMENT.match(text)
            if end_match:
                how = (
                    "STOP_RUN"
                    if end_match.group(1).upper().startswith("STOP")
                    else "GOBACK"
                    if end_match.group(1).upper() == "GOBACK"
                    else "EXIT_PROGRAM"
                )
                _append_event(
                    paragraph_events,
                    seq,
                    "end",
                    line_number,
                    current_under,
                    how=how,
                )
                seq += 1

            until_match = UNTIL.search(text)
            inline_perform = bool(INLINE_PERFORM.match(text))
            if perform_match and until_match:
                condition = _new_condition(
                    all_conditions,
                    program_name=paragraph["id"].split(":", 1)[-1].split(".", 1)[0],
                    kind="UNTIL",
                    text=until_match.group(1),
                    paragraph=paragraph["name"],
                    parent=current_under,
                    line_number=line_number,
                )
                if inline_perform:
                    stack.append({"type": "PERFORM", "condition": condition})
            elif inline_perform:
                stack.append({"type": "PERFORM", "condition": None})

            if END_IF_LINE.match(text):
                _close_construct(stack, "IF", line_number)
            if END_EVALUATE_LINE.match(text):
                _close_construct(stack, "EVALUATE", line_number)
            if END_PERFORM_LINE.match(text):
                _close_construct(stack, "PERFORM", line_number)
            if text.rstrip().endswith("."):
                _close_period_constructs(stack, line_number)

        _close_constructs_at_paragraph_end(stack, paragraph["line_end"])
        events_by_paragraph[paragraph["name"]] = paragraph_events
    return all_conditions, events_by_paragraph


def _new_condition(
    conditions: list[dict],
    program_name: str,
    kind: str,
    text: str,
    paragraph: str,
    parent: str | None,
    line_number: int,
) -> dict:
    """Create and record a normalized COBOL condition."""
    condition = {
        "id": f"cond:{program_name}.{len(conditions) + 1}",
        "kind": kind,
        "text": _condition_text(text),
        "paragraph": paragraph,
        "parent": parent,
        "line_span": [line_number, line_number],
    }
    conditions.append(condition)
    return condition


def _condition_text(text: str) -> str:
    """Normalize condition text and apply its length limit."""
    return normalize(text.rstrip().rstrip(".").strip())[:120]


def _under(stack: list[dict]) -> str | None:
    """Return the innermost active condition identifier."""
    for construct in reversed(stack):
        if construct.get("when"):
            return construct["when"]["id"]
        condition = construct.get("condition")
        if condition:
            return condition["id"]
    return None


def _close_construct(stack: list[dict], construct_type: str, line_number: int) -> None:
    """Close the nearest matching control construct."""
    for index in range(len(stack) - 1, -1, -1):
        if stack[index]["type"] == construct_type:
            construct = stack.pop(index)
            condition = construct.get("condition")
            if condition:
                condition["line_span"][1] = line_number
            current_when = construct.get("when")
            if current_when:
                current_when["line_span"][1] = line_number
            return


def _close_period_constructs(stack: list[dict], line_number: int) -> None:
    """Close active constructs at a terminating period."""
    while stack:
        construct = stack.pop()
        condition = construct.get("condition")
        if condition:
            condition["line_span"][1] = line_number
        current_when = construct.get("when")
        if current_when:
            current_when["line_span"][1] = line_number


def _close_constructs_at_paragraph_end(
    stack: list[dict],
    line_number: int,
) -> None:
    """Close remaining constructs at a paragraph boundary."""
    _close_period_constructs(stack, line_number)


def _append_event(
    events: list[dict],
    seq: int,
    kind: str,
    line: int,
    under: str | None,
    **fields,
) -> None:
    """Append one sequenced event."""
    event = {"seq": seq + 1, "kind": kind, "line": line, "under": under}
    event.update(fields)
    events.append(event)


def _file_events(
    lines: list[tuple[int, str]],
    line_number: int,
    text: str,
    files: list[dict],
    file_names: set[str],
    record_files: dict[str, str],
) -> list[dict]:
    """Extract OPEN, CLOSE, and file access events from a statement."""
    index = next(
        (index for index, (number, _) in enumerate(lines) if number == line_number),
        0,
    )
    statement, _ = statement_text(lines, index, 6)
    upper = statement.upper()
    results = []
    open_match = OPEN.match(upper)
    if open_match:
        mode = None
        remainder = open_match.group(1)
        tokens = re.findall(r"[A-Z0-9-]+", remainder)
        for token in tokens:
            if token in {"INPUT", "OUTPUT", "I-O", "EXTEND"}:
                mode = token
            elif token in file_names and mode:
                results.append({"op": "OPEN", "file": token, "mode": mode})
    close_match = CLOSE.match(upper)
    if close_match:
        for token in re.findall(r"[A-Z0-9-]+", close_match.group(1)):
            if token in file_names:
                results.append({"op": "CLOSE", "file": token, "mode": None})
    for regex, operation in (
        (READ, "READ"),
        (DELETE, "DELETE"),
        (START, "START"),
    ):
        match = regex.match(text)
        if match:
            results.append({"op": operation, "file": match.group(1).upper(), "mode": None})
    for regex, operation in ((WRITE, "WRITE"), (REWRITE, "REWRITE")):
        match = regex.match(text)
        if match:
            record = match.group(1).upper()
            results.append(
                {
                    "op": operation,
                    "file": record_files.get(record, record),
                    "mode": None,
                }
            )
    return results


def _condition_error(
    text: str,
    status_vars: dict[str, str],
) -> tuple[str, str | None] | None:
    """Identify a supported status or exception check."""
    for what, regex in CONDITION_ERROR_PATTERNS:
        match = regex.search(text)
        if match:
            variable = "SQLCODE" if what == "SQLCODE" else (
                "RETURN-CODE" if what == "RETURN_CODE" else None
            )
            return what, variable
    for status_var in status_vars:
        if re.search(rf"\b{re.escape(status_var)}\b", text, re.IGNORECASE):
            return "FILE_STATUS", status_var
    return None


def _fill_file_usage(file_info: dict, events: dict[str, list[dict]]) -> None:
    """Derive file operations and access from paragraph events."""
    logical_name = file_info["logical_name"]
    file_events = [
        event
        for paragraph_events in events.values()
        for event in paragraph_events
        if event["kind"] == "file_op" and event["file"] == logical_name
    ]
    open_modes = list(
        dict.fromkeys(
            event["mode"]
            for event in file_events
            if event["op"] == "OPEN" and event["mode"]
        )
    )
    operations = list(
        dict.fromkeys(
            event["op"]
            for event in file_events
            if event["op"] in {"READ", "WRITE", "REWRITE", "DELETE", "START"}
        )
    )
    lines = sorted({event["line"] for event in file_events})[:20]
    if operations:
        has_read = bool({"READ", "START"} & set(operations))
        has_write = bool({"WRITE", "REWRITE", "DELETE"} & set(operations))
    else:
        has_read = bool({"INPUT", "I-O"} & set(open_modes))
        has_write = bool({"OUTPUT", "EXTEND", "I-O"} & set(open_modes))
    access = (
        "read_write"
        if has_read and has_write
        else "read"
        if has_read
        else "write"
        if has_write
        else "unknown"
    )
    file_info.update(
        {
            "open_modes": open_modes,
            "operations": operations,
            "access": access,
            "lines": lines,
        }
    )


def _blocked_line_numbers(blocks: list[dict]) -> set[int]:
    """Return all source lines covered by EXEC blocks."""
    return {
        line_number
        for block in blocks
        for line_number in range(block["start"], block["end"] + 1)
    }


def _dialect(
    content: FileContent,
    blocks: list[dict],
    lines: list[tuple[int, str]],
) -> dict:
    """Detect compiler cards and embedded SQL or CICS blocks."""
    card_pattern = re.compile(r"^\s*(CBL|PROCESS)\s+(.*)$", re.IGNORECASE)
    cbl_cards = []
    for raw_line in content.raw_lines[:20]:
        match = card_pattern.match(raw_line)
        if match:
            cbl_cards.append(normalize(match.group(2)))
    copy_replacing = False
    for index, (_, text) in enumerate(lines):
        if COPY.match(text):
            statement, _ = statement_text(lines, index, 3)
            if COPY_REPLACING.search(statement):
                copy_replacing = True
                break
    return {
        "cbl_cards": cbl_cards,
        "uses_sql": any(block["kind"] == "SQL" for block in blocks),
        "uses_cics": any(block["kind"] == "CICS" for block in blocks),
        "copy_replacing": copy_replacing,
    }
