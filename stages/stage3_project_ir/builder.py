from datetime import datetime, timezone

from stages.stage3_project_ir.flows import build_conversion_order, build_entry_points
from stages.stage3_project_ir.graph import build_edges, build_nodes
from stages.stage3_project_ir.quality import build_quality
from stages.stage3_project_ir.views import (
    build_catalogs,
    build_coupling,
    build_data_view,
    build_gaps,
    build_interfaces,
    build_profile,
    build_screens,
    fill_cards,
)


def build_project_ir(files, meta, progress=None, should_stop=None):
    """Consolidate per-file IR into one project graph and set of views."""
    phases = [
        "nodes", "edges", "entry points", "cards", "cycles and order", "data view",
        "interfaces and catalogs", "gaps and coupling", "quality",
    ]
    results = {}
    for phase in phases:
        if progress:
            progress(f"Project IR: {phase}")
        if should_stop and should_stop():
            return None
        if phase == "nodes":
            results["nodes"], results["index"], results["duplicates"] = build_nodes(files)
        elif phase == "edges":
            results["edges"], results["dynamic_refs"], results["info"] = build_edges(
                files, results["nodes"], results["index"]
            )
        elif phase == "entry points":
            results["entry_points"] = build_entry_points(
                results["nodes"], results["edges"], files
            )
        elif phase == "cards":
            fill_cards(
                results["nodes"], results["edges"], files, results["entry_points"]
            )
            results["profile"] = build_profile(
                results["nodes"], files, results["entry_points"]
            )
        elif phase == "cycles and order":
            results["cycles"], results["conversion_order"] = build_conversion_order(
                results["nodes"], results["edges"], results["entry_points"]
            )
        elif phase == "data view":
            results["data_stores"], results["crud_matrix"] = build_data_view(
                results["nodes"], results["edges"], files
            )
        elif phase == "interfaces and catalogs":
            results["interfaces"] = build_interfaces(
                results["nodes"], results["edges"], files
            )
            results["screens"] = build_screens(results["nodes"], results["edges"])
            results["catalogs"] = build_catalogs(
                results["nodes"], files, results["entry_points"]
            )
        elif phase == "gaps and coupling":
            results["gaps"] = build_gaps(
                results["nodes"], results["edges"], results["entry_points"],
                results["conversion_order"],
            )
            results["coupling"] = build_coupling(
                results["entry_points"], results["nodes"]
            )
        elif phase == "quality":
            caveats = list(results["info"]["caveats"])
            if results["duplicates"]:
                caveats.append(f"Duplicate ids: {len(results['duplicates'])}")
            results["quality"] = build_quality(
                results["nodes"], results["edges"], files, results["dynamic_refs"],
                results["conversion_order"], caveats,
            )
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_folder": meta.get("source_folder"),
        "ir_run": meta.get("ir_dir"),
        "complete": meta.get("complete", False),
        "profile": results["profile"],
        "nodes": [results["nodes"][node_id] for node_id in sorted(results["nodes"])],
        "edges": results["edges"],
        "entry_points": results["entry_points"],
        "cycles": results["cycles"],
        "conversion_order": results["conversion_order"],
        "data_stores": results["data_stores"],
        "crud_matrix": results["crud_matrix"],
        "interfaces": results["interfaces"],
        "screens": results["screens"],
        "catalogs": results["catalogs"],
        "gaps": results["gaps"],
        "coupling": results["coupling"],
        "modules": [],
        "shared": [],
        "boundary_edges": [],
        "module_order": [],
        "duplicates": results["duplicates"],
        "quality": results["quality"],
    }
