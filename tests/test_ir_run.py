import json
import os
import time

from stages.stage1_inventory.inventory import build_inventory
from stages.stage2_ir import builder
from stages.stage2_ir.runner import run_ir


def test_run_writes_one_ir_per_inventory_file(tmp_path):
    """Write the manifest and IR output files for a complete inventory."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "program.cbl").write_text(
        "\n".join(
            [
                "       IDENTIFICATION DIVISION.",
                "       PROGRAM-ID. TESTPGM.",
                "       PROCEDURE DIVISION.",
                "       MAIN-PARA.",
                "           STOP RUN.",
            ]
        ),
        encoding="utf-8",
    )
    (source / "job.jcl").write_text(
        "//DAILY JOB (ACCT),'DAILY'\n//STEP1 EXEC PGM=TESTPGM",
        encoding="utf-8",
    )
    (source / "copy.cpy").write_text(
        "       01 COPY-RECORD.\n           05 COPY-FIELD PIC X.",
        encoding="utf-8",
    )
    (source / "map.bms").write_text(
        "MAPSET DFHMSD TYPE=FINAL\nMAP DFHMDI SIZE=(24,80)",
        encoding="utf-8",
    )
    (source / "readme.md").write_text(
        "# T\n- a\n- b\n```\nexample\n```",
        encoding="utf-8",
    )
    inventory = build_inventory(str(source))
    output_dir = tmp_path / "output" / "source_ir_20261029_120000"

    manifest = run_ir(inventory, str(source), str(output_dir))

    assert manifest["complete"] is True
    assert len(manifest["files"]) == 5
    assert os.path.isfile(output_dir / "ir_run.json")
    for entry in manifest["files"]:
        assert os.path.isfile(output_dir / entry["ir_file"])
    markdown_path = next(item["ir_file"] for item in manifest["files"] if item["path"] == "readme.md")
    with open(output_dir / markdown_path, encoding="utf-8") as source_file:
        markdown_ir = json.load(source_file)
    assert "program" not in markdown_ir
    assert markdown_ir["parse_status"] == "complete"
    program_path = next(item["ir_file"] for item in manifest["files"] if item["type"] == "cobol_program")
    with open(output_dir / program_path, encoding="utf-8") as source_file:
        program_ir = json.load(source_file)
    assert "program" in program_ir
    assert program_ir["program"]["paragraphs"]


def test_stop_returns_partial_run(tmp_path):
    """Stop between IR files and mark the run incomplete."""
    source = tmp_path / "source"
    source.mkdir()
    for name in ("one.txt", "two.txt", "three.txt"):
        (source / name).write_text("plain prose", encoding="utf-8")
    inventory = build_inventory(str(source))
    calls = 0

    def should_stop():
        nonlocal calls
        calls += 1
        return calls > 1

    manifest = run_ir(
        inventory,
        str(source),
        str(tmp_path / "output"),
        should_stop=should_stop,
    )

    assert manifest["complete"] is False
    assert len(manifest["files"]) < 3


def test_extractor_exception_does_not_stop_other_files(tmp_path, monkeypatch):
    """Record an extractor failure and continue producing other IR files."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "program.cbl").write_text(
        "       IDENTIFICATION DIVISION.\n"
        "       PROGRAM-ID. TESTPGM.\n"
        "       PROCEDURE DIVISION.\n"
        "       MAIN-PARA.\n"
        "           STOP RUN.",
        encoding="utf-8",
    )
    (source / "notes.md").write_text("plain note", encoding="utf-8")
    inventory = build_inventory(str(source))

    def fail_program(*args):
        """Raise an extractor exception for testing."""
        raise RuntimeError("test extraction failure")

    monkeypatch.setattr(builder, "build_program_ir", fail_program)
    output_dir = tmp_path / "output"
    manifest = run_ir(inventory, str(source), str(output_dir))

    assert manifest["complete"] is True
    failed = next(entry for entry in manifest["files"] if entry["type"] == "cobol_program")
    with open(output_dir / failed["ir_file"], encoding="utf-8") as source_file:
        file_ir = json.load(source_file)
    assert file_ir["parse_status"] == "partial"
    assert file_ir["unparsed_ranges"][0]["reason"].startswith("extractor error")
    assert len(manifest["files"]) == 2


def test_app_build_ir_uses_same_page_job_flow(tmp_path, monkeypatch):
    """Run IR from the page and render its results without a new route page."""
    import app as flask_app

    source = tmp_path / "source"
    source.mkdir()
    (source / "notes.md").write_text("# notes\n- first\n- second", encoding="utf-8")
    inventory = build_inventory(str(source))
    monkeypatch.setattr(flask_app, "WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.setattr(flask_app, "LATEST_INVENTORY", inventory)
    monkeypatch.setattr(flask_app, "LATEST_INVENTORY_PATH", "inventory.json")
    flask_app.app.config.update(TESTING=True)

    with flask_app.app.test_client() as client:
        page = client.get("/")
        assert b'id="build-ir-button"' in page.data
        assert b'id="build-ir-button" disabled' not in page.data
        response = client.post("/build-ir")
        job_id = response.get_json()["job_id"]

        for _ in range(500):
            status = client.get(f"/status/{job_id}").get_json()
            if status["status"] != "running":
                break
            time.sleep(0.01)

        result = client.get(f"/result/{job_id}")
        assert status["status"] == "complete"
        assert b"Per-file IR" in result.data
        assert b"IR output folder:" in result.data
        assert b"Parse status" in result.data
