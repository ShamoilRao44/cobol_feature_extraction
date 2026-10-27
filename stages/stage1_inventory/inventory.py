import hashlib
import json
import os
from datetime import datetime
from typing import Callable

from stages.stage1_inventory.classifier import classify
from stages.stage1_inventory.extractors import extract
from stages.stage1_inventory.linker import link_inventory
from stages.stage1_inventory.reader import read_file
from stages.stage1_inventory.scanner import list_files


def build_inventory(
    folder: str,
    should_stop: Callable[[], bool] | None = None,
    on_progress: Callable[[int, int, str | None], None] | None = None,
    on_classified: Callable[[dict], None] | None = None,
) -> dict:
    """Read and classify files, optionally stopping between files."""
    entries = []
    paths = list_files(folder)
    if on_progress:
        on_progress(0, len(paths), None)

    for relative_path in paths:
        if should_stop and should_stop():
            break

        content = read_file(os.path.join(folder, relative_path))
        classification = classify(content)
        declared_names, references = extract(
            content,
            classification.file_type,
            relative_path,
        )
        file_path = os.path.join(folder, relative_path)
        with open(file_path, "rb") as source_file:
            file_hash = hashlib.sha256(source_file.read()).hexdigest()
        entries.append({
            "path": relative_path,
            "type": classification.file_type,
            "confidence": classification.confidence,
            "evidence": classification.evidence,
            "runner_up": classification.runner_up,
            "scores": classification.scores,
            "kind": content.kind,
            "encoding": content.encoding,
            "line_ending": content.line_ending,
            "source_format": content.source_format,
            "size_bytes": os.path.getsize(file_path),
            "line_count": len(content.raw_lines),
            "code_line_count": len(content.code_lines),
            "sha256": file_hash,
            "declared_names": declared_names,
            "references": references,
        })
        if on_classified:
            on_classified(entries[-1])
        if on_progress:
            on_progress(len(entries), len(paths), relative_path)

    entries.sort(key=lambda entry: entry["path"])
    by_type = {}
    low_confidence = []
    for entry in entries:
        file_type = entry["type"]
        by_type[file_type] = by_type.get(file_type, 0) + 1
        if entry["confidence"] == "low":
            low_confidence.append(entry["path"])

    stopped = bool(should_stop and should_stop())
    if stopped:
        links = {
            "gaps": [],
            "entry_points": [],
            "duplicates": {"names": [], "identical_files": []},
        }
    else:
        if on_progress:
            on_progress(len(entries), len(paths), "Resolving references")
        links = link_inventory(entries)

    inventory = {
        "complete": not stopped,
        "source_folder": folder,
        "summary": {
            "total_files": len(entries),
            "by_type": by_type,
            "low_confidence": low_confidence,
            "gap_count": len(links["gaps"]),
            "entry_point_count": len(links["entry_points"]),
        },
        "files": entries,
    }
    inventory.update(links)
    return inventory


def write_inventory(inventory: dict, workspace_dir: str) -> str:
    """Write a timestamped inventory JSON file and return its path."""
    source_name = os.path.basename(os.path.normpath(inventory["source_folder"]))
    output_dir = os.path.join(workspace_dir, "stage1_outputs")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{source_name}_inventory_{timestamp}.json"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as output:
        json.dump(inventory, output, indent=2, ensure_ascii=False)
    return output_path
