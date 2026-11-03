import json
import os
from datetime import datetime, timezone
from typing import Callable

from stages.stage1_inventory.reader import read_file
from stages.stage3_project_ir.loader import load_ir_run
from stages.stage4_business_rules.rules import Ask, build_program_rules


def run_business_rules(
    ir_dir: str,
    output_dir: str,
    ask: Ask,
    model: str,
    cache_dir: str | None = None,
    progress: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> dict:
    """Extract business rules for every program in an IR run and write the manifest."""
    meta, files = load_ir_run(ir_dir)
    source_folder = meta.get("source_folder") or ""
    programs = [path for path in sorted(files) if files[path].get("program")]
    files_dir = os.path.join(output_dir, "files")
    os.makedirs(files_dir, exist_ok=True)
    output_files = []

    for index, path in enumerate(programs, start=1):
        if should_stop and should_stop():
            break
        if progress:
            progress(f"Rules {index}/{len(programs)}: {path}")
        content = read_file(os.path.join(source_folder, path))
        result = build_program_rules(files[path], content.raw_lines, ask, model, cache_dir)
        rules_path = os.path.join(files_dir, f"{path}.rules.json")
        os.makedirs(os.path.dirname(rules_path), exist_ok=True)
        with open(rules_path, "w", encoding="utf-8") as output:
            json.dump(result, output, indent=2, ensure_ascii=False)
        output_files.append({
            "path": path,
            "program": result["program"],
            "rules_file": os.path.relpath(rules_path, output_dir).replace(os.sep, "/"),
            "status": result["status"],
            "rules": len(result["rules"]),
            "unverified": sum(1 for rule in result["rules"] if not rule["verified"]),
            "chunks": len(result["chunks"]),
            "chunk_errors": sum(1 for chunk in result["chunks"] if chunk["status"] == "error"),
        })

    manifest = {
        "schema_version": "1.0",
        "source_folder": source_folder,
        "ir_run": os.path.basename(os.path.normpath(ir_dir)),
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "complete": len(output_files) == len(programs),
        "files": output_files,
    }
    with open(os.path.join(output_dir, "rules_run.json"), "w", encoding="utf-8") as output:
        json.dump(manifest, output, indent=2, ensure_ascii=False)
    return manifest
