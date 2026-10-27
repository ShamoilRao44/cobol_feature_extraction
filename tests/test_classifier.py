import json
import os
import re
import threading
import time

from stages.stage1_inventory.classifier import classify, decide_type
from stages.stage1_inventory.inventory import build_inventory, write_inventory
from stages.stage1_inventory.reader import read_file


def classify_lines(tmp_path, lines):
    """Write source lines and classify the resulting file."""
    path = tmp_path / "source.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return classify(read_file(str(path)))


def test_cobol_program_is_high_confidence(tmp_path):
    """Recognize a complete COBOL program."""
    lines = [
        "       IDENTIFICATION DIVISION.",
        "       PROGRAM-ID. TESTPGM.",
        "       ENVIRONMENT DIVISION.",
        "       DATA DIVISION.",
        "       WORKING-STORAGE SECTION.",
        "       01  WS-A  PIC 9(3).",
        "       PROCEDURE DIVISION.",
        "           MOVE 1 TO WS-A.",
        "           STOP RUN.",
    ]

    result = classify_lines(tmp_path, lines)

    assert result.file_type == "cobol_program"
    assert result.confidence == "high"


def test_cobol_fragment(tmp_path):
    """Recognize a COBOL procedure fragment."""
    lines = [
        "       PROCEDURE DIVISION.",
        "       MAIN-PARA.",
        "           PERFORM INIT-PARA.",
        "           MOVE 1 TO WS-A.",
        "           IF WS-A = 1",
        "               DISPLAY 'ONE'",
        "           END-IF.",
        "           STOP RUN.",
    ]

    assert classify_lines(tmp_path, lines).file_type == "cobol_fragment"


def test_copybook(tmp_path):
    """Recognize COBOL data declarations."""
    lines = [
        "       01  ACCT-RECORD.",
        "           05  ACCT-NUMBER     PIC X(10).",
        "           05  ACCT-BALANCE    PIC S9(9)V99 COMP-3.",
        "           05  ACCT-STATUS     PIC X(1).",
    ]

    assert classify_lines(tmp_path, lines).file_type == "copybook"


def test_jcl_job_has_high_confidence(tmp_path):
    """Recognize a JCL job."""
    lines = [
        "//DAILYJOB JOB (ACCT),'DAILY RUN',CLASS=A",
        "//STEP01   EXEC PGM=ACCTMSTR",
        "//INFILE   DD DSN=BANK.INPUT,DISP=SHR",
        "//OUTFILE  DD DSN=BANK.OUTPUT,DISP=(NEW,CATLG)",
        "//SYSOUT   DD SYSOUT=*",
    ]

    result = classify_lines(tmp_path, lines)

    assert result.file_type == "jcl"
    assert result.confidence == "high"


def test_jcl_proc(tmp_path):
    """Recognize JCL procedure members."""
    lines = [
        "//MYPROC   PROC",
        "//STEP1    EXEC PGM=IEFBR14",
        "//DD1      DD DSN=&HLQ..DATA,DISP=SHR",
    ]

    assert classify_lines(tmp_path, lines).file_type == "jcl_proc"


def test_bms_map(tmp_path):
    """Recognize BMS map definitions."""
    lines = [
        "MAPSET1  DFHMSD TYPE=&SYSPARM,MODE=INOUT,LANG=COBOL",
        "MAP1     DFHMDI SIZE=(24,80)",
        "FIELD1   DFHMDF POS=(1,1),LENGTH=10",
        "         DFHMSD TYPE=FINAL",
    ]

    assert classify_lines(tmp_path, lines).file_type == "bms_map"


def test_assembler(tmp_path):
    """Recognize assembler structure and instructions."""
    lines = [
        "MYPROG   CSECT",
        "                USING *,12",
        "                STM   14,12,12(13)",
        "                LR    12,15",
        "                MVC   WORK(8),=CL8'HELLO'",
        "WORK     DS    CL8",
        "                END",
    ]

    assert classify_lines(tmp_path, lines).file_type == "assembler"


def test_pli(tmp_path):
    """Recognize PL/I declarations and main procedure."""
    lines = [
        "MYPROG: PROC OPTIONS(MAIN);",
        "  DCL X FIXED BIN(31);",
        "  DCL Y CHAR(10);",
        "  X = 1;",
        "END MYPROG;",
    ]

    assert classify_lines(tmp_path, lines).file_type == "pli"


def test_sql(tmp_path):
    """Recognize SQL DDL and grant statements."""
    lines = [
        "CREATE TABLE ACCOUNT (",
        "    ACCT_NO CHAR(10) NOT NULL,",
        "    BALANCE DECIMAL(11,2)",
        ");",
        "CREATE INDEX IX1 ON ACCOUNT (ACCT_NO);",
        "GRANT SELECT ON ACCOUNT TO PUBLIC;",
    ]

    assert classify_lines(tmp_path, lines).file_type == "sql"


def test_other_source(tmp_path):
    """Recognize common Python source constructs."""
    lines = [
        "import os",
        "from pathlib import Path",
        "",
        "def main():",
        "    print('hi')",
        "",
        "class Foo:",
        "    pass",
    ]

    assert classify_lines(tmp_path, lines).file_type == "other_source"


def test_markdown_documentation_wins_over_jcl(tmp_path):
    """Prefer Markdown classification for fenced JCL examples."""
    lines = [
        "# Title",
        "",
        "- item one",
        "- item two",
        "```",
        "//DAILYJOB JOB (ACCT),'DAILY RUN',CLASS=A",
        "//STEP01   EXEC PGM=ACCTMSTR",
        "//INFILE   DD DSN=BANK.INPUT,DISP=SHR",
        "//OUTFILE  DD DSN=BANK.OUTPUT,DISP=(NEW,CATLG)",
        "//SYSOUT   DD SYSOUT=*",
        "```",
    ]

    assert classify_lines(tmp_path, lines).file_type == "documentation"


def test_plain_prose_is_unknown_with_low_confidence(tmp_path):
    """Classify unrecognized prose as unknown."""
    lines = [
        "The first sentence describes a routine process.",
        "Another sentence explains the result in plain language.",
        "A final sentence provides some additional context.",
    ]

    result = classify_lines(tmp_path, lines)

    assert result.file_type == "unknown"
    assert result.confidence == "low"


def test_empty_and_binary_files(tmp_path):
    """Classify empty and binary file content."""
    empty_path = tmp_path / "empty.txt"
    binary_path = tmp_path / "binary.txt"
    empty_path.write_bytes(b"")
    binary_path.write_bytes(b"abc\x00def")

    assert classify(read_file(str(empty_path))).file_type == "empty"
    assert classify(read_file(str(binary_path))).file_type == "binary"


def test_cobol_comment_does_not_trigger_bms(tmp_path):
    """Ignore BMS keywords in a fixed-format comment."""
    lines = [
        "       IDENTIFICATION DIVISION.",
        "      * USES DFHMSD DFHMDI DFHMDF",
        "       PROGRAM-ID. TESTPGM.",
        "       ENVIRONMENT DIVISION.",
        "       DATA DIVISION.",
        "       WORKING-STORAGE SECTION.",
        "       01  WS-A  PIC 9(3).",
        "       PROCEDURE DIVISION.",
        "           MOVE 1 TO WS-A.",
        "           STOP RUN.",
    ]

    assert classify_lines(tmp_path, lines).file_type == "cobol_program"


def test_embedded_sql_does_not_score_as_standalone_sql(tmp_path):
    """Do not classify embedded COBOL SQL as standalone SQL."""
    lines = [
        "       IDENTIFICATION DIVISION.",
        "       PROGRAM-ID. TESTPGM.",
        "       ENVIRONMENT DIVISION.",
        "       DATA DIVISION.",
        "       WORKING-STORAGE SECTION.",
        "       01  WS-A  PIC 9(3).",
        "       PROCEDURE DIVISION.",
        "           MOVE 1 TO WS-A.",
        "           EXEC SQL COMMIT END-EXEC.",
        "           STOP RUN.",
    ]

    result = classify_lines(tmp_path, lines)

    assert result.file_type == "cobol_program"
    assert result.scores.get("sql", 0) == 0


def test_decide_type():
    """Apply deterministic score thresholds and tie breaks."""
    assert decide_type({"jcl": 10, "cobol_program": 1}) == (
        "jcl",
        "high",
        "cobol_program",
    )
    assert decide_type({"jcl": 6, "copybook": 5}) == (
        "jcl",
        "low",
        "copybook",
    )
    assert decide_type({"jcl": 3}) == ("unknown", "low", "jcl")
    assert decide_type({}) == ("unknown", "low", None)


def test_build_and_write_inventory(tmp_path):
    """Build and save an inventory JSON file."""
    source_folder = tmp_path / "source"
    source_folder.mkdir()
    program = [
        "       IDENTIFICATION DIVISION.",
        "       PROGRAM-ID. TESTPGM.",
        "       ENVIRONMENT DIVISION.",
        "       DATA DIVISION.",
        "       WORKING-STORAGE SECTION.",
        "       01  WS-A  PIC 9(3).",
        "       PROCEDURE DIVISION.",
        "           MOVE 1 TO WS-A.",
        "           STOP RUN.",
    ]
    job = [
        "//DAILYJOB JOB (ACCT),'DAILY RUN',CLASS=A",
        "//STEP01   EXEC PGM=ACCTMSTR",
        "//INFILE   DD DSN=BANK.INPUT,DISP=SHR",
        "//OUTFILE  DD DSN=BANK.OUTPUT,DISP=(NEW,CATLG)",
        "//SYSOUT   DD SYSOUT=*",
    ]
    (source_folder / "program.txt").write_text("\n".join(program), encoding="utf-8")
    (source_folder / "job.txt").write_text("\n".join(job), encoding="utf-8")

    inventory = build_inventory(str(source_folder))
    output_path = write_inventory(inventory, str(tmp_path / "workspace"))
    with open(output_path, encoding="utf-8") as saved_file:
        saved_inventory = json.load(saved_file)

    assert len(saved_inventory["files"]) == 2
    assert saved_inventory["summary"]["total_files"] == 2
    assert saved_inventory["complete"] is True
    assert saved_inventory["summary"]["gap_count"] >= 1
    assert all("sha256" in entry for entry in saved_inventory["files"])
    assert all("declared_names" in entry for entry in saved_inventory["files"])
    assert all("references" in entry for entry in saved_inventory["files"])
    assert os.path.basename(os.path.dirname(output_path)) == "stage1_outputs"
    assert re.fullmatch(
        r"source_inventory_\d{8}_\d{6}\.json",
        os.path.basename(output_path),
    )


def test_stopped_inventory_saves_completed_files(tmp_path):
    """Save a timestamped partial inventory after a stop request."""
    source_folder = tmp_path / "tdc_all_files"
    source_folder.mkdir()
    (source_folder / "first.txt").write_text("first prose line", encoding="utf-8")
    (source_folder / "second.txt").write_text("second prose line", encoding="utf-8")
    stop_event = threading.Event()

    def report_progress(processed, total, relative_path):
        """Request cancellation after the first classified file."""
        if processed == 1:
            stop_event.set()

    inventory = build_inventory(
        str(source_folder),
        should_stop=stop_event.is_set,
        on_progress=report_progress,
    )
    output_path = write_inventory(inventory, str(tmp_path / "workspace"))

    assert inventory["summary"]["total_files"] == 1
    assert inventory["files"][0]["path"] == "first.txt"
    assert inventory["complete"] is False
    assert inventory["gaps"] == []
    assert inventory["entry_points"] == []
    assert inventory["duplicates"] == {"names": [], "identical_files": []}
    assert re.fullmatch(
        r"tdc_all_files_inventory_\d{8}_\d{6}\.json",
        os.path.basename(output_path),
    )


def test_app_copies_files_by_type_as_they_are_classified(tmp_path, monkeypatch):
    """Copy classified source files into per-type folders."""
    import app as flask_app

    source_folder = tmp_path / "tdc_all_files"
    source_folder.mkdir()
    (source_folder / "program.txt").write_text(
        "\n".join(
            [
                "       IDENTIFICATION DIVISION.",
                "       PROGRAM-ID. TESTPGM.",
                "       ENVIRONMENT DIVISION.",
                "       DATA DIVISION.",
                "       WORKING-STORAGE SECTION.",
                "       01  WS-A  PIC 9(3).",
                "       PROCEDURE DIVISION.",
                "           MOVE 1 TO WS-A.",
                "           STOP RUN.",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        flask_app,
        "WORKSPACE_DIR",
        str(tmp_path / "workspace"),
    )
    flask_app.app.config.update(TESTING=True)

    with flask_app.app.test_client() as client:
        response = client.post(
            "/",
            data={"folder_path": str(source_folder)},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.is_json
        job_id = response.get_json()["job_id"]

        for _ in range(500):
            status = client.get(f"/status/{job_id}").get_json()
            if status["status"] != "running":
                break
            time.sleep(0.01)

        copied_file = (
            tmp_path
            / "workspace"
            / "sorted_tdc_all_files"
            / "cobol_program"
            / "program.txt"
        )
        assert status["status"] == "complete"
        assert copied_file.read_text(encoding="utf-8") == (
            source_folder / "program.txt"
        ).read_text(encoding="utf-8")
