import json
import os

from stages.stage1_inventory.classifier import classify
from stages.stage1_inventory.reader import read_file
from stages.stage1_inventory.scanner import list_files


def build_inventory(folder: str) -> dict:
    """Read and classify every file in a folder."""
    entries = []
    for relative_path in list_files(folder):
        content = read_file(os.path.join(folder, relative_path))
        classification = classify(content)
        entries.append(
            {
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
                "size_bytes": os.path.getsize(os.path.join(folder, relative_path)),
                "line_count": len(content.raw_lines),
                "code_line_count": len(content.code_lines),
            }
        )

    entries.sort(key=lambda entry: entry["path"])
    by_type = {}
    low_confidence = []
    for entry in entries:
        file_type = entry["type"]
        by_type[file_type] = by_type.get(file_type, 0) + 1
        if entry["confidence"] == "low":
            low_confidence.append(entry["path"])

    return {
        "source_folder": folder,
        "summary": {
            "total_files": len(entries),
            "by_type": by_type,
            "low_confidence": low_confidence,
        },
        "files": entries,
    }


def write_inventory(inventory: dict, workspace_dir: str) -> str:
    """Write an inventory JSON file and return its path."""
    os.makedirs(workspace_dir, exist_ok=True)
    output_path = os.path.join(workspace_dir, "inventory.json")
    with open(output_path, "w", encoding="utf-8") as output:
        json.dump(inventory, output, indent=2, ensure_ascii=False)
    return output_path
