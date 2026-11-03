import json
import os
import shutil
import threading
import uuid
from datetime import datetime
from glob import glob

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import BadRequest

from stages.stage1_inventory.inventory import build_inventory, write_inventory
from stages.stage2_ir.runner import run_ir
from stages.stage3_project_ir.runner import run_project_ir
from stages.stage4_business_rules.llm import api_key, ask_grok, model_name
from stages.stage4_business_rules.runner import run_business_rules

app = Flask(__name__)
ASK_LLM = ask_grok
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
JOBS = {}
JOBS_LOCK = threading.Lock()
LATEST_INVENTORY = None
LATEST_INVENTORY_PATH = None


def parse_api_json():
    """Parse a JSON request body or return an API error response."""
    if not request.is_json:
        return None, (jsonify({"error": "Content-Type must be application/json"}), 415)
    try:
        body = request.get_json()
    except BadRequest:
        return None, (jsonify({"error": "Request body must contain valid JSON"}), 400)
    if not isinstance(body, dict):
        return None, (jsonify({"error": "Request body must be a JSON object"}), 400)
    return body, None


def latest_completed_inventory():
    """Return the newest completed inventory and its path."""
    global LATEST_INVENTORY, LATEST_INVENTORY_PATH
    with JOBS_LOCK:
        if LATEST_INVENTORY and LATEST_INVENTORY.get("complete") is True:
            return LATEST_INVENTORY, LATEST_INVENTORY_PATH

    stage1_dir = os.path.join(WORKSPACE_DIR, "stage1_outputs")
    candidates = sorted(
        glob(os.path.join(stage1_dir, "*_inventory_*.json")),
        key=os.path.getmtime,
        reverse=True,
    )
    for candidate in candidates:
        try:
            with open(candidate, encoding="utf-8") as source:
                inventory = json.load(source)
        except (OSError, json.JSONDecodeError):
            continue
        if inventory.get("complete") is True:
            with JOBS_LOCK:
                LATEST_INVENTORY = inventory
                LATEST_INVENTORY_PATH = candidate
            return inventory, candidate
    return None, None


def append_job_log(job_id, message):
    """Store and immediately print one job progress message."""
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is not None:
            job["logs"].append(message)
    print(f"[{job_id}] {message}", flush=True)


def latest_completed_ir_run():
    """Find the newest complete per-file IR run."""
    stage2_dir = os.path.join(WORKSPACE_DIR, "stage2_outputs")
    candidates = sorted(
        glob(os.path.join(stage2_dir, "*_ir_*", "ir_run.json")),
        key=os.path.getmtime,
        reverse=True,
    )
    for candidate in candidates:
        try:
            with open(candidate, encoding="utf-8") as source:
                manifest = json.load(source)
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("complete") is True:
            return os.path.dirname(candidate)
    return None


def create_inventory_job(folder_path):
    """Create and start an inventory background job."""
    job_id = uuid.uuid4().hex
    job = {
        "job_type": "inventory",
        "folder_path": folder_path,
        "status": "running",
        "logs": [],
        "processed": 0,
        "total": 0,
        "stop_event": threading.Event(),
        "inventory": None,
        "inventory_path": None,
        "display_path": None,
        "error": None,
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
    append_job_log(job_id, "Inventory started.")
    thread = threading.Thread(target=run_inventory, args=(job_id, folder_path), daemon=True)
    thread.start()
    return job_id, job


@app.route("/api/stage1/inventory", methods=["POST"])
def api_start_inventory():
    """Start inventory extraction from a JSON folder path."""
    body, error = parse_api_json()
    if error:
        return error
    folder_path = body.get("folder_path")
    if not isinstance(folder_path, str) or not folder_path.strip():
        return jsonify({"error": "folder_path must be a non-empty string"}), 400
    folder_path = folder_path.strip().strip('"')
    if not os.path.isdir(folder_path):
        return jsonify({"error": f"Folder not found: {folder_path}"}), 400
    job_id, _ = create_inventory_job(folder_path)
    return jsonify({
        "job_id": job_id,
        "status": "running",
        "status_url": f"/api/jobs/{job_id}",
        "result_url": f"/api/jobs/{job_id}/result",
    }), 202


def run_inventory(job_id, folder_path):
    """Build and save an inventory in a background thread."""
    global LATEST_INVENTORY, LATEST_INVENTORY_PATH
    try:
        source_name = os.path.basename(os.path.normpath(folder_path))
        sorted_folder = os.path.join(WORKSPACE_DIR, f"sorted_{source_name}")

        def copy_classified_file(entry):
            """Copy a classified file into its type folder."""
            type_folder = os.path.join(sorted_folder, entry["type"])
            os.makedirs(type_folder, exist_ok=True)
            source_path = os.path.join(folder_path, entry["path"])
            destination_path = os.path.join(
                type_folder,
                os.path.basename(entry["path"]),
            )
            shutil.copy2(source_path, destination_path)

        def report_progress(processed, total, relative_path):
            """Update the job's progress and append a per-file message."""
            with JOBS_LOCK:
                job = JOBS[job_id]
                job["processed"] = processed
                job["total"] = total
                if relative_path is None:
                    message = f"Found {total} files. Classification started."
                elif relative_path == "Resolving references":
                    message = "Resolving references"
                else:
                    message = f"Classified {processed}/{total}: {relative_path}"
            append_job_log(job_id, message)

        inventory = build_inventory(
            folder_path,
            should_stop=JOBS[job_id]["stop_event"].is_set,
            on_progress=report_progress,
            on_classified=copy_classified_file,
        )
        output_path = write_inventory(inventory, WORKSPACE_DIR)
        relative_output = os.path.relpath(
            output_path,
            os.path.dirname(__file__),
        ).replace(os.sep, "/")
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["inventory"] = inventory
            job["inventory_path"] = output_path
            job["display_path"] = relative_output
            job["status"] = "complete" if inventory["complete"] else "stopped"
            if job["status"] == "stopped":
                final_message = f"Stopped after {job['processed']} of {job['total']} files."
            else:
                final_message = "Classification complete."
                if inventory["complete"]:
                    LATEST_INVENTORY = inventory
                    LATEST_INVENTORY_PATH = output_path
        append_job_log(job_id, final_message)
        if inventory["complete"]:
            append_job_log(job_id, f"Inventory JSON stored in {relative_output}")
    except (OSError, ValueError) as error:
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["status"] = "error"
            job["error"] = str(error)
        append_job_log(job_id, f"Error: {error}")


@app.route("/", methods=["GET", "POST"])
def index():
    """Render the inventory page or start an inventory job."""
    if request.method == "GET":
        inventory, _ = latest_completed_inventory()
        return render_template(
            "index.html",
            folder_path="",
            inventory=inventory,
            error=None,
            job=None,
            job_id=None,
            ir_result=None,
            inventory_ready=inventory is not None,
        )

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    submitted_path = request.form.get("folder_path", "")
    folder_path = submitted_path.strip().strip('"')

    if not os.path.isdir(folder_path):
        error = f"Folder not found: {folder_path}"
        if is_ajax:
            return jsonify({"error": error}), 400
        return render_template(
            "index.html",
            folder_path=submitted_path,
            inventory=None,
            error=error,
            job=None,
            job_id=None,
            ir_result=None,
            inventory_ready=False,
        )

    job_id, job = create_inventory_job(folder_path)

    if is_ajax:
        return jsonify({"job_id": job_id})

    return render_template(
        "index.html",
        folder_path=submitted_path,
        inventory=None,
        error=None,
        job=job,
        job_id=job_id,
        ir_result=None,
        inventory_ready=False,
    )


def run_ir_job(job_id, inventory, source_folder, output_dir):
    """Build per-file IR in the background."""
    try:
        processed = 0

        def report_progress(message):
            """Append an IR progress message to its job."""
            nonlocal processed
            processed += 1
            with JOBS_LOCK:
                job = JOBS[job_id]
                job["processed"] = processed
            append_job_log(job_id, message)

        result = run_ir(
            inventory,
            source_folder,
            output_dir,
            progress=report_progress,
            should_stop=JOBS[job_id]["stop_event"].is_set,
        )
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["ir_result"] = result
            job["display_path"] = os.path.relpath(
                output_dir,
                os.path.dirname(__file__),
            ).replace(os.sep, "/")
            job["status"] = "complete" if result["complete"] else "stopped"
            final_message = "IR build complete." if result["complete"] else (
                f"IR build stopped after {len(result['files'])} files."
            )
        append_job_log(job_id, final_message)
    except (OSError, ValueError) as error:
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["status"] = "error"
            job["error"] = str(error)
        append_job_log(job_id, f"Error: {error}")


def create_ir_job(inventory, inventory_path):
    """Create and start a per-file IR background job."""
    source_folder = inventory.get("source_folder", "")
    if not os.path.isdir(source_folder):
        return None, f"Source folder not found: {source_folder}"
    source_name = os.path.basename(os.path.normpath(source_folder))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(
        WORKSPACE_DIR, "stage2_outputs", f"{source_name}_ir_{timestamp}"
    )
    job_id = uuid.uuid4().hex
    job = {
        "job_type": "ir",
        "folder_path": source_folder,
        "status": "running",
        "logs": [],
        "processed": 0,
        "total": len(inventory["files"]),
        "stop_event": threading.Event(),
        "inventory": inventory,
        "inventory_path": inventory_path,
        "display_path": None,
        "ir_result": None,
        "ir_output_dir": output_dir,
        "error": None,
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
    append_job_log(job_id, "IR build started.")
    thread = threading.Thread(
        target=run_ir_job,
        args=(job_id, inventory, source_folder, output_dir),
        daemon=True,
    )
    thread.start()
    return job_id, None


def run_project_ir_job(job_id, ir_dir, output_root):
    """Build project IR in the background and report each phase."""
    try:
        def report_progress(message):
            """Record a project IR phase in the terminal and job stream."""
            with JOBS_LOCK:
                job = JOBS[job_id]
                job["processed"] += 1
            append_job_log(job_id, message)

        result = run_project_ir(
            ir_dir,
            output_root,
            progress=report_progress,
            should_stop=JOBS[job_id]["stop_event"].is_set,
        )
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["project_result"] = result
            job["display_path"] = (
                os.path.relpath(result["output_dir"], os.path.dirname(__file__))
                .replace(os.sep, "/")
                if not result.get("stopped") else None
            )
            job["project_ir_path"] = result.get("project_ir_path")
            job["status"] = "stopped" if result.get("stopped") else "complete"
            if not result.get("stopped"):
                job["total"] = job["processed"]
        append_job_log(
            job_id,
            "Project IR build stopped."
            if result.get("stopped")
            else f"Project IR complete: {result['project_ir_path']}",
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["status"] = "error"
            job["error"] = str(error)
        append_job_log(job_id, f"Error: {error}")


@app.route("/build-ir", methods=["POST"])
def start_ir_build():
    """Start an IR run for the latest completed Stage 1 inventory."""
    inventory, inventory_path = latest_completed_inventory()
    if inventory is None:
        return jsonify({"error": "No completed inventory is available"}), 400
    job_id, error = create_ir_job(inventory, inventory_path)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"job_id": job_id})


@app.route("/api/stage2/ir", methods=["POST"])
def api_start_ir():
    """Start per-file IR from a completed inventory."""
    body, error = parse_api_json()
    if error:
        return error
    inventory_job_id = body.get("inventory_job_id")
    if inventory_job_id is not None:
        with JOBS_LOCK:
            inventory_job = JOBS.get(inventory_job_id)
            inventory = inventory_job.get("inventory") if inventory_job else None
            inventory_path = inventory_job.get("inventory_path") if inventory_job else None
            inventory_status = inventory_job.get("status") if inventory_job else None
        if inventory_job is None:
            return jsonify({"error": "Inventory job not found"}), 404
        if inventory_status != "complete" or not inventory:
            return jsonify({"error": "Inventory job is not complete"}), 409
    else:
        inventory, inventory_path = latest_completed_inventory()
    if inventory is None:
        return jsonify({"error": "No completed inventory is available"}), 400
    job_id, error = create_ir_job(inventory, inventory_path)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({
        "job_id": job_id,
        "status": "running",
        "status_url": f"/api/jobs/{job_id}",
        "result_url": f"/api/jobs/{job_id}/result",
    }), 202


def resolve_ir_run(body):
    """Return (ir_dir, manifest, None) for the requested or latest complete IR run, or an error response."""
    stage2_root = os.path.abspath(os.path.join(WORKSPACE_DIR, "stage2_outputs"))
    requested_dir = body.get("ir_dir")
    if requested_dir is None:
        ir_dir = latest_completed_ir_run()
    elif isinstance(requested_dir, str) and requested_dir.strip():
        ir_dir = requested_dir.strip()
        if not os.path.isabs(ir_dir):
            ir_dir = os.path.join(stage2_root, ir_dir)
        ir_dir = os.path.realpath(ir_dir)
        try:
            within_stage2 = os.path.commonpath([os.path.realpath(stage2_root), ir_dir]) == os.path.realpath(stage2_root)
        except ValueError:
            within_stage2 = False
        if not within_stage2:
            return None, None, (jsonify({"error": "ir_dir must be within workspace/stage2_outputs"}), 400)
    else:
        return None, None, (jsonify({"error": "ir_dir must be a non-empty string"}), 400)
    manifest_path = os.path.join(ir_dir, "ir_run.json") if ir_dir else ""
    if not ir_dir or not os.path.isfile(manifest_path):
        return None, None, (jsonify({"error": "No complete per-file IR run is available"}), 400)
    try:
        with open(manifest_path, encoding="utf-8") as source:
            manifest = json.load(source)
    except (OSError, json.JSONDecodeError) as error:
        return None, None, (jsonify({"error": f"Could not read IR run manifest: {error}"}), 400)
    if not isinstance(manifest, dict):
        return None, None, (jsonify({"error": "Invalid IR run manifest"}), 400)
    if manifest.get("complete") is not True:
        return None, None, (jsonify({"error": "The selected IR run is incomplete"}), 409)
    return ir_dir, manifest, None


@app.route("/api/stage3/project-ir", methods=["POST"])
def api_start_project_ir():
    """Start consolidated project IR from the latest or a selected IR run."""
    body, error = parse_api_json()
    if error:
        return error
    ir_dir, manifest, error = resolve_ir_run(body)
    if error:
        return error
    job_id = uuid.uuid4().hex
    job = {
        "job_type": "project_ir",
        "folder_path": manifest.get("source_folder", ""),
        "status": "running",
        "logs": [],
        "processed": 0,
        "total": 9,
        "stop_event": threading.Event(),
        "inventory": None,
        "inventory_path": None,
        "display_path": None,
        "project_ir_path": None,
        "project_result": None,
        "error": None,
        "ir_dir": ir_dir,
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
    append_job_log(job_id, "Project IR build started.")
    thread = threading.Thread(
        target=run_project_ir_job,
        args=(
            job_id,
            ir_dir,
            os.path.join(WORKSPACE_DIR, "stage3_outputs"),
        ),
        daemon=True,
    )
    thread.start()
    return jsonify({
        "job_id": job_id,
        "status": "running",
        "status_url": f"/api/jobs/{job_id}",
        "result_url": f"/api/jobs/{job_id}/result",
    }), 202


def run_business_rules_job(job_id, ir_dir, output_dir):
    """Extract business rules in the background and report each program."""
    try:
        def report_progress(message):
            """Record one program's progress in the terminal and job stream."""
            with JOBS_LOCK:
                JOBS[job_id]["processed"] += 1
            append_job_log(job_id, message)

        result = run_business_rules(
            ir_dir,
            output_dir,
            ask=ASK_LLM,
            model=model_name(),
            cache_dir=os.path.join(WORKSPACE_DIR, "stage4_cache"),
            progress=report_progress,
            should_stop=JOBS[job_id]["stop_event"].is_set,
        )
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["rules_result"] = result
            job["display_path"] = os.path.relpath(
                output_dir, os.path.dirname(__file__)
            ).replace(os.sep, "/")
            job["status"] = "complete" if result["complete"] else "stopped"
            rule_count = sum(item["rules"] for item in result["files"])
            final_message = (
                f"Business rules complete: {rule_count} rules from {len(result['files'])} programs."
                if result["complete"]
                else f"Business rules stopped after {len(result['files'])} programs."
            )
        append_job_log(job_id, final_message)
    except (OSError, ValueError, KeyError, TypeError) as error:
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["status"] = "error"
            job["error"] = str(error)
        append_job_log(job_id, f"Error: {error}")


@app.route("/api/stage4/business-rules", methods=["POST"])
def api_start_business_rules():
    """Start business-rule extraction from the latest or a selected IR run."""
    body, error = parse_api_json()
    if error:
        return error
    if not api_key():
        return jsonify({"error": "GROK_API_KEY is not set"}), 400
    ir_dir, manifest, error = resolve_ir_run(body)
    if error:
        return error
    source_folder = manifest.get("source_folder", "")
    if not os.path.isdir(source_folder):
        return jsonify({"error": f"Source folder not found: {source_folder}"}), 400
    source_name = os.path.basename(os.path.normpath(source_folder))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(
        WORKSPACE_DIR, "stage4_outputs", f"{source_name}_rules_{timestamp}"
    )
    job_id = uuid.uuid4().hex
    job = {
        "job_type": "business_rules",
        "folder_path": source_folder,
        "status": "running",
        "logs": [],
        "processed": 0,
        "total": sum(1 for item in manifest.get("files", []) if item.get("type") == "cobol_program"),
        "stop_event": threading.Event(),
        "inventory": None,
        "inventory_path": None,
        "display_path": None,
        "rules_result": None,
        "error": None,
        "ir_dir": ir_dir,
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
    append_job_log(job_id, f"Business rules started with model {model_name()}.")
    thread = threading.Thread(
        target=run_business_rules_job,
        args=(job_id, ir_dir, output_dir),
        daemon=True,
    )
    thread.start()
    return jsonify({
        "job_id": job_id,
        "status": "running",
        "status_url": f"/api/jobs/{job_id}",
        "result_url": f"/api/jobs/{job_id}/result",
    }), 202


@app.route("/api/jobs/<job_id>", methods=["GET"])
def api_job_status(job_id):
    """Return job progress, logs, and JSON result location."""
    since = request.args.get("since", default=0, type=int)
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return jsonify({"error": "Job not found"}), 404
        return jsonify({
            "job_id": job_id,
            "job_type": job["job_type"],
            "status": job["status"],
            "processed": job["processed"],
            "total": job["total"],
            "logs": job["logs"][max(0, since):],
            "log_count": len(job["logs"]),
            "error": job["error"],
            "result_url": f"/api/jobs/{job_id}/result",
            "files_url": (
                f"/api/stage2/ir/{job_id}/files"
                if job["job_type"] == "ir" else None
            ),
        })


@app.route("/api/stage2/ir/<job_id>/files", methods=["GET"])
def api_ir_files(job_id):
    """List generated per-file IR JSON documents."""
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None or job.get("job_type") != "ir":
            return jsonify({"error": "Per-file IR job not found"}), 404
        if job["status"] == "running":
            return jsonify({"error": "Per-file IR output is not ready"}), 409
        manifest = job.get("ir_result")
        if not manifest:
            return jsonify({"error": job.get("error") or "Per-file IR output is unavailable"}), 500
        files = [
            {
                "path": item["path"],
                "type": item["type"],
                "ir_file": item["ir_file"],
                "url": f"/api/stage2/ir/{job_id}/files/{item['ir_file']}",
            }
            for item in manifest["files"]
        ]
    return jsonify({"files": files})


@app.route("/api/stage2/ir/<job_id>/files/<path:ir_file>", methods=["GET"])
def api_ir_file(job_id, ir_file):
    """Return one generated per-file IR document as JSON."""
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None or job.get("job_type") != "ir":
            return jsonify({"error": "Per-file IR job not found"}), 404
        manifest = job.get("ir_result")
        output_dir = job.get("ir_output_dir")
        if job["status"] == "running":
            return jsonify({"error": "Per-file IR output is not ready"}), 409
        known_file = any(
            item.get("ir_file") == ir_file for item in (manifest or {}).get("files", [])
        )
    if not known_file or not output_dir:
        return jsonify({"error": "IR file not found"}), 404
    ir_path = os.path.abspath(os.path.join(output_dir, ir_file))
    if os.path.commonpath([os.path.abspath(output_dir), ir_path]) != os.path.abspath(output_dir):
        return jsonify({"error": "IR file is outside the output directory"}), 400
    try:
        with open(ir_path, encoding="utf-8") as source:
            return jsonify(json.load(source))
    except (OSError, json.JSONDecodeError) as error:
        return jsonify({"error": f"Could not read IR file: {error}"}), 500


@app.route("/api/jobs/<job_id>/result", methods=["GET"])
def api_job_result(job_id):
    """Return a completed stage result as JSON."""
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return jsonify({"error": "Job not found"}), 404
        if job["status"] == "running":
            return jsonify({"error": "Job result is not ready", "status": "running"}), 409
        if job["status"] == "error":
            return jsonify({"error": job["error"], "status": "error"}), 500
        job_type = job["job_type"]
        if job_type == "inventory":
            result = job["inventory"]
        elif job_type == "ir":
            result = job.get("ir_result")
        elif job_type == "business_rules":
            result = job.get("rules_result")
        else:
            result_path = job.get("project_ir_path")
            result = None
    if job_type == "project_ir":
        if not result_path or not os.path.isfile(result_path):
            return jsonify({"error": "Project IR result file is unavailable"}), 404
        try:
            with open(result_path, encoding="utf-8") as source:
                result = json.load(source)
        except (OSError, json.JSONDecodeError) as error:
            return jsonify({"error": f"Could not read project IR result: {error}"}), 500
    if result is None:
        return jsonify({"error": "Stage result is unavailable"}), 404
    return jsonify(result)


@app.route("/status/<job_id>", methods=["GET"])
def job_status(job_id):
    """Return new progress messages and the job state."""
    since = request.args.get("since", default=0, type=int)
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return jsonify({"error": "Inventory job not found"}), 404
        return jsonify(
            {
                "status": job["status"],
                "processed": job["processed"],
                "total": job["total"],
                "logs": job["logs"][max(0, since):],
                "log_count": len(job["logs"]),
            }
        )


@app.route("/stop/<job_id>", methods=["POST"])
def stop_job(job_id):
    """Request that an inventory job stop between files."""
    message = None
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return jsonify({"error": "Inventory job not found"}), 404
        if job["status"] == "running":
            job["stop_event"].set()
            message = "Stop requested. Finishing the current file..."
            status = job["status"]
        else:
            status = job["status"]
    if message:
        append_job_log(job_id, message)
    return jsonify({"status": status})


@app.route("/api/jobs/<job_id>/stop", methods=["POST"])
def api_stop_job(job_id):
    """Request that any running stage job stop at its next safe point."""
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return jsonify({"error": "Job not found"}), 404
        if job["status"] != "running":
            return jsonify({"status": job["status"]})
        job["stop_event"].set()
    append_job_log(job_id, "Stop requested. Finishing the current step...")
    return jsonify({"status": "stopping"})


@app.route("/result/<job_id>", methods=["GET"])
def job_result(job_id):
    """Render completed or partially completed inventory results."""
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None or job["status"] == "running":
            return "Inventory result not ready", 404
        job_view = {
            "job_type": job.get("job_type", "inventory"),
            "status": job["status"],
            "logs": list(job["logs"]),
            "display_path": job["display_path"],
            "error": job["error"],
        }
        inventory = job["inventory"]
        ir_result = job.get("ir_result")
    return render_template(
        "index.html",
        folder_path=job["folder_path"],
        inventory=inventory,
        error=job["error"],
        job=job_view,
        job_id=job_id,
        ir_result=ir_result,
        ir_output_path=job.get("display_path"),
        inventory_ready=inventory is not None and inventory.get("complete") is True,
    )


@app.route("/inventory/<job_id>", methods=["GET"])
def download_inventory(job_id):
    """Return a generated inventory JSON file."""
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        inventory_path = job["inventory_path"] if job else None
    if inventory_path is None or not os.path.isfile(inventory_path):
        return "No inventory yet", 404
    return send_file(inventory_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
