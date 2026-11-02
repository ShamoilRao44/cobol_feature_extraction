import os

from stages.stage1_inventory.linker import SYSTEM_NAMES, SYSTEM_PREFIXES

CONTROL_KINDS = {"copies", "includes", "calls", "links", "xctl", "runs_program", "runs_proc", "uses_map"}


def _node(nodes, node_id, kind, name, status, defined_in=None):
    """Create a node without replacing an existing definition."""
    if node_id not in nodes:
        nodes[node_id] = {
            "id": node_id,
            "kind": kind,
            "name": name,
            "defined_in": defined_in,
            "status": status,
            "card": {},
        }
    elif status == "defined" and nodes[node_id]["status"] != "defined":
        nodes[node_id].update(
            {"kind": kind, "name": name, "defined_in": defined_in, "status": status}
        )
    return nodes[node_id]


def _status_for(name):
    """Return whether a referenced name is system-provided or missing."""
    return "system" if name in SYSTEM_NAMES or name.startswith(SYSTEM_PREFIXES) else "gap"


def build_nodes(files):
    """Build project nodes, name indexes, and duplicate definitions."""
    nodes = {}
    index = {"program_names": {}, "copybook_names": {}, "proc_names": {}, "map_names": {}}
    definitions = {}
    duplicates = []
    for path in sorted(files):
        ir = files[path]
        for key, kind, prefix in (
            ("program", "program", "pgm:"),
            ("copybook", "copybook", "cpy:"),
            ("jcl", None, None),
            ("bms", "bms_map", "map:"),
        ):
            body = ir.get(key)
            if not body:
                continue
            if key == "jcl":
                kind = "jcl_job" if body.get("kind") == "job" else "jcl_proc"
                prefix = "job:" if kind == "jcl_job" else "proc:"
            node_id = body.get("id") or f"{prefix}{body.get('name', '')}"
            name = body.get("name") or body.get("mapset") or node_id.split(":", 1)[-1]
            name = name.upper()
            body["name"] = name
            if node_id in definitions:
                definitions[node_id].append(path)
                continue
            definitions[node_id] = [path]
            node = _node(nodes, node_id, kind, name, "defined", path)
            if kind == "program":
                index["program_names"].setdefault(name, node_id)
            elif kind == "copybook":
                index["copybook_names"].setdefault(name, node_id)
                if body.get("declares_table"):
                    table = body["declares_table"].upper()
                    _node(nodes, f"tbl:{table}", "table", table, "external")
                    nodes[f"tbl:{table}"]["layout_copybook"] = node_id
            elif kind == "jcl_proc":
                index["proc_names"].setdefault(name, node_id)
            elif kind == "bms_map":
                index["map_names"].setdefault(name, node_id)
                for map_item in body.get("maps", []):
                    index["map_names"].setdefault(map_item["name"].upper(), node_id)
    for node_id, paths in sorted(definitions.items()):
        if len(paths) > 1:
            duplicates.append({"id": node_id, "files": paths[1:]})
    return nodes, index, duplicates


def _resolve(nodes, index, name, target_kind):
    """Resolve a referenced target to a defined, system, or gap node."""
    name = (name or "").upper()
    mapping = {
        "program": ("program_names", "pgm:", "program"),
        "copybook": ("copybook_names", "cpy:", "copybook"),
        "proc": ("proc_names", "proc:", "jcl_proc"),
        "map": ("map_names", "map:", "bms_map"),
    }
    map_key, prefix, node_kind = mapping[target_kind]
    found = index[map_key].get(name)
    if found:
        return found
    status = _status_for(name)
    node_id = f"{prefix}{name}"
    _node(nodes, node_id, node_kind, name, status)
    return node_id


def _condition_for(program, item_id):
    """Find the active condition for a referenced program event."""
    for paragraph in program.get("paragraphs", []):
        for event in paragraph.get("events", []):
            if event.get("ref") == item_id:
                return event.get("under")
    return None


def _ref(file_path, line, paragraph=None, condition=None, **extra):
    """Create a source reference record."""
    result = {
        "file": file_path,
        "line": line,
        "paragraph": paragraph,
        "condition": condition,
    }
    result.update(extra)
    return result


def build_edges(files, nodes, index):
    """Build and aggregate typed project edges."""
    raw = []
    dynamic_refs = []
    info = {"step_targets": {}, "runs": {}, "caveats": [], "private_queues": {}}

    def add_edge(source, target, kind, file_path, line, paragraph=None, condition=None,
                 access=None, inferred=False, via=None, step=None, context=None,
                 variable=None, **ref_fields):
        """Append one unaggregated edge."""
        target_status = nodes[target]["status"]
        status = (
            "external" if kind == "starts" else "resolved"
            if target_status in {"defined", "external", "unmapped"}
            else target_status
        )
        raw.append({
            "from": source,
            "to": target,
            "kind": kind,
            "status": status,
            "access": access,
            "inferred": inferred,
            "via": via,
            "step": step,
            "context": context,
            "variable": variable,
            "ref": _ref(file_path, line, paragraph, condition, **ref_fields),
        })

    for file_path in sorted(files):
        ir = files[file_path]
        program = ir.get("program")
        if not program:
            continue
        source = program["id"]
        name = program["name"]
        for item in program.get("copybooks", []):
            target = _resolve(nodes, index, item.get("name"), "copybook")
            add_edge(source, target, "copies", file_path, item.get("line", 0),
                     section=item.get("section"))
        for item in program.get("sql", []):
            line = item.get("line_span", [0])[0]
            if item.get("kind") == "include" and item.get("include"):
                target = _resolve(nodes, index, item["include"], "copybook")
                add_edge(source, target, "includes", file_path, line,
                         item.get("paragraph"), _condition_for(program, item["id"]))
            elif item.get("dynamic"):
                dynamic_refs.append({
                    "node": source, "kind": "sql", "variable": None, "scope": None,
                    "line": line, "candidates": [], "resolved": False,
                })
            else:
                for table_name in item.get("tables", []):
                    short_name = table_name.rsplit(".", 1)[-1].upper()
                    target = f"tbl:{short_name}"
                    _node(nodes, target, "table", short_name, "external")
                    table_node = nodes[target]
                    qualified = table_node.setdefault("qualified_names", [])
                    if table_name.upper() != short_name and table_name.upper() not in qualified:
                        qualified.append(table_name.upper())
                    edge_kind = "reads" if item.get("access") == "read" else "writes"
                    if item.get("access") in {"read", "write"}:
                        add_edge(source, target, edge_kind, file_path, line,
                                 item.get("paragraph"), _condition_for(program, item["id"]),
                                 access=item["access"])
        for item in program.get("calls", []):
            _program_target(
                item, "call", "calls", source, name, file_path, program, nodes, index,
                add_edge, dynamic_refs, target_field="target", target_kind="program",
                line_field="line", extra={"args": item.get("args", [])},
            )
        for item in program.get("cics", []):
            command = item.get("command", "").upper()
            first = command.split()[0] if command else ""
            line = item.get("line", 0)
            paragraph = item.get("paragraph")
            condition = _condition_for(program, item.get("id"))
            dynamic_item = dict(item)
            dynamic_item["_dynamic_variable"] = _cics_dynamic_variable(item, program)
            if first in {"LINK", "XCTL", "LOAD"}:
                edge_kind = {"LINK": "links", "XCTL": "xctl", "LOAD": "calls"}[first]
                _program_target(
                    dynamic_item, "call" if first == "LOAD" else first.lower(),
                    edge_kind, source, name, file_path, program,
                    nodes, index, add_edge, dynamic_refs, target_field="program",
                    target_kind="program", line_field="line",
                    extra={"commarea": item.get("commarea")},
                )
            elif first == "RETURN" and item.get("transid"):
                transid = item["transid"].upper()
                target = f"tx:{transid}"
                _node(nodes, target, "transaction", transid, "external")
                add_edge(source, target, "starts", file_path, line, paragraph, condition)
            elif command in {"SEND MAP", "RECEIVE MAP"}:
                map_name = item.get("mapset") or item.get("map")
                if map_name:
                    if item.get("dynamic"):
                        _dynamic_target(
                            dynamic_item, "map", "map", source, name, file_path, nodes, index,
                            add_edge, dynamic_refs, line, paragraph, condition,
                            "uses_map",
                        )
                    else:
                        target = _resolve(nodes, index, map_name, "map")
                        add_edge(source, target, "uses_map", file_path, line, paragraph, condition)
            elif first in {"READQ", "WRITEQ", "DELETEQ"} and item.get("queue"):
                if item.get("dynamic"):
                    _dynamic_target(
                        dynamic_item, "queue", "queue", source, name, file_path, nodes, index,
                        add_edge, dynamic_refs, line, paragraph, condition,
                    )
                else:
                    queue = item["queue"].upper()
                    target = f"q:{queue}"
                    _node(nodes, target, "queue", queue, "external")
                    access = "read" if first == "READQ" else "write"
                    edge_kind = "reads" if access == "read" else "writes"
                    add_edge(source, target, edge_kind, file_path, line, paragraph,
                             condition, access=access)
            elif first in {"READ", "STARTBR", "READNEXT", "READPREV", "ENDBR", "RESETBR",
                           "WRITE", "REWRITE", "DELETE", "UNLOCK"} and item.get("file"):
                access = "read" if first in {
                    "READ", "STARTBR", "READNEXT", "READPREV", "ENDBR", "RESETBR"
                } else "write"
                if item.get("dynamic"):
                    _dynamic_target(
                        dynamic_item, "file", "file", source, name, file_path, nodes, index,
                        add_edge, dynamic_refs, line, paragraph, condition,
                        access=access,
                    )
                else:
                    filename = item["file"].upper()
                    target = f"cf:{filename}"
                    _node(nodes, target, "cics_file", filename, "external")
                    add_edge(source, target, "reads" if access == "read" else "writes",
                             file_path, line, paragraph, condition, access=access)

    for file_path in sorted(files):
        ir = files[file_path]
        jcl = ir.get("jcl")
        if not jcl:
            continue
        job_id = jcl["id"]
        for include in jcl.get("includes", []):
            target = _resolve(nodes, index, include.get("member"), "proc")
            add_edge(job_id, target, "includes", file_path, include.get("line", 0))
        for step in jcl.get("steps", []):
            step_name = step.get("name")
            target_name = step.get("target")
            exec_kind = step.get("exec_kind")
            target = _resolve(nodes, index, target_name, "program" if exec_kind == "pgm" else "proc") if target_name else None
            info["step_targets"][(job_id, step_name)] = target
            if target:
                relation = "runs_program" if exec_kind == "pgm" else "runs_proc"
                add_edge(job_id, target, relation, file_path,
                         (step.get("line_span") or [0])[0], step=step_name,
                         parm=step.get("parm"))
                if exec_kind == "pgm" and nodes[target]["status"] == "defined":
                    info["runs"].setdefault(target, []).append((job_id, step_name))

            target_is_program = bool(
                target and exec_kind == "pgm" and nodes[target]["status"] == "defined"
            )
            if target_is_program:
                target_source_path = next(
                    (path for path, candidate in files.items()
                     if candidate.get("program", {}).get("id") == target),
                    file_path,
                )
                target_program = files[target_source_path].get("program")
                if target_program:
                    for file_info in target_program.get("files", []):
                        ddname = file_info.get("ddname")
                        if not ddname:
                            continue
                        dd = next(
                            (item for item in step.get("dds", [])
                             if (item.get("ddname") or "").upper() == ddname.upper()),
                            None,
                        )
                        if not dd:
                            info["caveats"].append(
                                f"ddname {ddname} of {target_program['name']} has no DD in step {step_name} of {job_id}"
                            )
                            continue
                        if not dd.get("dsn"):
                            continue
                        dataset = dd["dsn"].upper()
                        dataset_id = f"ds:{dataset}"
                        _node(nodes, dataset_id, "dataset", dataset, "external")
                        nodes[dataset_id]["temporary"] = dataset.startswith("&&")
                        access = file_info.get("access", "unknown")
                        if access == "read_write":
                            access_pairs = [("read", "read"), ("write", "write")]
                            inferred = False
                        elif access in {"read", "write"}:
                            access_pairs = [(access, access)]
                            inferred = False
                        else:
                            dd_access = dd.get("access")
                            if dd_access in {"read", "write"}:
                                access_pairs = [(dd_access, dd_access)]
                            else:
                                access_pairs = [("read", "unknown")]
                            inferred = True
                        for edge_access, actual_access in access_pairs:
                            add_edge(
                                target_program["id"], dataset_id,
                                "reads" if edge_access == "read" else "writes",
                                target_source_path,
                                (file_info.get("lines") or [dd.get("line", 0)])[0],
                                access=actual_access,
                                inferred=inferred,
                                via="dd_join", step=step_name, context=job_id,
                                ddname=ddname, disp=dd.get("disp"),
                            )
            else:
                for dd in step.get("dds", []):
                    if not dd.get("dsn"):
                        continue
                    dataset = dd["dsn"].upper()
                    dataset_id = f"ds:{dataset}"
                    _node(nodes, dataset_id, "dataset", dataset, "external")
                    nodes[dataset_id]["temporary"] = dataset.startswith("&&")
                    access = dd.get("access")
                    edge_kind = "writes" if access == "write" else "reads"
                    add_edge(job_id, dataset_id, edge_kind, file_path, dd.get("line", 0),
                             access=access if access in {"read", "write"} else "unknown",
                             inferred=True, via="disp", step=step_name,
                             context=job_id, disp=dd.get("disp"))

    for file_path in sorted(files):
        program = files[file_path].get("program")
        if not program or program["id"] in info["runs"]:
            continue
        for file_info in program.get("files", []):
            ddname = file_info.get("ddname")
            if not ddname:
                continue
            target = f"dd:{ddname.upper()}"
            _node(nodes, target, "dataset", ddname.upper(), "unmapped")
            access = file_info.get("access")
            accesses = ("read", "write") if access == "read_write" else (
                (access,) if access in {"read", "write"} else ("read",)
            )
            for actual_access in accesses:
                add_edge(program["id"], target,
                         "reads" if actual_access == "read" else "writes",
                         file_path, (file_info.get("lines") or [0])[0],
                         access=actual_access, inferred=True, via="dd_join")

    for node in nodes.values():
        if "qualified_names" in node:
            node["qualified_names"].sort()
    edges = _aggregate(raw)
    dynamic_refs.sort(key=lambda item: (item["node"], item["line"], item["kind"]))
    return edges, dynamic_refs, info


def _program_target(item, ref_kind, edge_kind, source, program_name, file_path,
                    program, nodes, index, add_edge, dynamic_refs, target_field,
                    target_kind, line_field, extra):
    """Resolve one call-like program reference."""
    target_name = item.get(target_field)
    line = item.get(line_field, 0)
    paragraph = item.get("paragraph")
    condition = _condition_for(program, item.get("id"))
    if item.get("dynamic"):
        _dynamic_target(
            item, ref_kind, target_kind, source, program_name, file_path, nodes,
            index, add_edge, dynamic_refs, line, paragraph, condition, edge_kind,
            **extra,
        )
    elif target_name:
        target = _resolve(nodes, index, target_name, target_kind)
        add_edge(source, target, edge_kind, file_path, line, paragraph, condition,
                 **extra)


def _cics_dynamic_variable(item, program):
    """Find the preferred dynamic option variable from the program's data names."""
    data_names = {entry.get("name") for entry in program.get("data_items", [])}
    for key in ("program", "map", "mapset", "file", "queue"):
        value = item.get(key)
        if value and value in data_names:
            return value
    return None


def _dynamic_target(item, ref_kind, target_kind, source, program_name, file_path,
                    nodes, index, add_edge, dynamic_refs, line, paragraph, condition,
                    edge_kind=None, access=None, **extra):
    """Add candidate edges and record an unresolved dynamic target."""
    variable = item.get("_dynamic_variable") or (
        item.get("target") if ref_kind == "call" else (
        item.get("program") if target_kind == "program" else
        item.get("map") or item.get("mapset") if target_kind == "map" else
        item.get("file") if target_kind == "file" else item.get("queue")
        )
    )
    scope = item.get("queue_scope")
    candidates = item.get("candidates", [])
    if ref_kind == "queue" and scope == "session_private":
        nodes[source].setdefault("card", {}).setdefault("private_queues", 0)
        nodes[source]["card"]["private_queues"] += 1
        return
    dynamic_node = f"dyn:{program_name}.{variable}"
    resolved = bool(candidates)
    if candidates:
        for candidate in candidates:
            value = candidate["value"].upper()
            if target_kind == "queue":
                target = f"q:{value}"
                _node(nodes, target, "queue", value, "external")
            elif target_kind == "file":
                target = f"cf:{value}"
                _node(nodes, target, "cics_file", value, "external")
            else:
                target = _resolve(nodes, index, value, target_kind)
            add_edge(
                source, target, edge_kind or ("calls" if target_kind == "program" else "reads"),
                file_path, line, paragraph, condition, access=access, inferred=True,
                via="candidates", variable=variable, **extra,
            )
    elif ref_kind == "queue" and scope == "unknown":
        pass
    else:
        _node(nodes, dynamic_node, "unknown_target", variable, "dynamic")
        add_edge(
            source, dynamic_node, edge_kind or ("calls" if target_kind == "program" else "reads"),
            file_path, line, paragraph, condition, access=access,
            variable=variable, **extra,
        )
    dynamic_refs.append({
        "node": source,
        "kind": ref_kind,
        "variable": variable,
        "scope": scope,
        "line": line,
        "candidates": [candidate["value"] for candidate in candidates],
        "resolved": resolved,
    })


def _aggregate(raw):
    """Aggregate equivalent edges and sort their source references."""
    grouped = {}
    key_fields = ("from", "to", "kind", "status", "access", "inferred", "via",
                  "step", "context", "variable")
    for edge in raw:
        key = tuple(edge[field] for field in key_fields)
        group = grouped.setdefault(key, {field: edge[field] for field in key_fields}
                                   | {"count": 0, "refs": []})
        group["count"] += 1
        group["refs"].append(edge["ref"])
    result = []
    ordered = sorted(
        grouped.items(),
        key=lambda item: tuple("" if value is None else str(value) for value in item[0]),
    )
    for _, edge in ordered:
        edge["refs"].sort(key=lambda ref: (ref["file"], ref["line"]))
        edge["refs"] = edge["refs"][:10]
        result.append(edge)
    return result
