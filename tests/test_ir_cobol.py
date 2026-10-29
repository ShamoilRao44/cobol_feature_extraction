from stages.stage1_inventory.reader import read_file
from stages.stage2_ir.cobol_ir import build_program_ir, parse_data_items


def line_of(lines, text):
    """Return the number of the first matching source line."""
    return next(index for index, line in enumerate(lines, start=1) if text in line)


def read_lines(tmp_path, lines):
    """Write source lines and return their FileContent."""
    path = tmp_path / "program.cbl"
    path.write_text("\n".join(lines), encoding="utf-8")
    return read_file(str(path))


def test_program_ir_files_data_sql_calls_and_events(tmp_path):
    """Extract the requested structures from a representative COBOL program."""
    source = [
        "       IDENTIFICATION DIVISION.",
        "       PROGRAM-ID. TESTPGM.",
        "       ENVIRONMENT DIVISION.",
        "       INPUT-OUTPUT SECTION.",
        "       FILE-CONTROL.",
        "           SELECT INFILE ASSIGN TO UT-S-INDD",
        "               ORGANIZATION IS SEQUENTIAL",
        "               FILE STATUS IS WS-IN-STATUS.",
        "           SELECT OUTFILE ASSIGN TO UT-S-OUTDD.",
        "       DATA DIVISION.",
        "       FILE SECTION.",
        "       FD  INFILE.",
        "       01  IN-REC            PIC X(80).",
        "       FD  OUTFILE.",
        "       01  OUT-REC           PIC X(80).",
        "       WORKING-STORAGE SECTION.",
        "       01  WS-IN-STATUS      PIC XX.",
        "       01  WS-BALANCE        PIC S9(9)V99 COMP-3 VALUE 0.",
        "       01  WS-EOF            PIC X VALUE 'N'.",
        "           88  AT-EOF        VALUE 'Y'.",
        "           COPY ACCTREC.",
        "           EXEC SQL INCLUDE SQLCA END-EXEC.",
        "           EXEC SQL DECLARE ACCTCUR CURSOR FOR",
        "               SELECT ACCT_NO, BALANCE FROM ACCOUNT",
        "               WHERE STATUS = 'A'",
        "           END-EXEC.",
        "       LINKAGE SECTION.",
        "       01  LS-PARM           PIC X(10).",
        "       PROCEDURE DIVISION USING LS-PARM.",
        "       MAIN-PARA.",
        "           OPEN INPUT INFILE OUTPUT OUTFILE.",
        "           PERFORM READ-PARA UNTIL AT-EOF.",
        "           IF WS-IN-STATUS NOT = '00'",
        "               DISPLAY 'BAD STATUS'",
        "           END-IF.",
        "           EXEC SQL OPEN ACCTCUR END-EXEC.",
        "           EXEC SQL",
        "               UPDATE ACCOUNT SET BALANCE = :WS-BALANCE",
        "               WHERE ACCT_NO = :WS-ACCT",
        "           END-EXEC.",
        "           CALL 'SUBPGM' USING WS-BALANCE.",
        "           CLOSE INFILE OUTFILE.",
        "           GOBACK.",
        "       READ-PARA.",
        "           READ INFILE",
        "               AT END MOVE 'Y' TO WS-EOF",
        "           END-READ.",
        "           WRITE OUT-REC FROM IN-REC.",
    ]
    content = read_lines(tmp_path, source)
    program, unparsed = build_program_ir(content, "program.cbl", ["TESTPGM"])

    assert unparsed == []
    assert program["id"] == "pgm:TESTPGM"
    assert program["linkage"] == {"is_subprogram": True, "params": ["LS-PARM"]}
    assert [file["logical_name"] for file in program["files"]] == ["INFILE", "OUTFILE"]
    assert program["files"][0]["ddname"] == "INDD"
    assert program["files"][0]["organization"] == "SEQUENTIAL"
    assert program["files"][0]["status_var"] == "WS-IN-STATUS"
    assert program["files"][0]["open_modes"] == ["INPUT"]
    assert program["files"][0]["operations"] == ["READ"]
    assert program["files"][0]["access"] == "read"
    assert program["files"][1]["open_modes"] == ["OUTPUT"]
    assert program["files"][1]["operations"] == ["WRITE"]
    assert program["files"][1]["access"] == "write"
    assert program["copybooks"] == [
        {"name": "ACCTREC", "line": line_of(source, "COPY ACCTREC"), "replacing": False}
    ]
    assert program["data_items"]
    balance = next(item for item in program["data_items"] if item["name"] == "WS-BALANCE")
    assert balance["pic"] == "S9(9)V99"
    assert balance["usage"] == "COMP-3"
    assert balance["value"] == "0"
    assert [item["kind"] for item in program["sql"]] == [
        "include",
        "declare_cursor",
        "open",
        "update",
    ]
    assert program["sql"][1]["cursor"] == "ACCTCUR"
    assert program["sql"][1]["tables"] == ["ACCOUNT"]
    assert program["sql"][2]["tables"] == ["ACCOUNT"]
    assert program["sql"][3]["tables"] == ["ACCOUNT"]
    assert program["sql"][3]["host_vars"] == ["WS-BALANCE", "WS-ACCT"]
    assert program["calls"][0]["target"] == "SUBPGM"
    assert program["calls"][0]["args"] == ["WS-BALANCE"]
    assert [paragraph["name"] for paragraph in program["paragraphs"]] == [
        "MAIN-PARA",
        "READ-PARA",
    ]
    main_events = program["paragraphs"][0]["events"]
    assert [event["kind"] for event in main_events] == [
        "file_op", "file_op", "perform", "error_check", "display",
        "sql", "sql", "call", "file_op", "file_op", "end",
    ]
    assert program["metrics"]["paragraphs"] == 2
    assert program["metrics"]["conditions"] == 2
    assert program["metrics"]["sql"] == 4
    assert program["metrics"]["calls"] == 1
    assert program["dialect"]["uses_sql"] is True
    assert program["dialect"]["uses_cics"] is False
    read_events = program["paragraphs"][1]["events"]
    assert [event["kind"] for event in read_events] == [
        "file_op", "error_check", "file_op",
    ]
    assert read_events[1]["what"] == "AT_END"


def test_nested_conditions_and_paragraphs(tmp_path):
    """Track nested IF and EVALUATE conditions."""
    source = [
        "       IDENTIFICATION DIVISION.",
        "       PROGRAM-ID. CONDPGM.",
        "       PROCEDURE DIVISION.",
        "       MAIN-PARA.",
        "           IF A > 1",
        "               IF B > 2",
        "                   PERFORM P1 THRU P2",
        "               END-IF",
        "           ELSE",
        "               GO TO EXIT-PARA",
        "           END-IF.",
        "           EVALUATE TRUE",
        "               WHEN X = 1",
        "                   PERFORM P1",
        "               WHEN OTHER",
        "                   PERFORM P2",
        "           END-EVALUATE.",
        "           STOP RUN.",
        "       P1.",
        "           EXIT.",
        "       P2.",
        "           EXIT.",
        "       EXIT-PARA.",
        "           EXIT.",
    ]
    program, _ = build_program_ir(read_lines(tmp_path, source), "cond.cbl", ["CONDPGM"])

    assert [condition["kind"] for condition in program["conditions"]] == [
        "IF", "IF", "EVALUATE", "WHEN", "WHEN",
    ]
    assert [paragraph["name"] for paragraph in program["paragraphs"]] == [
        "MAIN-PARA", "P1", "P2", "EXIT-PARA",
    ]
    main_events = program["paragraphs"][0]["events"]
    assert [event["kind"] for event in main_events] == [
        "perform", "goto", "perform", "perform", "end",
    ]
    assert main_events[0]["thru"] == "P2"
    assert main_events[0]["under"] == program["conditions"][1]["id"]
    assert main_events[1]["under"] == program["conditions"][0]["id"]
    assert program["conditions"][0]["line_span"][1] == line_of(source, "END-IF.")


def test_cics_blocks_and_return_event(tmp_path):
    """Extract CICS options and corresponding events."""
    source = [
        "       IDENTIFICATION DIVISION.",
        "       PROGRAM-ID. ONLPGM.",
        "       PROCEDURE DIVISION.",
        "       MAIN-PARA.",
        "           EXEC CICS RECEIVE MAP('SGNA')",
        "                MAPSET('SGN00')",
        "           END-EXEC.",
        "           EXEC CICS XCTL",
        "                PROGRAM(WS-NEXT)",
        "           END-EXEC.",
        "           EXEC CICS RETURN TRANSID('CC00')",
        "                COMMAREA(WS-COMM)",
        "           END-EXEC.",
    ]
    program, _ = build_program_ir(read_lines(tmp_path, source), "online.cbl", ["ONLPGM"])

    assert [item["command"] for item in program["cics"]] == [
        "RECEIVE MAP", "XCTL", "RETURN",
    ]
    assert program["cics"][0]["map"] == "SGNA"
    assert program["cics"][0]["mapset"] == "SGN00"
    assert program["cics"][1]["program"] == "WS-NEXT"
    assert program["cics"][1]["dynamic"] is True
    assert program["cics"][2]["transid"] == "CC00"
    assert [event["kind"] for event in program["paragraphs"][0]["events"]] == [
        "cics", "cics", "cics", "end",
    ]
    assert program["paragraphs"][0]["events"][-1]["how"] == "CICS_RETURN"


def test_dialect_copy_replacing_and_partial_program(tmp_path):
    """Detect compiler cards, COPY REPLACING, and missing procedure division."""
    lines = [
        "CBL OPTIMIZE(FULL)",
        "       IDENTIFICATION DIVISION.",
        "       PROGRAM-ID. PARTIALPGM.",
        "       DATA DIVISION.",
        "       COPY BASE REPLACING ==OLD== BY ==NEW==.",
    ]
    program, unparsed = build_program_ir(
        read_lines(tmp_path, lines),
        "partial.cbl",
        ["PARTIALPGM"],
    )

    assert program["dialect"]["cbl_cards"] == ["OPTIMIZE(FULL)"]
    assert program["dialect"]["copy_replacing"] is True
    assert program["paragraphs"] == []
    assert program["metrics"]["paragraphs"] == 0
    assert any(item["reason"] == "no PROCEDURE DIVISION" for item in unparsed)


def test_unclosed_exec_is_partial(tmp_path):
    """Mark an unterminated EXEC block as unparsed."""
    source = [
        "       IDENTIFICATION DIVISION.",
        "       PROGRAM-ID. OPENPGM.",
        "       PROCEDURE DIVISION.",
        "       MAIN-PARA.",
        "           EXEC SQL SELECT 1 FROM X",
    ]

    _, unparsed = build_program_ir(
        read_lines(tmp_path, source),
        "open.cbl",
        ["OPENPGM"],
    )

    assert any(item["reason"] == "EXEC block not closed" for item in unparsed)


def test_parse_data_items_levels_and_values():
    """Extract levels, usage, values, and skip unsupported levels."""
    items = parse_data_items(
        [
            (1, "01 WS-BALANCE PIC S9(9)V99 COMP-3 VALUE 0."),
            (2, "88 AT-EOF VALUE 'Y'."),
            (3, "66 RENAMED-ITEM RENAMES WS-BALANCE."),
            (4, "50 INVALID-LEVEL PIC X."),
        ]
    )

    assert [item["level"] for item in items] == [1, 88, 66]
    assert items[0]["usage"] == "COMP-3"
    assert items[1]["value"] == "'Y'"
