def prog(
    path,
    name,
    copybooks=None,
    sql=None,
    cics=None,
    calls=None,
    files=None,
    params=None,
    lines=100,
    conditions=0,
    events=None,
    subprogram=False,
):
    """Create a minimal COBOL program IR fixture."""
    paragraphs = []
    for event in events or []:
        paragraph = event.get("paragraph", "MAIN")
        existing = next((item for item in paragraphs if item["name"] == paragraph), None)
        if existing is None:
            existing = {"name": paragraph, "events": []}
            paragraphs.append(existing)
        existing["events"].append(event)
    body = {
        "id": f"pgm:{name}",
        "name": name,
        "line_span": [1, lines],
        "header_comment": None,
        "metrics": {
            "lines": lines,
            "paragraphs": len(paragraphs),
            "conditions": conditions,
            "sql": len(sql or []),
            "cics": len(cics or []),
            "calls": len(calls or []),
        },
        "files": files or [],
        "copybooks": copybooks or [],
        "data_items": [],
        "linkage": {"is_subprogram": subprogram, "params": params or []},
        "sql": sql or [],
        "cics": cics or [],
        "calls": calls or [],
        "conditions": [],
        "issues": [],
        "paragraphs": paragraphs,
    }
    return path, {
        "path": path,
        "type": "cobol_program",
        "lines": lines,
        "parse_status": "complete",
        "unparsed_ranges": [],
        "program": body,
    }


def job(path, name, steps=None):
    """Create a minimal JCL job IR fixture."""
    parsed_steps = []
    for order, step in enumerate(steps or [], start=1):
        step_name, exec_kind, target, dds = step
        parsed_steps.append({
            "name": step_name,
            "order": order,
            "line_span": [order * 10, order * 10],
            "exec_kind": exec_kind,
            "target": target,
            "parm": None,
            "dds": [
                {
                    "ddname": ddname,
                    "dsn": dsn,
                    "kind": kind,
                    "access": access,
                    "disp": disp,
                    "line": order * 10 + index,
                }
                for index, (ddname, dsn, kind, access, *rest) in enumerate(dds, start=1)
                for disp in [rest[0] if rest else None]
            ],
        })
    return path, {
        "path": path,
        "type": "jcl",
        "lines": len(parsed_steps) * 10,
        "parse_status": "complete",
        "jcl": {
            "id": f"job:{name}",
            "kind": "job",
            "name": name,
            "line_span": [1, max(1, len(parsed_steps) * 10)],
            "steps": parsed_steps,
            "includes": [],
        },
    }


def cpy(path, name, declares_table=None, copies=None):
    """Create a minimal copybook IR fixture."""
    return path, {
        "path": path,
        "type": "copybook",
        "lines": 10,
        "parse_status": "complete",
        "copybook": {
            "id": f"cpy:{name}",
            "name": name,
            "copies": copies or [],
            "data_items": [],
            "declares_table": declares_table,
        },
    }


def bms(path, mapset, maps=None):
    """Create a minimal BMS IR fixture."""
    return path, {
        "path": path,
        "type": "bms_map",
        "lines": 10,
        "parse_status": "complete",
        "bms": {
            "id": f"map:{mapset}",
            "mapset": mapset,
            "maps": maps or [],
            "field_count": sum(item.get("fields", 0) for item in maps or []),
        },
    }
