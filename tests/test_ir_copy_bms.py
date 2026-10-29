from stages.stage1_inventory.reader import read_file
from stages.stage2_ir.bms_ir import build_bms_ir
from stages.stage2_ir.copybook_ir import build_copybook_ir


def content_for(tmp_path, filename, lines):
    """Write source lines and return their FileContent."""
    path = tmp_path / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    return read_file(str(path))


def test_copybook_data_and_copy_statements(tmp_path):
    """Parse copybook declarations and nested copies."""
    lines = [
        "       01  ACCT-RECORD.",
        "           05  ACCT-NUMBER     PIC X(10).",
        "           05  ACCT-BALANCE    PIC S9(9)V99 COMP-3.",
        "           COPY SUBREC.",
    ]

    result, unparsed = build_copybook_ir(
        content_for(tmp_path, "copybook.cpy", lines),
        "COPYLIB/acctrec.cpy",
        ["ACCTREC"],
    )

    assert unparsed == []
    assert result["id"] == "cpy:ACCTREC"
    assert len(result["data_items"]) == 3
    assert result["copies"] == [{"name": "SUBREC", "line": 4}]
    assert result["declares_table"] is None


def test_copybook_sql_declares_table(tmp_path):
    """Extract a DCLGEN SQL table declaration."""
    content = content_for(
        tmp_path,
        "account.cpy",
        [
            "       EXEC SQL DECLARE ACCOUNT TABLE (",
            "           ACCT_NO CHAR(10) NOT NULL",
            "       ) END-EXEC.",
            "       01 ACCOUNT-RECORD.",
        ],
    )

    result, _ = build_copybook_ir(content, "account.cpy", ["ACCOUNT"])

    assert result["declares_table"] == "ACCOUNT"


def test_bms_maps_fields_and_map_size(tmp_path):
    """Parse BMS mapset, map dimensions, and field count."""
    content = content_for(
        tmp_path,
        "screen.bms",
        [
            "MAPSET1  DFHMSD TYPE=&SYSPARM,MODE=INOUT,LANG=COBOL",
            "MAP1     DFHMDI SIZE=(24,80)",
            "FIELD1   DFHMDF POS=(1,1),LENGTH=10",
            "         DFHMDF POS=(2,1),LENGTH=5",
            "         DFHMSD TYPE=FINAL",
        ],
    )

    result, unparsed = build_bms_ir(content, "screen.bms", ["MAPSET1"])

    assert unparsed == []
    assert result["id"] == "map:MAPSET1"
    assert result["mapset"] == "MAPSET1"
    assert result["maps"] == [{"name": "MAP1", "size": "24x80", "line": 2}]
    assert result["field_count"] == 2
