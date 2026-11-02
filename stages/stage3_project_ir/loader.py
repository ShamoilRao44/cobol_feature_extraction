import json
import os


def load_ir_run(ir_dir: str) -> tuple[dict, dict[str, dict]]:
    """Load one per-file IR run and report missing files."""
    manifest_path = os.path.join(ir_dir, "ir_run.json")
    with open(manifest_path, encoding="utf-8") as source:
        manifest = json.load(source)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files", []), list):
        raise ValueError("Invalid per-file IR run manifest")
    meta = {
        "source_folder": manifest.get("source_folder"),
        "generated_at": manifest.get("generated_at"),
        "complete": manifest.get("complete", False),
        "load_warnings": [],
    }
    files = {}
    for entry in manifest.get("files", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not isinstance(entry.get("ir_file"), str):
            raise ValueError("Invalid per-file IR manifest entry")
        path = entry["path"]
        ir_path = os.path.abspath(os.path.join(ir_dir, entry["ir_file"]))
        if os.path.commonpath([os.path.abspath(ir_dir), ir_path]) != os.path.abspath(ir_dir):
            raise ValueError(f"IR file is outside the run directory: {entry['ir_file']}")
        try:
            with open(ir_path, encoding="utf-8") as source:
                item = json.load(source)
                if not isinstance(item, dict):
                    raise ValueError(f"Invalid IR document: {entry['ir_file']}")
                files[path] = item
        except FileNotFoundError:
            meta["load_warnings"].append(f"Missing IR file: {entry['ir_file']}")
    return meta, files
