from stages.stage1_inventory.extractors import extract
from stages.stage1_inventory.reader import read_file


def extract_lines(tmp_path, lines, file_type, rel_path="source.txt"):
    """Write lines, read the file, and extract names and references."""
    path = tmp_path / "source.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return extract(read_file(str(path)), file_type, rel_path)


def test_cobol_names_and_references(tmp_path):
    """Extract COBOL declarations, copybooks, and calls."""
    names, references = extract_lines(
        tmp_path,
        [
            "       PROGRAM-ID. TESTPGM.",
            "       COPY ACCTREC.",
            "       COPY SQLCA.",
            "       CALL 'SUBPGM'.",
            "       CALL WS-PGM-NAME.",
        ],
        "cobol_program",
    )

    assert names == ["TESTPGM"]
    assert references == [
        {"kind": "copy", "name": "ACCTREC", "line": 2, "dynamic": False},
        {"kind": "copy", "name": "SQLCA", "line": 3, "dynamic": False},
        {"kind": "call", "name": "SUBPGM", "line": 4, "dynamic": False},
        {"kind": "call", "name": "WS-PGM-NAME", "line": 5, "dynamic": True},
    ]


def test_sql_include_is_not_a_copy(tmp_path):
    """Extract SQL INCLUDE without treating it as a COBOL COPY."""
    names, references = extract_lines(
        tmp_path,
        ["           EXEC SQL INCLUDE SQLCA END-EXEC."],
        "cobol_program",
    )

    assert names == []
    assert references == [
        {"kind": "sql_include", "name": "SQLCA", "line": 1, "dynamic": False}
    ]


def test_fixed_format_comment_does_not_add_references(tmp_path):
    """Ignore reference-like text on fixed-format comment lines."""
    _, references = extract_lines(
        tmp_path,
        [
            "       PROGRAM-ID. TESTPGM.",
            "      * COPY HIDDEN.",
            "       COPY VISIBLE.",
        ],
        "cobol_program",
    )

    assert [reference["name"] for reference in references] == ["VISIBLE"]


def test_multiline_cics_references(tmp_path):
    """Extract CICS link, mapset, and transaction references."""
    _, references = extract_lines(
        tmp_path,
        [
            "           EXEC CICS XCTL",
            "                PROGRAM('COMEN01C')",
            "           END-EXEC.",
            "           EXEC CICS SEND MAP('COSGN0A')",
            "                MAPSET('COSGN00')",
            "           END-EXEC.",
            "           EXEC CICS RETURN TRANSID('CC00')",
            "           END-EXEC.",
            "           EXEC CICS LINK PROGRAM(WS-NEXT)",
        ],
        "cobol_program",
    )

    assert references == [
        {"kind": "cics_xctl", "name": "COMEN01C", "line": 1, "dynamic": False},
        {"kind": "cics_map", "name": "COSGN00", "line": 4, "dynamic": False},
        {"kind": "cics_transid", "name": "CC00", "line": 7, "dynamic": False},
        {"kind": "cics_link", "name": "WS-NEXT", "line": 9, "dynamic": True},
    ]


def test_jcl_references(tmp_path):
    """Extract JCL job, program, procedure, and include names."""
    names, references = extract_lines(
        tmp_path,
        [
            "//DAILY    JOB (ACCT),'X'",
            "//STEP1    EXEC PGM=TRANPROC,",
            "//         PARM='PROD'",
            "//STEP2    EXEC MYPROC,PARM=1",
            "//STEP3    EXEC PROC=OTHER",
            "//         INCLUDE MEMBER=INC1",
        ],
        "jcl",
    )

    assert names == ["DAILY"]
    assert references == [
        {"kind": "jcl_pgm", "name": "TRANPROC", "line": 2, "dynamic": False},
        {"kind": "jcl_proc", "name": "MYPROC", "line": 4, "dynamic": False},
        {"kind": "jcl_proc", "name": "OTHER", "line": 5, "dynamic": False},
        {"kind": "jcl_include", "name": "INC1", "line": 6, "dynamic": False},
    ]


def test_bms_declarations_use_raw_lines(tmp_path):
    """Extract BMS mapset and map names in required order."""
    names, _ = extract_lines(
        tmp_path,
        [
            "MAPSET1  DFHMSD TYPE=&SYSPARM,MODE=INOUT,LANG=COBOL",
            "MAP1     DFHMDI SIZE=(24,80)",
            "FIELD1   DFHMDF POS=(1,1),LENGTH=10",
            "         DFHMSD TYPE=FINAL",
        ],
        "bms_map",
    )

    assert names == ["MAPSET1", "MAP1"]


def test_assembler_declarations_use_raw_lines(tmp_path):
    """Extract assembler section names."""
    names, _ = extract_lines(
        tmp_path,
        [
            "MYPROG   CSECT",
            "                USING *,12",
            "                STM   14,12,12(13)",
            "                LR    12,15",
            "                MVC   WORK(8),=CL8'HELLO'",
            "WORK     DS    CL8",
            "                END",
        ],
        "assembler",
    )

    assert names == ["MYPROG"]


def test_stem_declarations_for_copybook_and_jcl_proc(tmp_path):
    """Use the file stem for undeclared copybooks and procedures."""
    copybook_names, _ = extract_lines(
        tmp_path,
        ["       01  ACCT-RECORD."],
        "copybook",
        "COPYLIB/acctrec.cpy",
    )
    no_extension_names, _ = extract_lines(
        tmp_path,
        ["       01  ACCT-RECORD."],
        "copybook",
        "ACCTREC",
    )
    proc_names, _ = extract_lines(
        tmp_path,
        ["//MYPROC PROC"],
        "jcl_proc",
        "PROCS/PAYPROC.jcl",
    )
    fallback_proc_names, _ = extract_lines(
        tmp_path,
        ["//STEP1 EXEC PGM=IEFBR14"],
        "jcl_proc",
        "PROCS/PAYPROC.jcl",
    )

    assert copybook_names == ["ACCTREC"]
    assert no_extension_names == ["ACCTREC"]
    assert proc_names == ["MYPROC"]
    assert fallback_proc_names == ["PAYPROC"]


def test_other_types_have_no_names_or_references(tmp_path):
    """Return no names or references for unsupported types."""
    assert extract_lines(tmp_path, ["A heading"], "documentation") == ([], [])
