import json

from stages.stage3_project_ir.builder import build_project_ir
from stages.stage3_project_ir.graph import build_edges, build_nodes
from stages.stage3_project_ir.runner import run_project_ir
from tests.ir_fixtures import bms, cpy, job, prog


def test_nodes_edges_and_missing_references():
    """Resolve defined and missing program and copybook references."""
    files = dict([
        prog("a.cbl", "A", copybooks=[{"name": "ACCTREC", "line": 2, "section": "LINKAGE"}],
             calls=[{"target": "B", "dynamic": False, "args": [], "line": 10}]),
        prog("b.cbl", "B"),
        cpy("acct.cpy", "ACCTREC"),
    ])
    nodes, index, duplicates = build_nodes(files)
    edges, dynamic_refs, _ = build_edges(files, nodes, index)
    assert nodes["cpy:ACCTREC"]["status"] == "defined"
    assert nodes["pgm:B"]["status"] == "defined"
    assert not duplicates
    assert not dynamic_refs
    assert {(edge["kind"], edge["to"], edge["status"]) for edge in edges} == {
        ("copies", "cpy:ACCTREC", "resolved"),
        ("calls", "pgm:B", "resolved"),
    }


def test_sql_data_edges_and_conversion_waves():
    """Order a program after the tables it reads and writes."""
    files = dict([
        prog("a.cbl", "A", sql=[
            {"id": "sql:A.1", "kind": "select", "tables": ["ACCOUNTS"], "access": "read",
             "line_span": [10, 10], "paragraph": "MAIN"},
            {"id": "sql:A.2", "kind": "update", "tables": ["ACCOUNTS"],
             "access": "write", "line_span": [20, 20], "paragraph": "MAIN"},
        ]),
    ])
    result = build_project_ir(files, {"source_folder": "source", "complete": True})
    assert "tbl:ACCOUNTS" in {node["id"] for node in result["nodes"]}
    assert {(edge["kind"], edge["count"]) for edge in result["edges"]} == {
        ("reads", 1), ("writes", 1)
    }
    units = result["conversion_order"]["waves"]
    assert units[0]["units"][0]["members"] == ["tbl:ACCOUNTS"]
    assert units[1]["units"][0]["members"] == ["pgm:A"]
    assert result["crud_matrix"]["pgm:A"]["tbl:ACCOUNTS"] == "RW"


def test_job_data_joins_entry_point_order_and_gaps():
    """Join COBOL file declarations to job DDs and expose missing callees."""
    files = dict([
        prog("p.cbl", "P", calls=[
            {"target": "MISSING", "dynamic": False, "args": [], "line": 8}
        ], files=[
            {"logical_name": "INFILE", "ddname": "INFILE", "record": "IN-REC",
             "access": "read", "lines": [5]},
        ]),
        job("daily.jcl", "DAILY", [
            ("MAIN", "pgm", "P", [
                ("INFILE", "USER.INPUT", "input", "read", "SHR"),
            ]),
        ]),
    ])
    result = build_project_ir(files, {"source_folder": "source", "complete": True})
    assert result["entry_points"][0]["kind"] == "jcl_job"
    assert result["entry_points"][0]["steps"][0]["reads"] == ["ds:USER.INPUT"]
    assert result["gaps"][0]["name"] == "MISSING"
    assert result["gaps"][0]["blocks_entry_points"] == ["ep:job:DAILY"]
    store = next(item for item in result["data_stores"] if item["id"] == "ds:USER.INPUT")
    assert store["layout"] == {"program": "pgm:P", "record": "IN-REC"}


def test_cycles_and_online_entry_points():
    """Collapse mutually linked programs into one online entry point."""
    files = dict([
        prog("a.cbl", "A", calls=[
            {"target": "B", "dynamic": False, "args": [], "line": 3}
        ], cics=[
            {"id": "cics:A.1", "command": "SEND MAP", "map": "SIGNON",
             "mapset": "SIGNON", "dynamic": False, "line": 4}
        ]),
        prog("b.cbl", "B", calls=[
            {"target": "A", "dynamic": False, "args": [], "line": 5}
        ]),
        bms("signon.bms", "SIGNON", [{"name": "SIGNON", "size": "24x80", "line": 1}]),
    ])
    result = build_project_ir(files, {"source_folder": "source", "complete": True})
    assert result["cycles"][0]["members"] == ["pgm:A", "pgm:B"]
    online = [entry for entry in result["entry_points"] if entry["kind"] == "online"]
    assert len(online) == 1
    assert online[0]["members"] == ["pgm:A", "pgm:B"]
    assert result["screens"][0]["used_by"] == ["pgm:A"]


def test_queue_candidates_and_private_queues():
    """Keep transaction-private queues out of shared data edges."""
    files = dict([
        prog("writer.cbl", "WRITER", cics=[
            {"id": "cics:WRITER.1", "command": "WRITEQ TS", "queue": "MYQ",
             "dynamic": False, "line": 2}
        ]),
        prog("reader.cbl", "READER", cics=[
            {"id": "cics:READER.1", "command": "READQ TS", "queue": "MYQ",
             "dynamic": False, "line": 2}
        ]),
        prog("private.cbl", "PRIVATE", cics=[
            {"id": "cics:PRIVATE.1", "command": "DELETEQ TS", "queue": "WS-QUEUE",
             "dynamic": True, "queue_scope": "session_private", "candidates": [],
             "line": 3}
        ]),
        prog("unknown.cbl", "UNKNOWN", cics=[
            {"id": "cics:UNKNOWN.1", "command": "READQ TS", "queue": "WS-QUEUE",
             "dynamic": True, "queue_scope": "unknown", "candidates": [],
             "line": 4}
        ]),
        prog("candidate.cbl", "CANDIDATE", cics=[
            {"id": "cics:CANDIDATE.1", "command": "WRITEQ TS", "queue": "WS-QUEUE",
             "dynamic": True, "queue_scope": "shared",
             "candidates": [{"value": "Q1", "line": 5, "how": "move"}], "line": 5}
        ]),
    ])
    result = build_project_ir(files, {"source_folder": "source", "complete": True})
    queue = next(node for node in result["nodes"] if node["id"] == "q:MYQ")
    assert queue["card"]["readers"] == ["pgm:READER"]
    assert queue["card"]["writers"] == ["pgm:WRITER"]
    assert "q:Q1" in {node["id"] for node in result["nodes"]}
    assert "pgm:UNKNOWN" not in {
        edge["from"] for edge in result["edges"] if edge["to"].startswith("dyn:")
    }
    assert next(
        node for node in result["nodes"] if node["id"] == "pgm:PRIVATE"
    )["card"]["private_queues"] == 1
    assert len(result["quality"]["dynamic_refs"]) == 2


def test_runner_writes_project_json_and_stop_skips_file(tmp_path):
    """Persist the consolidated output and honor a stop before a phase."""
    source = tmp_path / "source"
    ir_dir = source / "ir"
    ir_dir.mkdir(parents=True)
    path, ir = prog("program.cbl", "TESTPGM")
    (ir_dir / "files").mkdir()
    (ir_dir / "files" / "program.json").write_text(json.dumps(ir), encoding="utf-8")
    (ir_dir / "ir_run.json").write_text(json.dumps({
        "source_folder": str(source),
        "generated_at": "2026-01-01T00:00:00Z",
        "complete": True,
        "files": [{"path": path, "ir_file": "files/program.json"}],
    }), encoding="utf-8")
    output = run_project_ir(str(ir_dir), str(tmp_path / "output"))
    assert output["stopped"] is False
    with open(output["project_ir_path"], encoding="utf-8") as source_file:
        project = json.load(source_file)
    assert project["modules"] == []
    assert project["schema_version"] == "1.0"

    stopped = run_project_ir(
        str(ir_dir), str(tmp_path / "stopped"),
        should_stop=lambda: True,
    )
    assert stopped == {"stopped": True}
    assert not (tmp_path / "stopped").exists()
