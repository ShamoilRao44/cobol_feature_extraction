import json
import os
from datetime import datetime, timezone
from glob import glob
from typing import Callable

from stages.stage1_inventory.reader import read_file
from stages.stage2_ir.builder import build_file_ir


def run_ir(
    inventory: dict,
    source_folder: str,
    output_dir: str,
    progress: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> dict:
    """Build per-file IR documents and write the run manifest."""
    inventory_files = inventory["files"]
    output_files = []
    files_dir = os.path.join(output_dir, "files")
    os.makedirs(files_dir, exist_ok=True)

    for index, entry in enumerate(inventory_files, start=1):
        if should_stop and should_stop():
            break
        content = read_file(os.path.join(source_folder, entry["path"]))
        file_ir = build_file_ir(
            content,
            entry["type"],
            entry["path"],
            entry.get("declared_names", []),
            entry["sha256"],
        )
        ir_path = os.path.join(files_dir, f"{entry['path']}.ir.json")
        os.makedirs(os.path.dirname(ir_path), exist_ok=True)
        with open(ir_path, "w", encoding="utf-8") as output:
            json.dump(file_ir, output, indent=2, ensure_ascii=False)
        relative_ir_path = os.path.relpath(ir_path, output_dir).replace(os.sep, "/")
        output_files.append(
            {
                "path": entry["path"],
                "type": entry["type"],
                "ir_file": relative_ir_path,
                "parse_status": file_ir["parse_status"],
                "counts": _counts(file_ir),
            }
        )
        if progress:
            progress(f"IR {index}/{len(inventory_files)}: {entry['path']}")

    complete = len(output_files) == len(inventory_files)
    manifest = {
        "schema_version": "1.0",
        "source_folder": source_folder,
        "inventory_file": _inventory_path(inventory, output_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "complete": complete,
        "files": output_files,
    }
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "ir_run.json"), "w", encoding="utf-8") as output:
        json.dump(manifest, output, indent=2, ensure_ascii=False)
    return manifest


def _counts(file_ir: dict) -> dict:
    """Summarize parsed structure counts by body type."""
    if "program" in file_ir:
        program = file_ir["program"]
        metrics = program["metrics"]
        return {
            "paragraphs": metrics["paragraphs"],
            "sql": metrics["sql"],
            "cics": metrics["cics"],
            "calls": metrics["calls"],
            "conditions": metrics["conditions"],
        }
    if "jcl" in file_ir:
        jcl = file_ir["jcl"]
        return {
            "steps": len(jcl["steps"]),
            "dds": sum(len(step["dds"]) for step in jcl["steps"]),
        }
    if "copybook" in file_ir:
        copybook = file_ir["copybook"]
        return {
            "data_items": len(copybook["data_items"]),
            "copies": len(copybook["copies"]),
        }
    if "bms" in file_ir:
        bms = file_ir["bms"]
        return {"maps": len(bms["maps"]), "fields": bms["field_count"]}
    return {}


def _inventory_path(inventory: dict, output_dir: str) -> str:
    """Find the completed inventory file associated with this source."""
    workspace_dir = os.path.dirname(os.path.dirname(output_dir))
    stage1_dir = os.path.join(workspace_dir, "stage1_outputs")
    candidates = sorted(
        glob(os.path.join(stage1_dir, "*_inventory_*.json")),
        key=os.path.getmtime,
        reverse=True,
    )
    for candidate in candidates:
        try:
            with open(candidate, encoding="utf-8") as source:
                saved_inventory = json.load(source)
        except (OSError, json.JSONDecodeError):
            continue
        if (
            saved_inventory.get("complete") is True
            and saved_inventory.get("source_folder") == inventory.get("source_folder")
        ):
            return os.path.relpath(candidate, workspace_dir).replace(os.sep, "/")
    return ""
