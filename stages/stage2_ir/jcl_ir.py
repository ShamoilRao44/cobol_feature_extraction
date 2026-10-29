import re

from stages.stage1_inventory.models import FileContent

JCL_LINE = re.compile(r"^//(\S*)\s+(\S+)\s*(.*)$")
JCL_OPERATIONS = {
    "EXEC", "DD", "JOB", "PROC", "PEND", "INCLUDE", "SET", "IF", "ELSE",
    "ENDIF", "OUTPUT",
}
PGM = re.compile(r"\bPGM=([A-Z0-9#@$]+)", re.IGNORECASE)
PROC_TARGET = re.compile(r"^(?:PROC=)?([A-Z0-9#@$]+)", re.IGNORECASE)
PARM = re.compile(r"\bPARM=('[^']*'|[^,\s]+)", re.IGNORECASE)
COND = re.compile(r"\bCOND=(\([^)]*\)|[^,\s]+)", re.IGNORECASE)
DSN = re.compile(r"\bDSN(?:AME)?=([^,\s]+)", re.IGNORECASE)
DISP = re.compile(r"\bDISP=(\([^)]*\)|[^,\s]+)", re.IGNORECASE)
INCLUDE_MEMBER = re.compile(r"\bMEMBER=([A-Z0-9#@$]+)", re.IGNORECASE)
DUMMY = re.compile(r"\bDUMMY\b", re.IGNORECASE)


def build_jcl_ir(
    content: FileContent,
    rel_path: str,
    declared_names: list[str],
) -> tuple[dict, list[dict]]:
    """Build JCL job or procedure IR data."""
    statements = _parse_statements(content.code_lines)
    jobs = [statement for statement in statements if statement["op"].upper() == "JOB"]
    procs = [statement for statement in statements if statement["op"].upper() == "PROC"]
    execs = [statement for statement in statements if statement["op"].upper() == "EXEC"]
    kind = "job" if jobs else "proc"
    main_statement = jobs[0] if jobs else procs[0] if procs else None
    name = (
        main_statement["name"]
        if main_statement and main_statement["name"]
        else declared_names[0] if declared_names else ""
    )

    steps = []
    current_step = None
    previous_ddname = ""
    for statement in statements:
        operation = statement["op"].upper()
        if operation == "EXEC":
            current_step = _make_step(statement, len(steps) + 1)
            steps.append(current_step)
            previous_ddname = ""
        elif operation == "PEND":
            current_step = None
        elif operation == "DD" and current_step is not None:
            dd = _make_dd(statement, previous_ddname)
            if dd["ddname"]:
                previous_ddname = dd["ddname"]
            else:
                previous_ddname = dd["ddname"]
            current_step["dds"].append(dd)
            current_step["line_span"][1] = statement["line"]
        elif current_step is not None:
            current_step["line_span"][1] = statement["last_line"]

    includes = []
    for statement in statements:
        if statement["op"].upper() != "INCLUDE":
            continue
        match = INCLUDE_MEMBER.search(statement["operands"])
        if match:
            includes.append(
                {"member": match.group(1).upper(), "line": statement["line"]}
            )

    if jobs:
        first_line = min(statement["line"] for statement in statements)
        last_line = max(statement["line"] for statement in statements)
        result = {
            "kind": "job",
            "id": f"job:{name}",
            "name": name,
            "line_span": [first_line, last_line],
            "steps": steps,
            "includes": includes,
        }
    else:
        first_line = min(statement["line"] for statement in statements) if statements else 0
        last_line = max(statement["line"] for statement in statements) if statements else 0
        result = {
            "kind": "proc",
            "id": f"proc:{name}",
            "name": name,
            "line_span": [first_line, last_line],
            "steps": steps,
            "includes": includes,
        }

    if not jobs and not procs and not execs:
        return result, [
            {
                "start": 1,
                "end": len(content.raw_lines),
                "reason": "no JCL statements",
            }
        ]
    return result, []


def _parse_statements(code_lines: list[tuple[int, str]]) -> list[dict]:
    """Parse JCL control statements and continuations."""
    statements = []
    for line_number, text in code_lines:
        if not text.startswith("//"):
            continue
        match = JCL_LINE.match(text)
        if not match:
            continue
        name, operation, operands = match.groups()
        if not name and operation.upper() not in JCL_OPERATIONS and statements:
            statements[-1]["operands"] += operation + operands
            statements[-1]["last_line"] = line_number
            continue
        statements.append(
            {
                "name": name.upper(),
                "op": operation.upper(),
                "operands": operands.strip(),
                "line": line_number,
                "last_line": line_number,
            }
        )
    return statements


def _make_step(statement: dict, order: int) -> dict:
    """Create a JCL step from its EXEC statement."""
    operands = statement["operands"]
    program_match = PGM.search(operands)
    if program_match:
        exec_kind = "pgm"
        target = program_match.group(1).upper()
    else:
        exec_kind = "proc"
        target_match = PROC_TARGET.match(operands)
        target = target_match.group(1).upper() if target_match else None
    parm_match = PARM.search(operands)
    parm = parm_match.group(1).strip("'") if parm_match else None
    cond_match = COND.search(operands)
    return {
        "name": statement["name"] or f"STEP{order}",
        "order": order,
        "line_span": [statement["line"], statement["line"]],
        "exec_kind": exec_kind,
        "target": target,
        "parm": parm,
        "cond": cond_match.group(1) if cond_match else None,
        "dds": [],
    }


def _make_dd(statement: dict, previous_ddname: str) -> dict:
    """Interpret a JCL DD statement's data set and access mode."""
    ddname = statement["name"]
    operands = statement["operands"]
    dsn_match = DSN.search(operands)
    dsn = dsn_match.group(1) if dsn_match else None
    disp_match = DISP.search(operands)
    disp = disp_match.group(1) if disp_match else None
    if disp:
        disp = disp.strip("()").replace(" ", "")
    parts = disp.split(",") if disp else []

    if operands.upper().startswith("SYSOUT="):
        kind, access = "sysout", "write"
    elif DUMMY.search(operands):
        kind, access = "dummy", None
    elif operands.startswith("*") or operands.upper().startswith("DATA"):
        kind, access = "inline", "read"
    elif not ddname:
        kind, access = "concat", "read"
        ddname = previous_ddname
        if parts:
            _, access = _disp_kind_access(parts)
    elif not dsn:
        kind, access = "other", None
    elif len(parts) > 1 and parts[1].upper() == "DELETE":
        kind, access = "delete", "write"
    else:
        kind, access = _disp_kind_access(parts)

    return {
        "ddname": ddname,
        "dsn": dsn,
        "disp": disp,
        "kind": kind,
        "access": access,
        "inferred": True,
        "line": statement["line"],
    }


def _disp_kind_access(parts: list[str]) -> tuple[str, str]:
    """Map DISP's first value to its data set kind and access."""
    value = parts[0].upper() if parts else "NEW"
    if value == "NEW":
        return "new", "write"
    if value == "MOD":
        return "output", "write"
    if value == "SHR":
        return "input", "read"
    if value == "OLD":
        return "input", "unknown"
    return "other", "unknown"
