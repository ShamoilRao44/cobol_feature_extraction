import re

PROGRAM_ID = re.compile(r"^\s*PROGRAM-ID\b", re.IGNORECASE)
PROCEDURE_DIVISION = re.compile(r"^\s*PROCEDURE\s+DIVISION", re.IGNORECASE)
IDENTIFICATION_DIVISION = re.compile(
    r"^\s*(IDENTIFICATION|ID)\s+DIVISION", re.IGNORECASE
)
DATA_DIVISION = re.compile(r"^\s*DATA\s+DIVISION", re.IGNORECASE)
ENVIRONMENT_DIVISION = re.compile(r"^\s*ENVIRONMENT\s+DIVISION", re.IGNORECASE)
COBOL_VERB = re.compile(
    r"^\s*(MOVE|PERFORM|IF|EVALUATE|COMPUTE|ADD|SUBTRACT|MULTIPLY|DIVIDE|"
    r"DISPLAY|ACCEPT|READ|WRITE|REWRITE|OPEN|CLOSE|CALL|GO\s+TO|STOP\s+RUN|"
    r"GOBACK|INITIALIZE|STRING|UNSTRING|INSPECT|EXEC\s+SQL|EXEC\s+CICS|"
    r"END-IF|END-EVALUATE|END-PERFORM)(?=\s|\.|$)",
    re.IGNORECASE,
)
COPYBOOK_LEVEL = re.compile(
    r"^\s*(0[1-9]|[1-4][0-9]|66|77|88)\s+([A-Z0-9][A-Z0-9-]*|FILLER)\b",
    re.IGNORECASE,
)
PIC = re.compile(r"\b(PIC|PICTURE)\b", re.IGNORECASE)
SQL_DECLARE_TABLE = re.compile(
    r"EXEC\s+SQL\s+DECLARE\s+\S+\s+TABLE", re.IGNORECASE
)
JCL_SLASH = re.compile(r"^//")
JCL_JOB = re.compile(r"^//\S*\s+JOB\b", re.IGNORECASE)
JCL_EXEC = re.compile(r"^//\S*\s+EXEC\b", re.IGNORECASE)
JCL_DD = re.compile(r"^//\S*\s+DD\b", re.IGNORECASE)
JCL_PROC = re.compile(r"^//\S*\s+PROC\b", re.IGNORECASE)
BMS_DFHMSD = re.compile(r"\bDFHMSD\b", re.IGNORECASE)
BMS_DFHMDI = re.compile(r"\bDFHMDI\b", re.IGNORECASE)
BMS_DFHMDF = re.compile(r"\bDFHMDF\b", re.IGNORECASE)
ASSEMBLER_SECTION = re.compile(r"(?:^|\s)(CSECT|DSECT|RSECT)\b", re.IGNORECASE)
ASSEMBLER_STORAGE = re.compile(
    r"^\S*\s+(DS|DC)\s+\d*[CXFHPAZDEBS]", re.IGNORECASE
)
ASSEMBLER_USING = re.compile(r"\sUSING\s+(\*|\w+,\s*\d+)", re.IGNORECASE)
ASSEMBLER_INSTRUCTION = re.compile(
    r"(?:^|\s)(BALR|BASR|STM|LM|MVC|CLC|LTR|LR|BNZ|BZ|BNE|BE)\s",
    re.IGNORECASE,
)
PLI_MAIN = re.compile(r"OPTIONS\s*\(\s*MAIN", re.IGNORECASE)
PLI_DCL = re.compile(r"^\s*DCL\s", re.IGNORECASE)
PLI_PROC = re.compile(r"^\s*\S+:\s*(PROC|PROCEDURE)\b", re.IGNORECASE)
SQL_EXEC = re.compile(r"EXEC\s+SQL", re.IGNORECASE)
SQL_DDL = re.compile(
    r"^\s*(CREATE|ALTER|DROP)\s+(OR\s+REPLACE\s+)?"
    r"(TABLE|INDEX|VIEW|TABLESPACE|DATABASE|STOGROUP|SEQUENCE|ALIAS|"
    r"SCHEMA|PROCEDURE|TRIGGER|UNIQUE)\b",
    re.IGNORECASE,
)
SQL_OTHER = re.compile(r"^\s*(GRANT|COMMENT\s+ON|COMMIT)\b", re.IGNORECASE)
SQL_DML = re.compile(
    r"^\s*(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b", re.IGNORECASE
)
MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+\S")
MARKDOWN_BULLET = re.compile(r"^\s*[-*+]\s+\S")
MARKDOWN_TABLE = re.compile(r"^\|.*\|\s*$")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\([^)]+\)")
OTHER_SOURCE_PATTERNS = [
    ("python", re.compile(r"^\s*def\s+\w+\(.*\)\s*(->.*)?:\s*$")),
    ("python", re.compile(r"^\s*class\s+\w+.*:\s*$")),
    ("python", re.compile(r"^\s*(import\s+\w+|from\s+[\w.]+\s+import\s)")),
    (
        "java",
        re.compile(
            r"^\s*(public|private|protected)\s+(static\s+)?"
            r"(class|interface|enum|void|[\w<>\[\]]+)\s+\w+"
        ),
    ),
    ("java", re.compile(r"^\s*package\s+[\w.]+;")),
    ("java", re.compile(r"^\s*import\s+[\w.*]+;")),
    ("csharp", re.compile(r"^\s*using\s+[\w.]+;")),
    ("js", re.compile(r"^\s*(const|let|var)\s+\w+\s*=")),
    ("js", re.compile(r"^\s*function\s+\w+\s*\(")),
    ("c", re.compile(r"^\s*#include\s*[<\"]")),
    ("shell", re.compile(r"^#!/")),
    ("xml", re.compile(r"^\s*<\?xml")),
]


def find(
    code_lines: list[tuple[int, str]], regex: re.Pattern[str]
) -> list[tuple[int, str]]:
    """Return code lines matching a compiled regular expression."""
    return [(number, text) for number, text in code_lines if regex.search(text)]


def _evidence(matches: list[tuple[int, str]]) -> list[str]:
    """Format the first five matched lines as evidence."""
    unique_matches = {number: text for number, text in matches}
    first_matches = sorted(unique_matches.items())[:5]
    return [
        f"line {number}: {text.strip()[:80]}"
        for number, text in first_matches
    ]


def score_cobol_program(
    code_lines: list[tuple[int, str]],
) -> tuple[int, list[str]]:
    """Score COBOL program structure."""
    program_ids = find(code_lines, PROGRAM_ID)
    if not program_ids:
        return 0, []

    score = 4
    matches = list(program_ids)
    for regex, points in (
        (PROCEDURE_DIVISION, 4),
        (IDENTIFICATION_DIVISION, 2),
        (DATA_DIVISION, 1),
        (ENVIRONMENT_DIVISION, 1),
    ):
        found = find(code_lines, regex)
        if found:
            score += points
            matches.extend(found)
    evidence = _evidence(matches)
    if len(program_ids) >= 2:
        evidence = evidence[:4] + [
            f"{len(program_ids)} PROGRAM-ID lines (multiple programs)"
        ]
    return score, evidence


def score_cobol_fragment(
    code_lines: list[tuple[int, str]],
) -> tuple[int, list[str]]:
    """Score standalone COBOL procedure fragments."""
    if find(code_lines, PROGRAM_ID):
        return 0, []

    procedures = find(code_lines, PROCEDURE_DIVISION)
    verbs = [
        (number, text)
        for number, text in find(code_lines, COBOL_VERB)
        if not text.strip().endswith((":", "{", ";"))
    ]
    score = (4 if procedures else 0) + min(len(verbs), 10)
    return score, _evidence(procedures + verbs)


def score_copybook(code_lines: list[tuple[int, str]]) -> tuple[int, list[str]]:
    """Score COBOL data declarations."""
    if find(code_lines, PROGRAM_ID) or find(code_lines, PROCEDURE_DIVISION):
        return 0, []

    levels = find(code_lines, COPYBOOK_LEVEL)
    if len(levels) < 2:
        return 0, []
    pictures = find(code_lines, PIC)
    declarations = find(code_lines, SQL_DECLARE_TABLE)
    score = min(len(levels), 8) + (2 if pictures else 0) + (3 if declarations else 0)
    return score, _evidence(levels + pictures + declarations)


def score_jcl(code_lines: list[tuple[int, str]]) -> tuple[int, list[str]]:
    """Score JCL jobs."""
    slash_lines = find(code_lines, JCL_SLASH)
    jobs = find(code_lines, JCL_JOB)
    if not jobs or len(slash_lines) < 2:
        return 0, []

    executes = find(code_lines, JCL_EXEC)
    data_definitions = find(code_lines, JCL_DD)
    score = 5 + (3 if executes else 0) + min(len(data_definitions), 4)
    return score, _evidence(jobs + executes + data_definitions)


def score_jcl_proc(code_lines: list[tuple[int, str]]) -> tuple[int, list[str]]:
    """Score JCL procedure members."""
    if find(code_lines, JCL_JOB):
        return 0, []

    slash_lines = find(code_lines, JCL_SLASH)
    if len(slash_lines) < 2 or len(slash_lines) < 0.5 * len(code_lines):
        return 0, []
    procedures = find(code_lines, JCL_PROC)
    executes = find(code_lines, JCL_EXEC)
    data_definitions = find(code_lines, JCL_DD)
    score = (
        (5 if procedures else 0)
        + (3 if executes else 0)
        + min(len(data_definitions), 4)
    )
    return score, _evidence(procedures + executes + data_definitions)


def score_bms_map(code_lines: list[tuple[int, str]]) -> tuple[int, list[str]]:
    """Score BMS map definitions."""
    maps = find(code_lines, BMS_DFHMSD)
    identifiers = find(code_lines, BMS_DFHMDI)
    fields = find(code_lines, BMS_DFHMDF)
    score = (5 if maps else 0) + (3 if identifiers else 0) + min(len(fields), 5)
    return score, _evidence(maps + identifiers + fields)


def score_assembler(code_lines: list[tuple[int, str]]) -> tuple[int, list[str]]:
    """Score assembler sections, storage, and instructions."""
    if find(code_lines, BMS_DFHMSD):
        return 0, []

    sections = find(code_lines, ASSEMBLER_SECTION)
    storage = find(code_lines, ASSEMBLER_STORAGE)
    using = find(code_lines, ASSEMBLER_USING)
    instructions = find(code_lines, ASSEMBLER_INSTRUCTION)
    score = (
        (4 if sections else 0)
        + min(len(storage), 4)
        + (2 if using else 0)
        + min(len(instructions), 4)
    )
    return score, _evidence(sections + storage + using + instructions)


def score_pli(code_lines: list[tuple[int, str]]) -> tuple[int, list[str]]:
    """Score PL/I declarations and procedures."""
    main_options = find(code_lines, PLI_MAIN)
    declarations = find(code_lines, PLI_DCL)
    procedures = find(code_lines, PLI_PROC)
    score = (6 if main_options else 0) + min(len(declarations), 5) + (
        3 if procedures else 0
    )
    return score, _evidence(main_options + declarations + procedures)


def score_sql(code_lines: list[tuple[int, str]]) -> tuple[int, list[str]]:
    """Score standalone SQL statements."""
    if find(code_lines, SQL_EXEC):
        return 0, []

    ddl = find(code_lines, SQL_DDL)
    other = find(code_lines, SQL_OTHER)
    semicolons = [
        (number, text)
        for number, text in code_lines
        if text.strip().endswith(";")
    ]
    dml = find(code_lines, SQL_DML)
    score = min(3 * len(ddl), 12) + min(len(other), 3)
    if len(semicolons) >= 2:
        score += min(len(dml), 4)
    return score, _evidence(ddl + other + (dml if len(semicolons) >= 2 else []))


def score_other_source(
    code_lines: list[tuple[int, str]],
) -> tuple[int, list[str]]:
    """Score common non-mainframe source syntax."""
    matches = []
    for number, text in code_lines:
        for language, regex in OTHER_SOURCE_PATTERNS:
            if regex.search(text):
                matches.append((language, number, text))
    evidence = [
        f"{language} line {number}: {text.strip()[:80]}"
        for language, number, text in matches[:5]
    ]
    return min(2 * len(matches), 10), evidence


def markdown_counts(code_lines: list[tuple[int, str]]) -> dict[str, int]:
    """Count common Markdown structures."""
    lines = [text for _, text in code_lines]
    return {
        "headings": len(find(code_lines, MARKDOWN_HEADING)),
        "fences": sum(line.startswith("```") for line in lines),
        "bullets": len(find(code_lines, MARKDOWN_BULLET)),
        "tables": len(find(code_lines, MARKDOWN_TABLE)),
        "links": len(find(code_lines, MARKDOWN_LINK)),
    }


def looks_like_markdown(code_lines: list[tuple[int, str]]) -> bool:
    """Check whether content has a characteristic Markdown structure."""
    counts = markdown_counts(code_lines)
    return counts["fences"] >= 2 or (
        counts["headings"] >= 2
        and counts["bullets"] + counts["tables"] + counts["links"] >= 2
    )


def score_documentation(
    code_lines: list[tuple[int, str]],
) -> tuple[int, list[str]]:
    """Score Markdown documentation structures."""
    counts = markdown_counts(code_lines)
    score = (
        min(2 * counts["headings"], 6)
        + min(2 * counts["fences"], 6)
        + min(counts["bullets"], 4)
        + min(counts["tables"], 3)
        + min(counts["links"], 3)
    )
    matches = []
    for regex in (MARKDOWN_HEADING, MARKDOWN_BULLET, MARKDOWN_TABLE, MARKDOWN_LINK):
        matches.extend(find(code_lines, regex))
    matches.extend(
        (number, text)
        for number, text in code_lines
        if text.startswith("```")
    )
    return score, _evidence(matches)


SCORERS = {
    "cobol_program": score_cobol_program,
    "cobol_fragment": score_cobol_fragment,
    "copybook": score_copybook,
    "jcl": score_jcl,
    "jcl_proc": score_jcl_proc,
    "bms_map": score_bms_map,
    "assembler": score_assembler,
    "pli": score_pli,
    "sql": score_sql,
    "other_source": score_other_source,
    "documentation": score_documentation,
}
