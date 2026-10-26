import os
import re

from charset_normalizer import from_bytes

from stages.stage1_inventory.models import FileContent

MAX_FILE_SIZE = 10 * 1024 * 1024
SKIPPED_FIXED_INDICATORS = {"*", "/"}
FIXED_INDICATORS = {" ", "*", "/", "-", "D", "d"}
FREE_FORMAT_DIRECTIVE = re.compile(r"^\s*>>\s*SOURCE\s+FORMAT\s+(IS\s+)?FREE", re.IGNORECASE)
FIXED_SEQUENCE = re.compile(r"^[ 0-9A-Za-z]{6}$")


def read_file(path: str) -> FileContent:
    """Read and classify a text file without using its name or extension."""
    if os.path.getsize(path) > MAX_FILE_SIZE:
        return FileContent(path, "too_large", None, "none", None, [], [])

    with open(path, "rb") as source:
        data = source.read()

    if b"\x00" in data[:8192]:
        return FileContent(path, "binary", None, "none", None, [], [])

    records = None
    try:
        text = data.decode("utf-8-sig")
        encoding = "utf-8"
    except UnicodeDecodeError:
        ebcdic_text = data.decode("cp037")
        printable_count = sum(
            character.isprintable() or character.isspace()
            for character in ebcdic_text
        )
        is_ebcdic = (
            data
            and data.count(b"\x40") / len(data) >= 0.1
            and printable_count / len(ebcdic_text) >= 0.98
        )
        if is_ebcdic:
            text = ebcdic_text.replace("\x85", "\n")
            encoding = "cp037"
            if "\n" not in text and len(text) % 80 == 0:
                records = [text[index:index + 80] for index in range(0, len(text), 80)]
        else:
            match = from_bytes(data).best()
            if match is None:
                text = data.decode("latin-1")
                encoding = "latin-1"
            else:
                text = str(match)
                encoding = match.encoding

    if records is not None:
        line_ending = "none"
        lines = records
    else:
        crlf_count = text.count("\r\n")
        lf_count = text.count("\n") - crlf_count
        cr_count = text.count("\r") - crlf_count
        ending_count = sum(count > 0 for count in (crlf_count, lf_count, cr_count))
        if ending_count > 1:
            line_ending = "mixed"
        elif crlf_count:
            line_ending = "CRLF"
        elif lf_count:
            line_ending = "LF"
        elif cr_count:
            line_ending = "CR"
        else:
            line_ending = "none"
        lines = text.splitlines()

    raw_lines = [line.expandtabs(8) for line in lines]
    source_format = _detect_source_format(raw_lines)
    code_lines = _clean_code_lines(raw_lines, source_format)
    return FileContent(path, "text", encoding, line_ending, source_format, raw_lines, code_lines)


def _detect_source_format(lines: list[str]) -> str:
    """Detect free or fixed source layout from line content."""
    if any(FREE_FORMAT_DIRECTIVE.match(line) for line in lines[:50]):
        return "free"

    candidates = [line for line in lines if line.strip() and len(line) >= 7]
    fixed_count = sum(
        bool(FIXED_SEQUENCE.match(line[:6])) and line[6] in FIXED_INDICATORS
        for line in candidates
    )
    if len(candidates) >= 3 and fixed_count / len(candidates) >= 0.8:
        return "fixed"
    return "free"


def _clean_code_lines(lines: list[str], source_format: str) -> list[tuple[int, str]]:
    """Remove blank lines and comments while preserving original line numbers."""
    code_lines = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        if source_format == "fixed":
            if len(line) < 7 or line[6] in SKIPPED_FIXED_INDICATORS:
                continue
            code = line[7:72].rstrip()
        else:
            code = line.rstrip()
            if code.lstrip().startswith(("*>", "//*")):
                continue
            comment_start = code.find(" *>")
            if comment_start >= 0:
                code = code[:comment_start].rstrip()

        if code.strip():
            code_lines.append((line_number, code))
    return code_lines
