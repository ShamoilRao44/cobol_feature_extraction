import time


def wait_for_job(client, job_id):
    """Poll a background job until it leaves the running state."""
    for _ in range(500):
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        status = response.get_json()
        if status["status"] != "running":
            return status
        time.sleep(0.01)
    raise AssertionError(f"Job {job_id} did not finish")


def test_json_api_runs_all_stages_and_prints_live_logs(tmp_path, monkeypatch, capsys):
    """Run all stages through JSON APIs and expose progress in the terminal."""
    import app as flask_app

    source = tmp_path / "source"
    source.mkdir()
    (source / "notes.md").write_text("# notes\n- api pipeline", encoding="utf-8")
    monkeypatch.setattr(flask_app, "WORKSPACE_DIR", str(tmp_path / "workspace"))
    flask_app.app.config.update(TESTING=True)

    with flask_app.app.test_client() as client:
        inventory_response = client.post(
            "/api/stage1/inventory",
            json={"folder_path": str(source)},
        )
        assert inventory_response.status_code == 202
        inventory_job_id = inventory_response.get_json()["job_id"]
        inventory_status = wait_for_job(client, inventory_job_id)
        assert inventory_status["status"] == "complete"
        inventory_result = client.get(
            inventory_status["result_url"]
        ).get_json()
        assert inventory_result["complete"] is True

        ir_response = client.post(
            "/api/stage2/ir",
            json={"inventory_job_id": inventory_job_id},
        )
        assert ir_response.status_code == 202
        ir_job_id = ir_response.get_json()["job_id"]
        ir_status = wait_for_job(client, ir_job_id)
        assert ir_status["status"] == "complete"
        ir_result = client.get(ir_status["result_url"]).get_json()
        assert ir_result["complete"] is True
        ir_files = client.get(f"/api/stage2/ir/{ir_job_id}/files").get_json()["files"]
        assert ir_files
        one_file = client.get(ir_files[0]["url"])
        assert one_file.status_code == 200
        assert one_file.get_json()["schema_version"] == "1.1"

        project_response = client.post("/api/stage3/project-ir", json={})
        assert project_response.status_code == 202
        project_job_id = project_response.get_json()["job_id"]
        project_status = wait_for_job(client, project_job_id)
        assert project_status["status"] == "complete"
        project_result = client.get(project_status["result_url"]).get_json()
        assert project_result["modules"] == []
        assert project_result["schema_version"] == "1.0"

    terminal = capsys.readouterr().out
    assert f"[{inventory_job_id}] Classified 1/1: notes.md" in terminal
    assert f"[{ir_job_id}] IR 1/1: notes.md" in terminal
    assert f"[{project_job_id}] Project IR: quality" in terminal
