from stages.stage1_inventory.linker import link_inventory


def make_file(path, file_type, names=None, references=None, sha256=""):
    """Create a small linker input record."""
    return {
        "path": path,
        "type": file_type,
        "declared_names": names or [],
        "references": references or [],
        "sha256": sha256,
    }


def make_reference(kind, name, line=1, dynamic=False):
    """Create a linker reference record."""
    return {"kind": kind, "name": name, "line": line, "dynamic": dynamic}


def test_link_statuses_and_gaps():
    """Resolve references and group unresolved names."""
    program = make_file(
        "A.cbl",
        "cobol_program",
        ["A"],
        [
            make_reference("copy", "ACCTREC", 2),
            make_reference("copy", "SQLCA", 3),
            make_reference("call", "B", 4),
            make_reference("call", "VAR", 5, True),
            make_reference("cics_transid", "CC00", 6),
        ],
    )
    called_program = make_file("B.cbl", "cobol_program", ["B"])

    result = link_inventory([program, called_program])

    assert [reference["status"] for reference in program["references"]] == [
        "gap",
        "system",
        "resolved",
        "dynamic",
        "external",
    ]
    assert program["references"][2]["file"] == "B.cbl"
    assert result["gaps"] == [
        {
            "name": "ACCTREC",
            "kinds": ["copy"],
            "referenced_by": [{"file": "A.cbl", "line": 2}],
        }
    ]


def test_reference_must_resolve_to_an_allowed_type():
    """Do not resolve calls to declarations of the wrong type."""
    caller = make_file(
        "A.cbl",
        "cobol_program",
        ["A"],
        [make_reference("call", "ACCTREC")],
    )
    copybook = make_file("ACCTREC.cpy", "copybook", ["ACCTREC"])

    result = link_inventory([caller, copybook])

    assert caller["references"][0]["status"] == "gap"
    assert result["gaps"][0]["name"] == "ACCTREC"


def test_copy_resolves_to_copybook():
    """Resolve copybook references to matching copybook declarations."""
    caller = make_file(
        "A.cbl",
        "cobol_program",
        ["A"],
        [make_reference("copy", "ACCTREC")],
    )
    copybook = make_file("ACCTREC.cpy", "copybook", ["ACCTREC"])

    link_inventory([caller, copybook])

    assert caller["references"][0]["status"] == "resolved"
    assert caller["references"][0]["file"] == "ACCTREC.cpy"


def test_system_programs_and_prefixes():
    """Treat system names and system prefixes as external references."""
    file = make_file(
        "job.jcl",
        "jcl",
        references=[
            make_reference("jcl_pgm", "IEFBR14"),
            make_reference("call", "DFHUNKNOWN"),
        ],
    )

    link_inventory([file])

    assert [reference["status"] for reference in file["references"]] == [
        "system",
        "system",
    ]


def test_entry_points_and_inbound_jcl_program():
    """Identify JCL jobs, online programs, and root programs."""
    job = make_file(
        "job.jcl",
        "jcl",
        ["DAILY"],
        [make_reference("jcl_pgm", "BATCH")],
    )
    batch = make_file("batch.cbl", "cobol_program", ["BATCH"])
    root = make_file("root.cbl", "cobol_program", ["ROOT"])
    online = make_file(
        "online.cbl",
        "cobol_program",
        ["ONLINE"],
        [make_reference("cics_map", "MAPSET")],
    )

    result = link_inventory([online, root, batch, job])

    assert result["entry_points"] == [
        {"name": "DAILY", "path": "job.jcl", "kind": "jcl_job", "inferred": False},
        {"name": "ONLINE", "path": "online.cbl", "kind": "online", "inferred": True},
        {"name": "ROOT", "path": "root.cbl", "kind": "root_program", "inferred": True},
    ]


def test_self_call_does_not_remove_root_entry_point():
    """Ignore a file's self-reference when finding inbound calls."""
    program = make_file(
        "self.cbl",
        "cobol_program",
        ["SELF"],
        [make_reference("call", "SELF")],
    )

    result = link_inventory([program])

    assert result["entry_points"] == [
        {
            "name": "SELF",
            "path": "self.cbl",
            "kind": "root_program",
            "inferred": True,
        }
    ]


def test_duplicate_declarations_and_identical_hashes():
    """Report same-type declared-name and content duplicates."""
    files = [
        make_file("one.cbl", "cobol_program", ["DUP"], sha256="same"),
        make_file("two.cbl", "cobol_program", ["DUP"], sha256="same"),
        make_file("copy.cpy", "copybook", ["DUP"], sha256="other"),
    ]

    result = link_inventory(files)

    assert result["duplicates"]["names"] == [
        {"name": "DUP", "files": ["one.cbl", "two.cbl"]}
    ]
    assert result["duplicates"]["identical_files"] == [["one.cbl", "two.cbl"]]


def test_different_types_do_not_make_duplicate_names():
    """Only same-type repeated declarations count as name duplicates."""
    files = [
        make_file("job.jcl", "jcl", ["COMMON"]),
        make_file("program.cbl", "cobol_program", ["COMMON"]),
    ]

    result = link_inventory(files)

    assert result["duplicates"]["names"] == []
