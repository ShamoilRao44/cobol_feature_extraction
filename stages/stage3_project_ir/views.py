from collections import Counter


DATA_KINDS = {"table", "dataset", "queue", "cics_file"}


def fill_cards(nodes, edges, files, entry_points):
    """Populate compact summaries on every project node."""
    entry_by_node = {}
    for entry in entry_points:
        for node_id in set(entry["members"]) | set(entry["reach"]):
            entry_by_node.setdefault(node_id, set()).add(entry["id"])
        for node_id in entry["touches"]["reads"] + entry["touches"]["writes"] + entry["touches"]["screens"]:
            entry_by_node.setdefault(node_id, set()).add(entry["id"])
    for node_id, node in nodes.items():
        outgoing = [edge for edge in edges if edge["from"] == node_id]
        incoming = [edge for edge in edges if edge["to"] == node_id]
        node["used_by"] = sorted(entry_by_node.get(node_id, set()))
        node["fan_in"] = len({edge["from"] for edge in incoming})
        node["fan_out"] = len({edge["to"] for edge in outgoing})
        if node["kind"] == "program":
            ir = next(
                (item.get("program") for item in files.values()
                 if item.get("program", {}).get("id") == node_id),
                {},
            )
            card = {
                "mode": "online" if any(edge["kind"] in {"uses_map", "starts"} for edge in outgoing)
                else "subprogram" if ir.get("linkage", {}).get("is_subprogram") else "batch",
                "lines": ir.get("metrics", {}).get("lines", 0),
                "paragraphs": len(ir.get("paragraphs", [])),
                "conditions": len(ir.get("conditions", [])),
                "sql": len(ir.get("sql", [])),
                "cics": len(ir.get("cics", [])),
                "calls": len(ir.get("calls", [])),
                "params": ir.get("linkage", {}).get("params", []),
                "callers": sorted({
                    edge["from"] for edge in incoming
                    if edge["kind"] in {"calls", "links", "xctl", "runs_program"}
                }),
                "callees": sorted({
                    edge["to"] for edge in outgoing
                    if edge["kind"] in {"calls", "links", "xctl"}
                }),
                "copybooks": sorted({edge["to"] for edge in outgoing if edge["kind"] == "copies"}),
                "stores_read": sorted({edge["to"] for edge in outgoing if edge["kind"] == "reads"}),
                "stores_written": sorted({edge["to"] for edge in outgoing if edge["kind"] == "writes"}),
                "screens": sorted({edge["to"] for edge in outgoing if edge["kind"] == "uses_map"}),
                "queues_named": sorted({
                    edge["to"] for edge in outgoing
                    if edge["to"].startswith("q:") and edge["kind"] in {"reads", "writes"}
                }),
                "private_queues": node.get("card", {}).get("private_queues", 0),
                "error_checks": dict(Counter(
                    event.get("what", "unknown")
                    for paragraph in ir.get("paragraphs", [])
                    for event in paragraph.get("events", [])
                    if event.get("kind") == "error_check"
                )),
                "header_comment": ir.get("header_comment"),
                "mode_hint": None,
            }
            node["card"] = card
        elif node["kind"] == "copybook":
            ir = next(
                (item.get("copybook") for item in files.values()
                 if item.get("copybook", {}).get("id") == node_id),
                {},
            )
            sections = sorted({
                ref.get("section")
                for edge in incoming if edge["kind"] == "copies"
                for ref in edge["refs"] if ref.get("section")
            })
            node["card"] = {
                "used_by": sorted({edge["from"] for edge in incoming}),
                "sections": sections,
                "items": len(ir.get("data_items", [])),
                "declares_table": ir.get("declares_table"),
            }
        elif node["kind"] in {"jcl_job", "jcl_proc"}:
            ir = next(
                (item.get("jcl") for item in files.values()
                 if item.get("jcl", {}).get("id") == node_id),
                {},
            )
            node["card"] = {
                "steps": [step.get("name") for step in ir.get("steps", [])],
                "runs": sorted({
                    edge["to"] for edge in outgoing
                    if edge["kind"] in {"runs_program", "runs_proc"}
                }),
                "includes": sorted({edge["to"] for edge in outgoing if edge["kind"] == "includes"}),
            }
        elif node["kind"] == "bms_map":
            ir = next(
                (item.get("bms") for item in files.values()
                 if item.get("bms", {}).get("id") == node_id),
                {},
            )
            node["card"] = {
                "mapset": ir.get("mapset"),
                "maps": [item.get("name") for item in ir.get("maps", [])],
                "fields": ir.get("field_count", 0),
                "used_by": sorted({edge["from"] for edge in incoming if edge["kind"] == "uses_map"}),
            }
        elif node["kind"] in DATA_KINDS:
            disp_seen = sorted({
                ref.get("disp")
                for edge in incoming
                for ref in edge["refs"]
                if ref.get("disp")
            })
            node["card"] = {
                "readers": sorted({edge["from"] for edge in incoming if edge["kind"] == "reads"}),
                "writers": sorted({edge["from"] for edge in incoming if edge["kind"] == "writes"}),
                "disp_seen": disp_seen,
                "temporary": node.get("temporary", False),
            }
            if node["kind"] == "table":
                node["card"]["layout_copybook"] = node.get("layout_copybook")


def build_profile(nodes, files, entry_points):
    """Summarize project size and complexity."""
    by_type = Counter(ir.get("type", "unknown") for ir in files.values())
    counts = Counter(
        node["kind"] for node in nodes.values() if node["status"] == "defined"
    )
    data_counts = Counter(
        node["kind"] for node in nodes.values()
        if node["kind"] in DATA_KINDS
    )
    programs = sorted(
        (node for node in nodes.values() if node["kind"] == "program" and node["status"] == "defined"),
        key=lambda node: (-node["card"].get("lines", 0), node["id"]),
    )
    return {
        "files": len(files),
        "by_type": dict(sorted(by_type.items())),
        "total_lines": sum(ir.get("lines", 0) for ir in files.values()),
        "programs": counts["program"],
        "copybooks": counts["copybook"],
        "jobs": counts["jcl_job"],
        "procs": counts["jcl_proc"],
        "maps": counts["bms_map"],
        "tables": data_counts["table"],
        "datasets": data_counts["dataset"],
        "queues": data_counts["queue"],
        "entry_points": len(entry_points),
        "technology": {
            "jcl": any(ir.get("jcl") for ir in files.values()),
            "cics": any(ir.get("program", {}).get("cics") for ir in files.values()),
            "db2": any(ir.get("program", {}).get("sql") for ir in files.values()),
        },
        "largest_programs": [
            {"id": node["id"], "lines": node["card"].get("lines", 0),
             "paragraphs": node["card"].get("paragraphs", 0),
             "conditions": node["card"].get("conditions", 0)}
            for node in programs[:10]
        ],
        "most_complex": [
            {"id": node["id"], "lines": node["card"].get("lines", 0),
             "paragraphs": node["card"].get("paragraphs", 0),
             "conditions": node["card"].get("conditions", 0)}
            for node in sorted(
                programs,
                key=lambda node: (-node["card"].get("conditions", 0), node["id"]),
            )[:10]
        ],
    }


def build_data_view(nodes, edges, files):
    """Build the data-store inventory and per-program CRUD matrix."""
    data_stores = []
    crud_matrix = {}
    for node_id, node in sorted(nodes.items()):
        if node["kind"] not in DATA_KINDS:
            continue
        incoming = [edge for edge in edges if edge["to"] == node_id]
        producers = sorted({edge["from"] for edge in incoming if edge["kind"] == "writes"})
        consumers = sorted({edge["from"] for edge in incoming if edge["kind"] == "reads"})
        layout = None
        for edge in incoming:
            if edge.get("via") != "dd_join":
                continue
            program = next(
                (ir.get("program") for ir in files.values()
                 if ir.get("program", {}).get("id") == edge["from"]),
                None,
            )
            if not program:
                continue
            ref_ddname = next(
                (ref.get("ddname") for ref in edge["refs"] if ref.get("ddname")),
                None,
            )
            file_info = next(
                (item for item in program.get("files", [])
                 if item.get("ddname", "").upper() == (ref_ddname or "").upper()
                 and item.get("record")),
                None,
            )
            if file_info:
                layout = {"program": edge["from"], "record": file_info["record"]}
                break
        data_stores.append({
            "id": node_id,
            "kind": node["kind"],
            "name": node["name"],
            "status": node["status"],
            "defined_in": node["defined_in"],
            "producers": producers,
            "consumers": consumers,
            "layout": layout,
        })
    for node_id, node in sorted(nodes.items()):
        if node["kind"] != "program":
            continue
        accesses = {}
        for edge in edges:
            if edge["from"] != node_id or edge["to"] not in nodes or nodes[edge["to"]]["kind"] not in DATA_KINDS:
                continue
            if edge["kind"] == "reads":
                accesses.setdefault(edge["to"], set()).add("read")
            elif edge["kind"] == "writes":
                accesses.setdefault(edge["to"], set()).add("write")
        if accesses:
            crud_matrix[node_id] = {
                store: "RW" if modes == {"read", "write"} else "R" if "read" in modes else "W"
                for store, modes in sorted(accesses.items())
            }
    return data_stores, crud_matrix


def build_interfaces(nodes, edges, files):
    """Build callable interface definitions with caller references."""
    result = []
    for node_id, node in sorted(nodes.items()):
        if node["kind"] != "program" or node["status"] != "defined":
            continue
        callers = []
        for edge in edges:
            if edge["to"] != node_id or edge["kind"] not in {"calls", "links", "xctl"}:
                continue
            for ref in edge["refs"]:
                callers.append({
                    "node": edge["from"],
                    "kind": edge["kind"],
                    "file": ref["file"],
                    "line": ref["line"],
                    "args": ref.get("args"),
                    "commarea": ref.get("commarea"),
                })
        if not callers:
            continue
        program = next(
            (ir["program"] for ir in files.values()
             if ir.get("program", {}).get("id") == node_id),
            {},
        )
        result.append({
            "program": node_id,
            "params": program.get("linkage", {}).get("params", []),
            "is_subprogram": program.get("linkage", {}).get("is_subprogram", False),
            "callers": sorted(callers, key=lambda caller: (caller["file"], caller["line"], caller["node"])),
        })
    return result


def build_screens(nodes, edges):
    """List BMS maps and their consuming programs."""
    return [
        {
            "id": node_id,
            "mapset": node.get("card", {}).get("mapset"),
            "maps": node.get("card", {}).get("maps", []),
            "fields": node.get("card", {}).get("fields", 0),
            "used_by": node.get("card", {}).get("used_by", []),
        }
        for node_id, node in sorted(nodes.items())
        if node["kind"] == "bms_map"
    ]


def build_catalogs(nodes, files, entry_points):
    """Build display, job-step, and error-handling catalogs."""
    messages = []
    job_steps = []
    error_handling = []
    for path, ir in sorted(files.items()):
        program = ir.get("program")
        if program:
            for paragraph in program.get("paragraphs", []):
                for event in paragraph.get("events", []):
                    if event.get("kind") == "display":
                        messages.append({
                            "program": program["id"],
                            "paragraph": paragraph.get("name"),
                            "line": event.get("line"),
                            "text": event.get("text"),
                        })
            error_handling.append({
                "program": program["id"],
                "counts": dict(Counter(
                    event.get("what", "unknown")
                    for para in program.get("paragraphs", [])
                    for event in para.get("events", [])
                    if event.get("kind") == "error_check"
                )),
            })
        jcl = ir.get("jcl")
        if jcl:
            for step in jcl.get("steps", []):
                job_steps.append({
                    "job": jcl["id"],
                    "order": step.get("order"),
                    "step": step.get("name"),
                    "target": step.get("target"),
                    "status": next(
                        (
                            node["status"] for node in nodes.values()
                            if node["name"] == (step.get("target") or "").upper()
                            and node["kind"] == (
                                "program" if step.get("exec_kind") == "pgm" else "jcl_proc"
                            )
                        ),
                        None,
                    ),
                    "parm": step.get("parm"),
                })
    return {
        "messages": sorted(messages, key=lambda item: (item["program"], item["line"])),
        "job_steps": sorted(job_steps, key=lambda item: (item["job"], item["order"])),
        "error_handling": sorted(error_handling, key=lambda item: item["program"]),
    }


def build_gaps(nodes, edges, entry_points, order):
    """Report gaps and the entry points and conversion units they affect."""
    units = {
        member: unit
        for wave in order.get("waves", [])
        for unit in wave["units"]
        for member in unit["members"]
    }
    reverse_dependencies = {}
    for wave in order.get("waves", []):
        for unit in wave["units"]:
            for dependency in unit["depends_on"]:
                reverse_dependencies.setdefault(dependency, set()).add(unit["id"])
    result = []
    for node_id, node in sorted(nodes.items()):
        if node["status"] != "gap":
            continue
        references = []
        sources = set()
        for edge in edges:
            if edge["to"] != node_id:
                continue
            sources.add(edge["from"])
            for ref in edge["refs"]:
                references.append({"node": edge["from"], "file": ref["file"], "line": ref["line"]})
        affected_units = set()
        for source in sources:
            unit = units.get(source)
            if unit:
                affected_units.add(unit["id"])
        pending = list(affected_units)
        while pending:
            unit_id = pending.pop()
            for dependent in reverse_dependencies.get(unit_id, set()):
                if dependent not in affected_units:
                    affected_units.add(dependent)
                    pending.append(dependent)
        blocking_entries = [
            entry["id"] for entry in entry_points
            if sources.intersection(set(entry["members"]) | set(entry["reach"]))
        ]
        result.append({
            "id": node_id,
            "kind": node["kind"],
            "name": node["name"],
            "referenced_by": sorted(
                references, key=lambda ref: (ref["file"], ref["line"], ref["node"])
            )[:10],
            "blocks_entry_points": sorted(blocking_entries),
            "blocks_units": sorted(affected_units),
        })
    return result


def build_coupling(entry_points, nodes):
    """Find pairs of entry points that share code or data stores."""
    coupling = []
    for index, first in enumerate(sorted(entry_points, key=lambda item: item["id"])):
        first_reach = set(first["reach"])
        first_reads = set(first["touches"]["reads"])
        first_writes = set(first["touches"]["writes"])
        for second in sorted(entry_points, key=lambda item: item["id"])[index + 1:]:
            second_reach = set(second["reach"])
            second_reads = set(second["touches"]["reads"])
            second_writes = set(second["touches"]["writes"])
            shared = first_reach & second_reach
            shared_code = sorted(
                node_id for node_id in shared
                if nodes.get(node_id, {}).get("kind") in {"program", "jcl_proc", "bms_map"}
            )
            shared_copybooks = sorted(
                node_id for node_id in shared
                if nodes.get(node_id, {}).get("kind") == "copybook"
            )
            shared_reads = sorted(first_reads & second_reads)
            shared_writes = sorted(first_writes & second_writes)
            a_to_b = sorted(first_writes & second_reads)
            b_to_a = sorted(second_writes & first_reads)
            if not any((shared_code, shared_copybooks, shared_reads, shared_writes, a_to_b, b_to_a)):
                continue
            coupling.append({
                "a": first["id"],
                "b": second["id"],
                "shared_code": shared_code,
                "shared_copybooks": shared_copybooks,
                "shared_reads": shared_reads,
                "shared_writes": shared_writes,
                "a_to_b": a_to_b,
                "b_to_a": b_to_a,
                "merge_candidate": bool(shared_writes),
            })
    return coupling
