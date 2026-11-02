import json
import os
from datetime import datetime

from stages.stage3_project_ir.builder import build_project_ir
from stages.stage3_project_ir.loader import load_ir_run


def run_project_ir(ir_dir, output_root=None, progress=None, should_stop=None):
    """Load an IR run, build its project document, and persist the result."""
    if output_root is None:
        repository_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        output_root = os.path.join(repository_root, "workspace", "stage3_outputs")
    meta, files = load_ir_run(ir_dir)
    meta["ir_dir"] = os.path.basename(os.path.normpath(ir_dir))
    project_ir = build_project_ir(files, meta, progress, should_stop)
    if project_ir is None:
        return {"stopped": True}
    source_name = os.path.basename(os.path.normpath(meta.get("source_folder") or "project"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(
        output_root, f"{source_name}_project_ir_{timestamp}"
    )
    os.makedirs(output_dir, exist_ok=True)
    project_ir_path = os.path.join(output_dir, "project_ir.json")
    with open(project_ir_path, "w", encoding="utf-8") as output:
        json.dump(project_ir, output, indent=2, ensure_ascii=False)
    summary = dict(project_ir["profile"])
    summary.update({
        "entry_points": len(project_ir["entry_points"]),
        "waves": len(project_ir["conversion_order"]["waves"]),
        "gaps": len(project_ir["gaps"]),
        "resolved_ratio": project_ir["quality"]["resolved_ratio"],
        "authoritative": project_ir["quality"]["authoritative"],
    })
    return {
        "stopped": False,
        "output_dir": output_dir,
        "project_ir_path": project_ir_path,
        "summary": summary,
    }
