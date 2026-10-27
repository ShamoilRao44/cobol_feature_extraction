import os
import shutil
import threading
import uuid

from flask import Flask, jsonify, render_template, request, send_file

from stages.stage1_inventory.inventory import build_inventory, write_inventory

app = Flask(__name__)
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
JOBS = {}
JOBS_LOCK = threading.Lock()


def run_inventory(job_id, folder_path):
    """Build and save an inventory in a background thread."""
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
        return render_template(
            "index.html",
            folder_path="",
            inventory=None,
            error=None,
            job=None,
            job_id=None,
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
        )

    job_id = uuid.uuid4().hex
    job = {
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
    )


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
            "status": job["status"],
            "logs": list(job["logs"]),
            "display_path": job["display_path"],
            "error": job["error"],
        }
        inventory = job["inventory"]
    return render_template(
        "index.html",
        folder_path=job["folder_path"],
        inventory=inventory,
        error=job["error"],
        job=job_view,
        job_id=job_id,
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
