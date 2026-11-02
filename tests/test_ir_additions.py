from stages.stage1_inventory.reader import read_file
from stages.stage2_ir.cobol_ir import build_program_ir


def build_program(tmp_path, lines, source_format="fixed"):
    """Build a COBOL IR document from source lines."""
    path = tmp_path / "program.cbl"
    path.write_text("\n".join(lines), encoding="utf-8")
    content = read_file(str(path))
    content.source_format = source_format
    return build_program_ir(content, "program.cbl", ["TESTPGM"])[0]


def test_copybooks_track_sections(tmp_path):
    """Record the COBOL section containing each COPY statement."""
    program = build_program(
        tmp_path,
        [
            "       IDENTIFICATION DIVISION.",
            "       PROGRAM-ID. TESTPGM.",
            "       DATA DIVISION.",
            "       WORKING-STORAGE SECTION.",
            "       COPY ACCTREC.",
            "       LINKAGE SECTION.",
            "       COPY PARMREC.",
            "       PROCEDURE DIVISION.",
            "       COPY PROCOPY.",
        ],
    )
    assert [item["section"] for item in program["copybooks"]] == [
        "WORKING-STORAGE",
        "LINKAGE",
        "PROCEDURE",
    ]


def test_cics_whitespace_commarea_and_missing_target(tmp_path):
    """Parse spaced CICS operands and report missing program targets."""
    program = build_program(
        tmp_path,
        [
            "       IDENTIFICATION DIVISION.",
            "       PROGRAM-ID. TESTPGM.",
            "       PROCEDURE DIVISION.",
            "       MAIN-PARA.",
            "           EXEC CICS LINK PROGRAM ( 'CIPTMON' )",
            "                COMMAREA(WS-COMM) END-EXEC.",
            "           EXEC CICS LINK END-EXEC.",
        ],
    )
    assert program["cics"][0]["program"] == "CIPTMON"
    assert program["cics"][0]["commarea"] == "WS-COMM"
    assert program["cics"][0]["dynamic"] is False
    assert program["issues"] == [
        {
            "kind": "cics_target_missing",
            "line": program["cics"][1]["line"],
            "detail": "LINK",
        }
    ]


def test_dynamic_call_candidates_and_literal_call(tmp_path):
    """Resolve literal candidates for a dynamic call in source-line order."""
    program = build_program(
        tmp_path,
        [
            "       IDENTIFICATION DIVISION.",
            "       PROGRAM-ID. TESTPGM.",
            "       DATA DIVISION.",
            "       WORKING-STORAGE SECTION.",
            "       01 WS-PGM PIC X(8) VALUE 'SUBC'.",
            "       PROCEDURE DIVISION.",
            "       MAIN-PARA.",
            "           MOVE 'SUBA' TO WS-PGM.",
            "           MOVE 'SUBB' TO WS-PGM.",
            "           CALL WS-PGM.",
            "           CALL 'SUBX'.",
        ],
    )
    assert program["calls"][0]["dynamic"] is True
    assert program["calls"][0]["candidates"] == [
        {"value": "SUBC", "line": 5, "how": "value"},
        {"value": "SUBA", "line": 8, "how": "move"},
        {"value": "SUBB", "line": 9, "how": "move"},
    ]
    assert program["calls"][1]["candidates"] == []


def test_cics_queue_scope_and_candidate_values(tmp_path):
    """Classify queue references as shared, private, or unresolved."""
    lines = [
        "       IDENTIFICATION DIVISION.",
        "       PROGRAM-ID. TESTPGM.",
        "       DATA DIVISION.",
        "       WORKING-STORAGE SECTION.",
        "       05 QUEUENAME.",
        "          10 QUEUENAME-TRANS PIC X(4).",
        "          10 QUEUENAME-TERM PIC X(4).",
        "       PROCEDURE DIVISION.",
        "       MAIN-PARA.",
        "           EXEC CICS DELETEQ TS QUEUE(QUEUENAME) END-EXEC.",
    ]
    program = build_program(
        tmp_path,
        lines[:7] + ["       01 WS-DUMMY PIC X."] + lines[7:],
    )
    assert program["cics"][0]["dynamic"] is True
    assert program["cics"][0]["queue_scope"] == "unknown"

    program = build_program(
        tmp_path,
        lines[:7]
        + ["       01 WS-DUMMY PIC X."]
        + lines[7:9]
        + ["           MOVE EIBTRNID TO QUEUENAME-TRANS."]
        + lines[9:],
    )
    assert program["cics"][0]["queue_scope"] == "session_private"

    program = build_program(
        tmp_path,
        lines[:7]
        + ["       01 WS-DUMMY PIC X."]
        + lines[7:9]
        + ["           MOVE 'ABCD' TO QUEUENAME-TRANS."]
        + lines[9:],
    )
    assert program["cics"][0]["queue_scope"] == "unknown"

    program = build_program(
        tmp_path,
        [
            "       IDENTIFICATION DIVISION.",
            "       PROGRAM-ID. TESTPGM.",
            "       PROCEDURE DIVISION.",
            "       MAIN-PARA.",
            "           EXEC CICS DELETEQ TS QUEUE('MYQ') END-EXEC.",
            "           EXEC CICS READQ TS QUEUE(WS-QUEUE) END-EXEC.",
        ],
    )
    assert program["cics"][0]["queue_scope"] == "shared"
    assert program["cics"][0]["dynamic"] is False
    assert program["cics"][1]["queue_scope"] == "unknown"


def test_comments_and_banner_filtering(tmp_path):
    """Extract useful fixed-format header and paragraph comments."""
    program = build_program(
        tmp_path,
        [
            "      * PAYROLL POSTING",
            "      *****",
            "       IDENTIFICATION DIVISION.",
            "       PROGRAM-ID. TESTPGM.",
            "       PROCEDURE DIVISION.",
            "      * CALCULATE TAX",
            "       TAX-PARA.",
            "           GOBACK.",
        ],
    )
    assert program["header_comment"] == "PAYROLL POSTING"
    assert program["paragraphs"][0]["comment"] == "CALCULATE TAX"


def test_sql_columns_and_file_record(tmp_path):
    """Record SQL columns and the first 01 record following each FD."""
    program = build_program(
        tmp_path,
        [
            "       IDENTIFICATION DIVISION.",
            "       PROGRAM-ID. TESTPGM.",
            "       ENVIRONMENT DIVISION.",
            "       INPUT-OUTPUT SECTION.",
            "       FILE-CONTROL.",
            "           SELECT INFILE ASSIGN TO INDD.",
            "       DATA DIVISION.",
            "       FILE SECTION.",
            "       FD INFILE.",
            "       01 IN-REC PIC X(80).",
            "       WORKING-STORAGE SECTION.",
            "       PROCEDURE DIVISION.",
            "       MAIN-PARA.",
            "           EXEC SQL SELECT A, B AS X FROM T",
            "               INTO :A, :B END-EXEC.",
            "           EXEC SQL INSERT INTO T (C1, C2) VALUES (:A, :B)",
            "           END-EXEC.",
            "           EXEC SQL UPDATE T SET C1 = :X, C2 = 5 WHERE K = 1",
            "           END-EXEC.",
        ],
    )
    assert program["files"][0]["record"] == "IN-REC"
    assert program["sql"][0]["columns"] == ["A", "B"]
    assert program["sql"][1]["columns"] == ["C1", "C2"]
    assert program["sql"][2]["columns"] == ["C1", "C2"]


def test_sql_columns_respect_nested_clauses(tmp_path):
    """Keep nested FROM clauses inside the selected column expressions."""
    program = build_program(
        tmp_path,
        [
            "       IDENTIFICATION DIVISION.",
            "       PROGRAM-ID. TESTPGM.",
            "       PROCEDURE DIVISION.",
            "       MAIN-PARA.",
            "           EXEC SQL SELECT COALESCE(A, B),",
            "               (SELECT C FROM INNER_TABLE) AS VALUE",
            "               FROM OUTER_TABLE END-EXEC.",
        ],
    )
    assert program["sql"][0]["columns"] == [
        "COALESCE(A, B)",
        "(SELECT C FROM INNER_TABLE)",
    ]
