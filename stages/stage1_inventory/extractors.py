import os
import re

from stages.stage1_inventory.models import FileContent

PROGRAM_NAME = re.compile(
    r"^\s*PROGRAM-ID\.?\s+['\"]?([A-Z0-9][A-Z0-9-]*)",
    re.IGNORECASE,
)
JCL_JOB_NAME = re.compile(r"^//([A-Z0-9#@$]+)\s+JOB\b", re.IGNORECASE)
JCL_PROC_NAME = re.compile(r"^//([A-Z0-9#@$]+)\s+PROC\b", re.IGNORECASE)
BMS_MAPSET_NAME = re.compile(r"^([A-Z0-9#@$]+)\s+DFHMSD\b", re.IGNORECASE)
BMS_MAP_NAME = re.compile(r"^([A-Z0-9#@$]+)\s+DFHMDI\b", re.IGNORECASE)
ASSEMBLER_NAME = re.compile(
    r"^([A-Z0-9#@$]+)\s+(CSECT|RSECT|START)\b",
    re.IGNORECASE,
)
PLI_NAME = re.compile(
    r"^\s*([A-Z0-9#@$_]+)\s*:\s*(PROC|PROCEDURE)\b",
    re.IGNORECASE,
)
COPY_REFERENCE = re.compile(r"^\s*COPY\s+[\"']?([A-Z0-9][A-Z0-9_-]*)", re.IGNORECASE)
SQL_INCLUDE = re.compile(
    r"EXEC\s+SQL\s+INCLUDE\s+([A-Z0-9][A-Z0-9_-]*)",
    re.IGNORECASE,
)
CALL_REFERENCE = re.compile(
    r"\bCALL\s+(?:(['\"])([A-Z0-9#@$_-]+)\1|([A-Z][A-Z0-9-]*))",
    re.IGNORECASE,
)
EXEC_START = re.compile(r"\bEXEC\s+(CICS|SQL)\b", re.IGNORECASE)
EXEC_END = re.compile(r"\bEND-EXEC\b", re.IGNORECASE)
CICS_LINK = re.compile(
    r"\bEXEC\s+CICS\s+LINK\b.*?\bPROGRAM\s*\(\s*(['\"]?)([A-Z0-9#@$_-]+)\1\s*\)",
    re.IGNORECASE,
)
CICS_XCTL = re.compile(
    r"\bEXEC\s+CICS\s+XCTL\b.*?\bPROGRAM\s*\(\s*(['\"]?)([A-Z0-9#@$_-]+)\1\s*\)",
    re.IGNORECASE,
)
CICS_MAP_ACTION = re.compile(
    r"\bEXEC\s+CICS\s+(?:SEND|RECEIVE)\b.*?\bMAP\b",
    re.IGNORECASE,
)
CICS_MAPSET = re.compile(r"\bMAPSET\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.IGNORECASE)
CICS_MAP = re.compile(r"\bMAP\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.IGNORECASE)
CICS_TRANSID = re.compile(
    r"\bEXEC\s+CICS\s+RETURN\b.*?\bTRANSID\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    re.IGNORECASE,
)
JCL_PGM_REFERENCE = re.compile(
    r"^//\S*\s+EXEC\s+PGM=([A-Z0-9#@$]+)",
    re.IGNORECASE,
)
JCL_PROC_REFERENCE = re.compile(
    r"^//\S*\s+EXEC\s+(?:PROC=)?([A-Z0-9#@$]+)",
    re.IGNORECASE,
)
JCL_INCLUDE_REFERENCE = re.compile(
    r"^//\S*\s+INCLUDE\s+MEMBER=([A-Z0-9#@$]+)",
    re.IGNORECASE,
)


def _normalize(name: str) -> str:
    """Strip and uppercase an extracted name."""
    return name.strip().upper()


def _reference(kind: str, name: str, line: int, dynamic: bool = False) -> dict:
    """Create a normalized reference record."""
    return {
        "kind": kind,
        "name": _normalize(name),
        "line": line,
        "dynamic": dynamic,
    }


def exec_blocks(code_lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Join EXEC CICS and EXEC SQL statements across source lines."""
    blocks = []
    index = 0
    while index < len(code_lines):
        line_number, text = code_lines[index]
        if not EXEC_START.search(text):
            index += 1
            continue

        statement = []
        end_index = index
        for offset in range(15):
            current_index = index + offset
            if current_index >= len(code_lines):
                break
            current_text = code_lines[current_index][1]
            statement.append(current_text)
            end_index = current_index
            if EXEC_END.search(current_text):
                break
        blocks.append((line_number, " ".join(statement)))
        index = end_index + 1
    return blocks


def extract(
    content: FileContent,
    file_type: str,
    rel_path: str,
) -> tuple[list[str], list[dict]]:
    """Extract declared names and references from file content."""
    code_lines = content.code_lines
    declared_names = []
    if file_type == "cobol_program":
        declared_names = [
            _normalize(match.group(1))
            for _, text in code_lines
            if (match := PROGRAM_NAME.search(text))
        ]
    elif file_type == "jcl":
        declared_names = [
            _normalize(match.group(1))
            for _, text in code_lines
            if (match := JCL_JOB_NAME.search(text))
        ][:1]
    elif file_type == "jcl_proc":
        declared_names = [
            _normalize(match.group(1))
            for _, text in code_lines
            if (match := JCL_PROC_NAME.search(text))
        ][:1]
        if not declared_names:
            declared_names = [
                _normalize(os.path.splitext(os.path.basename(rel_path))[0])
            ]
    elif file_type == "bms_map":
        for regex in (BMS_MAPSET_NAME, BMS_MAP_NAME):
            declared_names.extend(
                _normalize(match.group(1))
                for line in content.raw_lines
                if (match := regex.search(line))
            )
    elif file_type == "assembler":
        declared_names = [
            _normalize(match.group(1))
            for line in content.raw_lines
            if (match := ASSEMBLER_NAME.search(line))
        ]
    elif file_type == "pli":
        declared_names = [
            _normalize(match.group(1))
            for _, text in code_lines
            if (match := PLI_NAME.search(text))
        ][:1]
    elif file_type in {"copybook", "cobol_fragment"}:
        declared_names = [
            _normalize(os.path.splitext(os.path.basename(rel_path))[0])
        ]

    references = _extract_references(code_lines, file_type)
    return declared_names, references


def _extract_references(
    code_lines: list[tuple[int, str]],
    file_type: str,
) -> list[dict]:
    """Extract supported references from executable file types."""
    if file_type not in {
        "cobol_program",
        "cobol_fragment",
        "copybook",
        "jcl",
        "jcl_proc",
    }:
        return []

    references = []
    blocks = exec_blocks(code_lines)
    block_lines = set()
    for line_number, joined_text in blocks:
        start_index = next(
            (
                index
                for index, (number, _) in enumerate(code_lines)
                if number == line_number
            ),
            None,
        )
        if start_index is not None:
            for number, text in code_lines[start_index:start_index + 15]:
                block_lines.add(number)
                if EXEC_END.search(text):
                    break
        for match in SQL_INCLUDE.finditer(joined_text):
            references.append(_reference("sql_include", match.group(1), line_number))
        for regex, kind in ((CICS_LINK, "cics_link"), (CICS_XCTL, "cics_xctl")):
            for match in regex.finditer(joined_text):
                quoted = bool(match.group(1))
                references.append(
                    _reference(kind, match.group(2), line_number, not quoted)
                )
        if CICS_MAP_ACTION.search(joined_text):
            match = CICS_MAPSET.search(joined_text) or CICS_MAP.search(joined_text)
            if match:
                references.append(
                    _reference("cics_map", match.group(1), line_number)
                )
        for match in CICS_TRANSID.finditer(joined_text):
            references.append(
                _reference("cics_transid", match.group(1), line_number)
            )

    for line_number, text in code_lines:
        if line_number in block_lines:
            continue
        if file_type in {"cobol_program", "cobol_fragment", "copybook"}:
            for match in COPY_REFERENCE.finditer(text):
                references.append(_reference("copy", match.group(1), line_number))
            for match in CALL_REFERENCE.finditer(text):
                name = match.group(2) or match.group(3)
                references.append(
                    _reference("call", name, line_number, bool(match.group(3)))
                )
        if file_type in {"jcl", "jcl_proc"}:
            for match in JCL_PGM_REFERENCE.finditer(text):
                references.append(_reference("jcl_pgm", match.group(1), line_number))
            if not JCL_PGM_REFERENCE.search(text):
                for match in JCL_PROC_REFERENCE.finditer(text):
                    references.append(_reference("jcl_proc", match.group(1), line_number))
            for match in JCL_INCLUDE_REFERENCE.finditer(text):
                references.append(
                    _reference("jcl_include", match.group(1), line_number)
                )
    return references
