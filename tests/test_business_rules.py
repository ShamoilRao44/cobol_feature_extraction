import json

from stages.stage1_inventory.inventory import build_inventory
from stages.stage2_ir.runner import run_ir
from stages.stage4_business_rules import chunks, llm
from stages.stage4_business_rules.chunks import build_chunks
from stages.stage4_business_rules.prompts import parse_rules
from stages.stage4_business_rules.runner import run_business_rules

PROGRAM = [
    "IDENTIFICATION DIVISION.",
    "PROGRAM-ID. INTPGM.",
    "DATA DIVISION.",
    "WORKING-STORAGE SECTION.",
    "01  WS-BALANCE        PIC S9(9)V99 COMP-3.",
    "01  WS-RATE           PIC 9V9999.",
    "01  WS-INTEREST       PIC S9(9)V99 COMP-3.",
    "PROCEDURE DIVISION.",
    "MAIN-PARA.",
    "    PERFORM CALC-PARA.",
    "    STOP RUN.",
    "CALC-PARA.",
    "    IF WS-BALANCE > 0",
    "        COMPUTE WS-INTEREST = WS-BALANCE * WS-RATE / 12",
    "    END-IF.",
]


def reply(rules):
    """Wrap rules in the JSON reply shape, inside a markdown fence."""
    return "```json\n" + json.dumps({"rules": rules}) + "\n```"


def interest_rule(line_start=13, line_end=15):
    """Return one plausible rule for CALC-PARA."""
    return {
        "paragraph": "CALC-PARA", "title": "Monthly interest", "kind": "calculation",
        "description": "Interest is balance times rate divided by 12.",
        "condition": "Balance is positive", "data": ["ws-balance", "WS-RATE"],
        "line_start": line_start, "line_end": line_end, "confidence": "high",
    }


def make_ir_run(tmp_path):
    """Write the sample program plus a markdown file and build their per-file IR."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "INTPGM.cbl").write_text("\n".join("       " + line for line in PROGRAM), encoding="utf-8")
    (source / "notes.md").write_text("# Notes\n- a\n- b\n```\nx\n```", encoding="utf-8")
    ir_dir = tmp_path / "ir"
    run_ir(build_inventory(str(source)), str(source), str(ir_dir))
    return ir_dir


def test_env_file_then_env_override(tmp_path, monkeypatch):
    """Read base_url/model/key from .env and let real LLM_* variables override it."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# VM settings\nLLM_BASE_URL=http://localhost:8000/v1/\n"
        "LLM_MODEL=qwen3-coder-next\nLLM_API_KEY=\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(llm, "ENV_PATH", str(env_file))
    for name in llm.ENV_NAMES.values():
        monkeypatch.delenv(name, raising=False)
    config = llm.load_config()
    assert config["base_url"] == "http://localhost:8000/v1"
    assert config["model"] == "qwen3-coder-next"
    assert config["context_tokens"] == 64000
    assert llm.config_error(config) is None
    monkeypatch.setenv("LLM_MODEL", "other-model")
    assert llm.load_config()["model"] == "other-model"


def test_grok_without_key_is_a_config_error():
    """Require a key only for the hosted Grok API."""
    config = dict(llm.DEFAULTS, api_key="")
    assert "LLM_API_KEY" in llm.config_error(config)


def test_prompt_over_budget_is_rejected_before_any_request():
    """Refuse prompts that would not fit the model context with room for the reply."""
    config = dict(llm.DEFAULTS, base_url="http://localhost:1/v1", context_tokens=1000,
                  max_output_tokens=500)
    try:
        llm.ask_llm("system", "x" * 3000, config)
    except ValueError as error:
        assert "budget" in str(error)
        return
    raise AssertionError("expected ValueError")


def test_parse_rules_accepts_fenced_json():
    """Read rules from a reply wrapped in a markdown code fence."""
    assert parse_rules(reply([interest_rule()]))[0]["title"] == "Monthly interest"


def test_parse_rules_rejects_text_without_json():
    """Raise ValueError when the reply has no JSON object."""
    try:
        parse_rules("Sorry, I cannot help.")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_chunks_group_paragraphs_within_budget(monkeypatch):
    """Start a new chunk when the next paragraph would exceed the line budget."""
    monkeypatch.setattr(chunks, "MAX_CHUNK_LINES", 10)
    program = {"name": "P", "paragraphs": [
        {"name": "A", "line_start": 1, "line_end": 4},
        {"name": "B", "line_start": 5, "line_end": 8},
        {"name": "C", "line_start": 9, "line_end": 12},
    ]}
    result = build_chunks(program)
    assert [chunk["paragraphs"] for chunk in result] == [["A", "B"], ["C"]]
    assert result[0]["line_span"] == [1, 8]


def test_run_writes_verified_rules_and_prompt_has_numbered_lines(tmp_path):
    """Produce one rules file per program with verified line spans."""
    ir_dir = make_ir_run(tmp_path)
    prompts = []

    def fake_ask(system, prompt):
        """Record the prompt and answer with one good and one bad rule."""
        prompts.append(prompt)
        return reply([interest_rule(), interest_rule(500, 501)])

    out = tmp_path / "rules"
    manifest = run_business_rules(str(ir_dir), str(out), fake_ask, "fake-model")
    assert manifest["complete"] is True
    assert [item["path"] for item in manifest["files"]] == ["INTPGM.cbl"]
    assert manifest["files"][0]["rules"] == 2
    assert manifest["files"][0]["unverified"] == 1
    assert "    14 |" in prompts[0] and "COMPUTE WS-INTEREST" in prompts[0]
    assert "WS-RATE" in prompts[0]
    result = json.loads((out / "files" / "INTPGM.cbl.rules.json").read_text(encoding="utf-8"))
    good, bad = result["rules"]
    assert good["id"] == "rule:INTPGM.1"
    assert good["verified"] is True and good["line_span"] == [13, 15]
    assert good["paragraph"] == "CALC-PARA" and good["data"] == ["WS-BALANCE", "WS-RATE"]
    assert bad["verified"] is False and bad["line_span"] is None
    assert bad["claimed_lines"] == [500, 501]


def test_llm_error_marks_program_partial_and_run_continues(tmp_path):
    """Record a failed chunk instead of stopping the run."""
    ir_dir = make_ir_run(tmp_path)

    def failing_ask(system, prompt):
        """Simulate a network failure."""
        raise OSError("network down")

    manifest = run_business_rules(str(ir_dir), str(tmp_path / "rules"), failing_ask, "m")
    assert manifest["complete"] is True
    assert manifest["files"][0]["status"] == "partial"
    assert manifest["files"][0]["chunk_errors"] == 1


def test_cache_avoids_second_llm_call(tmp_path):
    """Reuse cached replies when the same prompt is sent again."""
    ir_dir = make_ir_run(tmp_path)
    calls = []

    def counting_ask(system, prompt):
        """Count calls and return one rule."""
        calls.append(prompt)
        return reply([interest_rule()])

    cache = tmp_path / "cache"
    run_business_rules(str(ir_dir), str(tmp_path / "r1"), counting_ask, "m", str(cache))
    run_business_rules(str(ir_dir), str(tmp_path / "r2"), counting_ask, "m", str(cache))
    assert len(calls) == 1


def test_stop_before_first_program_gives_incomplete_run(tmp_path):
    """Leave the run incomplete when stop is requested."""
    ir_dir = make_ir_run(tmp_path)
    manifest = run_business_rules(
        str(ir_dir), str(tmp_path / "rules"), lambda s, p: reply([]), "m",
        should_stop=lambda: True,
    )
    assert manifest["complete"] is False
    assert manifest["files"] == []


def test_api_requires_key_and_runs_with_fake_llm(tmp_path, monkeypatch):
    """Reject a run without a key, then run Stage 4 through the JSON API."""
    import app as flask_app
    from tests.test_api_pipeline import wait_for_job

    ir_dir = make_ir_run(tmp_path)
    stage2 = tmp_path / "workspace" / "stage2_outputs" / "src_ir_1"
    stage2.parent.mkdir(parents=True)
    ir_dir.rename(stage2)
    monkeypatch.setattr(flask_app, "WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.setattr(llm, "ENV_PATH", str(tmp_path / "missing.env"))
    for name in llm.ENV_NAMES.values():
        monkeypatch.delenv(name, raising=False)
    flask_app.app.config.update(TESTING=True)
    with flask_app.app.test_client() as client:
        assert client.post("/api/stage4/business-rules", json={}).status_code == 400
        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setattr(flask_app, "ASK_LLM", lambda s, p: reply([interest_rule()]))
        response = client.post("/api/stage4/business-rules", json={})
        assert response.status_code == 202
        status = wait_for_job(client, response.get_json()["job_id"])
        assert status["status"] == "complete"
        result = client.get(status["result_url"]).get_json()
        assert result["files"][0]["rules"] == 1
