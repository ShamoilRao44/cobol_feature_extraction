from collections import Counter


def build_quality(nodes, edges, files, dynamic_refs, order, extra_caveats):
    """Summarize parser coverage and reference certainty."""
    by_type = Counter(ir.get("type", "unknown") for ir in files.values())
    nodes_by_kind = Counter(node["kind"] for node in nodes.values())
    nodes_by_status = Counter(node["status"] for node in nodes.values())
    edges_by_status = Counter(edge["status"] for edge in edges)
    partial = []
    issues = []
    for path, ir in sorted(files.items()):
        if ir.get("parse_status") == "partial":
            ranges = ir.get("unparsed_ranges", [])
            partial.append({
                "path": path,
                "parse_status": "partial",
                "reason": ranges[0].get("reason") if ranges else None,
            })
        for issue in ir.get("program", {}).get("issues", []):
            issues.append({"file": path, **issue})
    total_edges = len(edges)
    resolved = sum(
        count for status, count in edges_by_status.items()
        if status in {"resolved", "system", "external"}
    )
    caveats = []
    if partial:
        caveats.append(f"{len(partial)} files could not be fully parsed")
    gaps = sum(
        edge["count"] for edge in edges
        if nodes.get(edge["to"], {}).get("status") == "gap"
    )
    if gaps:
        caveats.append(f"{gaps} references to missing source (gaps)")
    if dynamic_refs:
        caveats.append(f"{len(dynamic_refs)} dynamic references")
    sql_unparsed = sum(
        1 for ir in files.values()
        if ir.get("type") == "sql" and not any(
            ir.get(body) for body in ("program", "jcl", "copybook", "bms")
        )
    )
    if sql_unparsed:
        caveats.append(f"{sql_unparsed} SQL/DDL files are not parsed")
    if not any(ir.get("jcl") for ir in files.values()) and any(
        ir.get("program", {}).get("files") for ir in files.values()
    ):
        caveats.append("No JCL found: dataset joins skipped")
    duplicates = [item for item in extra_caveats if item.startswith("Duplicate ids:")]
    caveats.extend(duplicates)
    caveats.extend(item for item in extra_caveats if item not in duplicates)
    authoritative = not (
        any(node["status"] in {"gap", "dynamic"} for node in nodes.values())
        or dynamic_refs
        or partial
    )
    return {
        "counts": {
            "files": len(files),
            "by_type": dict(sorted(by_type.items())),
            "nodes_by_kind": dict(sorted(nodes_by_kind.items())),
            "nodes_by_status": dict(sorted(nodes_by_status.items())),
            "edges_by_status": dict(sorted(edges_by_status.items())),
        },
        "resolved_ratio": resolved / total_edges if total_edges else 1.0,
        "unparsed_files": partial,
        "issues": sorted(issues, key=lambda item: (item["file"], item["line"])),
        "dynamic_refs": dynamic_refs,
        "caveats": caveats,
        "authoritative": authoritative,
    }
