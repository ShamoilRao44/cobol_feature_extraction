import json
import os
import shutil
import threading
import uuid
from datetime import datetime
from glob import glob

from flask import Flask, jsonify, render_template, request, send_file

from stages.stage1_inventory.inventory import build_inventory, write_inventory
from stages.stage2_ir.runner import run_ir

app = Flask(__name__)
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
JOBS = {}
JOBS_LOCK = threading.Lock()
LATEST_INVENTORY = None
LATEST_INVENTORY_PATH = None


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
                    job["logs"].append(f"Found {total} files. Classification started.")
                elif relative_path == "Resolving references":
                    job["logs"].append("Resolving references")
                else:
                    job["logs"].append(f"Classified {processed}/{total}: {relative_path}")

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
                job["logs"].append(
                    f"Stopped after {job['processed']} of {job['total']} files."
                )
            else:
                job["logs"].append("Classification complete.")
            job["logs"].append(f"Inventory JSON stored in {relative_output}")
            if inventory["complete"]:
                LATEST_INVENTORY = inventory
                LATEST_INVENTORY_PATH = output_path
    except (OSError, ValueError) as error:
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["status"] = "error"
            job["error"] = str(error)
            job["logs"].append(f"Error: {error}")


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

    job_id = uuid.uuid4().hex
    job = {
        "job_type": "inventory",
        "folder_path": folder_path,
        "status": "running",
        "logs": ["Inventory started."],
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
    thread = threading.Thread(
        target=run_inventory,
        args=(job_id, folder_path),
        daemon=True,
    )
    thread.start()

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
                job["logs"].append(message)

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
            job["logs"].append(
                "IR build complete."
                if result["complete"]
                else f"IR build stopped after {len(result['files'])} files."
            )
    except (OSError, ValueError) as error:
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["status"] = "error"
            job["error"] = str(error)
            job["logs"].append(f"Error: {error}")


@app.route("/build-ir", methods=["POST"])
def start_ir_build():
    """Start an IR run for the latest completed Stage 1 inventory."""
    inventory, inventory_path = latest_completed_inventory()
    if inventory is None:
        return jsonify({"error": "No completed inventory is available"}), 400
    source_folder = inventory.get("source_folder", "")
    if not os.path.isdir(source_folder):
        return jsonify({"error": f"Source folder not found: {source_folder}"}), 400

    source_name = os.path.basename(os.path.normpath(source_folder))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(
        WORKSPACE_DIR,
        "stage2_outputs",
        f"{source_name}_ir_{timestamp}",
    )
    job_id = uuid.uuid4().hex
    job = {
        "job_type": "ir",
        "folder_path": source_folder,
        "status": "running",
        "logs": ["IR build started."],
        "processed": 0,
        "total": len(inventory["files"]),
        "stop_event": threading.Event(),
        "inventory": inventory,
        "inventory_path": inventory_path,
        "display_path": None,
        "ir_result": None,
        "error": None,
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
    thread = threading.Thread(
        target=run_ir_job,
        args=(job_id, inventory, source_folder, output_dir),
        daemon=True,
    )
    thread.start()
    return jsonify({"job_id": job_id})


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
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return jsonify({"error": "Inventory job not found"}), 404
        if job["status"] == "running":
            job["stop_event"].set()
            job["logs"].append("Stop requested. Finishing the current file...")
    return jsonify({"status": job["status"]})


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
