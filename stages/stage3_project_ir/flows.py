from collections import deque

CODE = {"copies", "includes", "calls", "links", "xctl", "runs_program", "runs_proc", "uses_map"}
CONTROL = {"calls", "links", "xctl", "runs_program"}
ORDER = ["copies", "includes", "calls", "links", "xctl", "runs_program", "runs_proc",
         "uses_map", "reads", "writes"]


def _components(vertices, adjacency):
    """Find strongly connected components without recursion."""
    sequence = 0
    indexes = {}
    lowlinks = {}
    active = []
    on_active = set()
    components = []
    for root in sorted(vertices):
        if root in indexes:
            continue
        indexes[root] = sequence
        lowlinks[root] = sequence
        sequence += 1
        active.append(root)
        on_active.add(root)
        frames = [(root, iter(adjacency.get(root, [])))]
        while frames:
            node, children = frames[-1]
            child = next(children, None)
            if child is not None:
                if child not in indexes:
                    indexes[child] = sequence
                    lowlinks[child] = sequence
                    sequence += 1
                    active.append(child)
                    on_active.add(child)
                    frames.append((child, iter(adjacency.get(child, []))))
                elif child in on_active:
                    lowlinks[node] = min(lowlinks[node], indexes[child])
                continue
            frames.pop()
            if frames:
                parent = frames[-1][0]
                lowlinks[parent] = min(lowlinks[parent], lowlinks[node])
            if lowlinks[node] == indexes[node]:
                component = []
                while active:
                    member = active.pop()
                    on_active.remove(member)
                    component.append(member)
                    if member == node:
                        break
                components.append(sorted(component))
    return components


def _outgoing(edges, source, kinds=None):
    """Return edges from one source filtered by kind."""
    return [edge for edge in edges if edge["from"] == source and (
        kinds is None or edge["kind"] in kinds
    )]


def _reachable(members, edges):
    """Find nodes reachable through code relationships."""
    queue = deque(sorted(members))
    visited = set(members)
    while queue:
        source = queue.popleft()
        for edge in _outgoing(edges, source, CODE):
            target = edge["to"]
            if target not in visited:
                visited.add(target)
                queue.append(target)
    return sorted(visited - set(members))


def _touches(members, reach, edges):
    """Summarize data and screen targets reached by an entry point."""
    sources = set(members) | set(reach)
    reads = set()
    writes = set()
    screens = set()
    for edge in edges:
        if edge["from"] not in sources:
            continue
        if edge.get("context") not in {None, *reach, *members}:
            continue
        if edge["kind"] == "reads":
            reads.add(edge["to"])
        elif edge["kind"] == "writes":
            writes.add(edge["to"])
        elif edge["kind"] == "uses_map":
            screens.add(edge["to"])
    queues = {node for node in reads | writes if node.startswith("q:")}
    return {
        "reads": sorted(reads),
        "writes": sorted(writes),
        "screens": sorted(screens),
        "queues": sorted(queues),
        "external": sorted(
            node_id for node_id in reach
            if any(edge["to"] == node_id and edge["status"] in {"system", "gap", "dynamic"}
                   for edge in edges)
        ),
    }


def _program_steps(members, edges):
    """Create ordered call-flow steps for program entry points."""
    results = []
    queue = deque((member, "start", None, 0, 0) for member in sorted(members))
    visited = set()
    while queue:
        source, via, parent, line, depth = queue.popleft()
        if source in visited or depth > 10:
            continue
        visited.add(source)
        results.append((source, via, parent, line))
        if depth == 10:
            continue
        next_edges = [
            edge for edge in _outgoing(edges, source, {"calls", "links", "xctl"})
            if edge["to"].startswith("pgm:")
        ]
        next_edges.sort(key=lambda edge: (
            min((ref["line"] for ref in edge["refs"]), default=0), edge["to"]
        ))
        for edge in next_edges:
            line = min((ref["line"] for ref in edge["refs"]), default=0)
            queue.append((edge["to"], edge["kind"], source, line, depth + 1))
    steps = []
    for order, (node_id, via, parent, line) in enumerate(results, start=1):
        maps = sorted({edge["to"] for edge in _outgoing(edges, node_id, {"uses_map"})})
        reads = sorted({edge["to"] for edge in _outgoing(edges, node_id, {"reads"})
                        if edge.get("context") is None})
        writes = sorted({edge["to"] for edge in _outgoing(edges, node_id, {"writes"})
                         if edge.get("context") is None})
        steps.append({
            "order": order,
            "node": node_id,
            "via": via,
            "from": parent,
            "line": line,
            "maps": maps,
            "reads": reads,
            "writes": writes,
        })
    return steps


def _job_steps(node_id, jcl, edges, nodes, files, depth=0, opened=()):
    """Build job steps and bounded procedure expansions."""
    steps = []
    for raw_step in jcl.get("steps", []):
        name = raw_step.get("name")
        target = next(
            (edge["to"] for edge in _outgoing(edges, node_id, {"runs_program", "runs_proc"})
             if edge.get("step") == name),
            None,
        )
        reads = set()
        writes = set()
        for edge in edges:
            if edge.get("context") != node_id or edge.get("step") != name:
                continue
            if edge["kind"] == "reads":
                reads.add(edge["to"])
            elif edge["kind"] == "writes":
                writes.add(edge["to"])
        expanded = []
        if target and target.startswith("proc:") and target not in opened and depth < 3:
            proc_ir = next(
                (candidate.get("jcl") for candidate in files.values()
                 if candidate.get("jcl", {}).get("id") == target),
                None,
            )
            if proc_ir:
                expanded = _job_steps(
                    target, proc_ir, edges, nodes, files, depth + 1, opened + (target,)
                )
        steps.append({
            "order": raw_step.get("order", len(steps) + 1),
            "name": name,
            "node": target,
            "status": nodes[target]["status"] if target in nodes else None,
            "exec_kind": raw_step.get("exec_kind"),
            "parm": raw_step.get("parm"),
            "reads": sorted(reads),
            "writes": sorted(writes),
            "expands": expanded,
        })
    return steps


def build_entry_points(nodes, edges, files):
    """Build batch and root-unit entry points."""
    entries = []
    programs = {
        node_id for node_id, node in nodes.items()
        if node["kind"] == "program" and node["status"] == "defined"
    }
    adjacency = {node_id: set() for node_id in programs}
    for edge in edges:
        if edge["kind"] in {"calls", "links", "xctl"} and edge["from"] in programs and edge["to"] in programs:
            if edge["from"] != edge["to"]:
                adjacency[edge["from"]].add(edge["to"])
    components = _components(programs, {key: sorted(value) for key, value in adjacency.items()})

    for node_id, node in sorted(nodes.items()):
        if node["kind"] != "jcl_job" or node["status"] != "defined":
            continue
        jcl = next(
            (item.get("jcl") for item in files.values()
             if item.get("jcl", {}).get("id") == node_id),
            {},
        )
        line = (jcl.get("line_span") or [0])[0]
        entries.append({
            "id": f"ep:{node_id}",
            "node": node_id,
            "members": [node_id],
            "kind": "jcl_job",
            "name": node["name"],
            "inferred": False,
            "confidence": "high",
            "trigger": {
                "type": "batch", "name": node["name"],
                "source_file": node["defined_in"], "line": line,
            },
            "steps": _job_steps(node_id, jcl, edges, nodes, files),
            "reach": _reachable([node_id], edges),
            "touches": {},
            "metrics": {},
            "summary": None,
        })

    incoming_from = {node_id: set() for node_id in programs}
    for source, targets in adjacency.items():
        for target in targets:
            incoming_from[target].add(source)
    for component in components:
        member_set = set(component)
        inbound_run = any(
            edge["kind"] == "runs_program" and edge["to"] in member_set
            for edge in edges
        )
        if any(source not in member_set for target in component for source in incoming_from[target]) or inbound_run:
            continue
        member_edges = [
            edge for edge in edges
            if edge["from"] in member_set and edge["kind"] in {"uses_map", "starts"}
        ]
        entry_kind = "online" if member_edges else "root_program"
        node_id = component[0]
        program_ir = next(
            (item["program"] for item in files.values()
             if item.get("program", {}).get("id") == node_id),
            {},
        )
        line = (program_ir.get("line_span") or [0])[0]
        started = sorted(
            (edge for edge in member_edges if edge["kind"] == "starts"),
            key=lambda edge: (
                min((ref["line"] for ref in edge["refs"]), default=0), edge["to"]
            ),
        )
        trigger = {
            "type": "user" if entry_kind == "online" else "none",
            "name": next(
                (nodes[edge["to"]]["name"] for edge in started if edge["to"] in nodes),
                None,
            ),
            "source_file": nodes[node_id]["defined_in"],
            "line": line,
        }
        entries.append({
            "id": f"ep:{node_id}",
            "node": node_id,
            "members": component,
            "kind": entry_kind,
            "name": nodes[node_id]["name"],
            "inferred": True,
            "confidence": "high",
            "trigger": trigger,
            "steps": _program_steps(component, edges),
            "reach": _reachable(component, edges),
            "touches": {},
            "metrics": {},
            "summary": None,
        })

    for entry in entries:
        entry["touches"] = _touches(entry["members"], entry["reach"], edges)
        relevant = set(entry["members"]) | set(entry["reach"])
        target_edges = [
            edge for edge in edges if edge["from"] in relevant
        ]
        if any(nodes.get(node, {}).get("status") == "gap" for node in entry["reach"]):
            entry["confidence"] = "low"
        elif any(nodes.get(node, {}).get("status") == "dynamic" for node in entry["reach"]) or any(
            edge.get("via") == "candidates" for edge in target_edges
        ):
            entry["confidence"] = "medium"
        metrics = {"programs": 0, "copybooks": 0, "jobs_and_procs": 0,
                   "lines": 0, "conditions": 0}
        for node_id in relevant:
            node = nodes.get(node_id)
            if not node:
                continue
            key = {
                "program": "programs",
                "copybook": "copybooks",
                "jcl_job": "jobs_and_procs",
                "jcl_proc": "jobs_and_procs",
            }.get(node["kind"])
            if key:
                metrics[key] += 1
            ir = next(
                (item.get("program") or item.get("copybook") or item.get("jcl")
                 for item in files.values()
                 if any(body and body.get("id") == node_id for body in
                        (item.get("program"), item.get("copybook"), item.get("jcl")))),
                {},
            )
            metrics["lines"] += ir.get("metrics", {}).get("lines", 0) or (
                max(0, (ir.get("line_span") or [0, 0])[1] - (ir.get("line_span") or [0, 0])[0] + 1)
            )
            metrics["conditions"] += len(ir.get("conditions", []))
        entry["metrics"] = metrics
    return sorted(entries, key=lambda entry: entry["id"])


def build_conversion_order(nodes, edges, entry_points):
    """Build cycles and least-dependent-first conversion units."""
    convertible = {
        node_id for node_id, node in nodes.items()
        if node["status"] == "defined" or node["kind"] in {
            "table", "dataset", "queue", "cics_file"
        }
    }
    excluded = [
        {"node": node_id, "status": node["status"]}
        for node_id, node in sorted(nodes.items())
        if node_id not in convertible
    ]
    adjacency = {node_id: set() for node_id in convertible}
    edge_kinds = {}
    for edge in edges:
        if edge["kind"] not in ORDER or edge["from"] not in convertible or edge["to"] not in convertible:
            continue
        if edge["from"] == edge["to"]:
            continue
        adjacency[edge["from"]].add(edge["to"])
        edge_kinds[(edge["from"], edge["to"])] = edge["kind"]
    components = _components(convertible, {key: sorted(value) for key, value in adjacency.items()})
    components.sort(key=lambda members: members[0])
    comp_for = {member: index for index, comp in enumerate(components) for member in comp}
    dependencies = {index: set() for index in range(len(components))}
    for source, targets in adjacency.items():
        for target in targets:
            left = comp_for[source]
            right = comp_for[target]
            if left != right:
                dependencies[left].add(right)
    pending = set(range(len(components)))
    waves = {}
    while pending:
        ready = sorted(
            index for index in pending
            if dependencies[index].issubset(waves)
        )
        if not ready:
            break
        for index in ready:
            waves[index] = 0 if not dependencies[index] else 1 + max(
                waves[dependency] for dependency in dependencies[index]
            )
            pending.remove(index)
    ordered_components = sorted(
        range(len(components)),
        key=lambda index: (waves.get(index, 0), components[index][0]),
    )
    unit_ids = {index: f"u:{number}" for number, index in enumerate(ordered_components, 1)}
    cycles = []
    for cycle_number, index in enumerate(
        sorted(
            (i for i, members in enumerate(components) if len(members) > 1),
            key=lambda i: components[i][0],
        ),
        1,
    ):
        via = sorted({
            edge["kind"] for edge in edges
            if edge["from"] in components[index] and edge["to"] in components[index]
        })
        cycles.append({
            "id": f"cyc:{cycle_number}",
            "members": components[index],
            "via": via,
        })
    units_by_wave = {}
    for index in ordered_components:
        members = components[index]
        notes = []
        for member in members:
            node = nodes[member]
            if node["kind"] in {"table", "dataset", "queue", "cics_file"}:
                notes.append("no source for data store")
            missing = sorted({
                edge["to"] for edge in edges
                if edge["from"] == member and edge["to"] in nodes
                and nodes[edge["to"]]["status"] == "gap"
            })
            dynamic = sorted({
                edge["to"] for edge in edges
                if edge["from"] == member and edge["to"] in nodes
                and nodes[edge["to"]]["status"] == "dynamic"
            })
            if missing:
                notes.append("references gap " + ", ".join(missing[:5]))
            if dynamic:
                notes.append("references dynamic " + ", ".join(dynamic[:5]))
        unit = {
            "id": unit_ids[index],
            "kind": "cycle" if len(members) > 1 else "single",
            "members": members,
            "depends_on": sorted(unit_ids[dependency] for dependency in dependencies[index]),
            "lines": sum(nodes[member].get("card", {}).get("lines", 0) for member in members),
            "conditions": sum(nodes[member].get("card", {}).get("conditions", 0) for member in members),
            "notes": sorted(set(notes)),
        }
        units_by_wave.setdefault(waves.get(index, 0), []).append(unit)
    referenced_missing = any(
        edge["from"] in convertible and nodes.get(edge["to"], {}).get("status") in {"gap", "dynamic"}
        for edge in edges
    )
    gap_count = sum(
        edge["count"] for edge in edges
        if nodes.get(edge["to"], {}).get("status") == "gap"
    )
    dynamic_count = sum(
        edge["count"] for edge in edges
        if nodes.get(edge["to"], {}).get("status") == "dynamic"
    )
    caveats = []
    if gap_count:
        caveats.append(f"{gap_count} references to missing source")
    if dynamic_count:
        caveats.append(f"{dynamic_count} dynamic references")
    return cycles, {
        "basis": ORDER,
        "waves": [
            {"wave": wave, "units": units_by_wave[wave]}
            for wave in sorted(units_by_wave)
        ],
        "excluded": excluded,
        "complete": not referenced_missing,
        "caveats": caveats,
    }
