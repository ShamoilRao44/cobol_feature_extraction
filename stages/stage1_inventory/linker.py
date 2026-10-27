SYSTEM_NAMES = {
    "SQLCA", "SQLDA", "DFHAID", "DFHBMSCA", "DFHEIBLK", "IEFBR14", "IEBGENER",
    "IEBCOPY", "IEBCOMPR", "IEBUPDTE", "IDCAMS", "SORT", "ICEMAN", "ICETOOL",
    "IKJEFT01", "IKJEFT1B", "DSNTEP2", "DSNTEP4", "DSNUTILB", "DSNTIAUL",
    "IGYCRCTL", "IEWL", "IEWBLINK", "ADRDSSU",
}
SYSTEM_PREFIXES = ("DFH", "CEE", "IEB", "IEF", "IEW", "IGY", "IKJ", "DSN", "ICE")
ALLOWED_TYPES = {
    "copy": {"copybook", "cobol_fragment", "sql"},
    "sql_include": {"copybook", "cobol_fragment", "sql"},
    "call": {"cobol_program", "assembler", "pli"},
    "cics_link": {"cobol_program", "assembler", "pli"},
    "cics_xctl": {"cobol_program", "assembler", "pli"},
    "jcl_pgm": {"cobol_program", "assembler", "pli"},
    "jcl_proc": {"jcl_proc"},
    "jcl_include": {"jcl_proc"},
    "cics_map": {"bms_map"},
}
INBOUND_KINDS = {"call", "cics_link", "cics_xctl", "jcl_pgm"}


def link_inventory(files: list[dict]) -> dict:
    """Resolve references and report gaps, entry points, and duplicates."""
    name_table = {}
    for file in files:
        for declared_name in file["declared_names"]:
            name = declared_name.upper()
            name_table.setdefault(name, []).append((file["type"], file["path"]))
    for records in name_table.values():
        records.sort(key=lambda record: record[1])

    gaps_by_name = {}
    inbound_paths = set()
    for file in files:
        for reference in file["references"]:
            name = reference["name"].upper()
            kind = reference["kind"]
            if reference["dynamic"]:
                reference["status"] = "dynamic"
            elif kind == "cics_transid":
                reference["status"] = "external"
            else:
                allowed = ALLOWED_TYPES.get(kind, set())
                matches = [
                    path
                    for file_type, path in name_table.get(name, [])
                    if file_type in allowed
                ]
                if matches:
                    reference["status"] = "resolved"
                    reference["file"] = matches[0]
                    if kind in INBOUND_KINDS and matches[0] != file["path"]:
                        inbound_paths.add(matches[0])
                elif name in SYSTEM_NAMES or name.startswith(SYSTEM_PREFIXES):
                    reference["status"] = "system"
                else:
                    reference["status"] = "gap"
                    gap = gaps_by_name.setdefault(
                        name,
                        {"name": name, "kinds": set(), "referenced_by": []},
                    )
                    gap["kinds"].add(kind)
                    gap["referenced_by"].append(
                        {"file": file["path"], "line": reference["line"]}
                    )

    gaps = [
        {
            "name": gap["name"],
            "kinds": sorted(gap["kinds"]),
            "referenced_by": sorted(
                gap["referenced_by"],
                key=lambda reference: (reference["file"], reference["line"]),
            ),
        }
        for gap in gaps_by_name.values()
    ]
    gaps.sort(key=lambda gap: gap["name"])

    entry_points = []
    for file in files:
        file_type = file["type"]
        declared_name = (
            file["declared_names"][0] if file["declared_names"] else file["path"]
        )
        if file_type == "jcl":
            entry_points.append(
                {
                    "name": declared_name,
                    "path": file["path"],
                    "kind": "jcl_job",
                    "inferred": False,
                }
            )
        elif file_type == "cobol_program" and any(
            reference["kind"] in {"cics_map", "cics_transid"}
            for reference in file["references"]
        ):
            entry_points.append(
                {
                    "name": declared_name,
                    "path": file["path"],
                    "kind": "online",
                    "inferred": True,
                }
            )
        elif (
            file_type in {"cobol_program", "assembler", "pli"}
            and file["path"] not in inbound_paths
        ):
            entry_points.append(
                {
                    "name": declared_name,
                    "path": file["path"],
                    "kind": "root_program",
                    "inferred": True,
                }
            )
    entry_points.sort(key=lambda entry: entry["path"])

    duplicates = _find_duplicates(files)
    return {
        "gaps": gaps,
        "entry_points": entry_points,
        "duplicates": duplicates,
    }


def _find_duplicates(files: list[dict]) -> dict:
    """Find duplicate declarations within types and identical file hashes."""
    declarations = {}
    hashes = {}
    for file in files:
        for name in file["declared_names"]:
            declarations.setdefault((file["type"], name.upper()), set()).add(
                file["path"]
            )
        hashes.setdefault(file["sha256"], set()).add(file["path"])

    duplicate_paths_by_name = {}
    for (_, name), paths in declarations.items():
        if len(paths) >= 2:
            duplicate_paths_by_name.setdefault(name, set()).update(paths)
    duplicate_names = [
        {"name": name, "files": sorted(paths)}
        for name, paths in sorted(duplicate_paths_by_name.items())
    ]
    identical_files = sorted(
        [sorted(paths) for paths in hashes.values() if len(paths) >= 2]
    )
    return {"names": duplicate_names, "identical_files": identical_files}
