from stages.stage1_inventory.reader import read_file
from stages.stage2_ir.jcl_ir import build_jcl_ir


def build(lines, tmp_path, file_type="jcl", declared_names=None):
    """Write JCL lines and return their IR result."""
    path = tmp_path / "job.jcl"
    path.write_text("\n".join(lines), encoding="utf-8")
    return build_jcl_ir(
        read_file(str(path)),
        "job.jcl",
        declared_names or [],
    )


def test_job_steps_dds_and_includes(tmp_path):
    """Parse JCL job steps, data sets, and includes."""
    lines = [
        "//DAILYJOB JOB (ACCT),'DAILY RUN',CLASS=A",
        "//PREPARE  EXEC PGM=IEFBR14",
        "//OLDOUT   DD DSN=BANK.OUT,DISP=(MOD,DELETE)",
        "//MAIN     EXEC PGM=TRANPROC,",
        "//         PARM='PROD'",
        "//INFILE   DD DSN=BANK.TRANS,DISP=SHR",
        "//OUTFILE  DD DSN=BANK.TRANOUT,DISP=(NEW,CATLG)",
        "//         DD DSN=BANK.TRANOUT2,DISP=SHR",
        "//SYSOUT   DD SYSOUT=*",
        "//SYSIN    DD *",
        "//STEP3    EXEC MYPROC",
        "//         INCLUDE MEMBER=INC1",
    ]

    result, unparsed = build(lines, tmp_path)

    assert unparsed == []
    assert result["kind"] == "job"
    assert result["id"] == "job:DAILYJOB"
    assert len(result["steps"]) == 3
    assert result["steps"][0]["exec_kind"] == "pgm"
    assert result["steps"][0]["target"] == "IEFBR14"
    assert result["steps"][0]["dds"][0] == {
        "ddname": "OLDOUT",
        "dsn": "BANK.OUT",
        "disp": "MOD,DELETE",
        "kind": "delete",
        "access": "write",
        "inferred": True,
        "line": 3,
    }
    main = result["steps"][1]
    assert main["target"] == "TRANPROC"
    assert main["parm"] == "PROD"
    assert len(main["dds"]) == 5
    assert main["dds"][0]["kind"] == "input"
    assert main["dds"][1]["kind"] == "new"
    assert main["dds"][2]["ddname"] == "OUTFILE"
    assert main["dds"][2]["kind"] == "concat"
    assert main["dds"][3]["kind"] == "sysout"
    assert main["dds"][4]["kind"] == "inline"
    assert result["steps"][2]["exec_kind"] == "proc"
    assert result["steps"][2]["target"] == "MYPROC"
    assert result["includes"] == [{"member": "INC1", "line": 12}]


def test_proc_statements(tmp_path):
    """Parse a JCL procedure and its data set."""
    result, unparsed = build(
        [
            "//MYPROC   PROC",
            "//STEP1    EXEC PGM=IEFBR14",
            "//DD1      DD DSN=&HLQ..DATA,DISP=SHR",
        ],
        tmp_path,
        "jcl_proc",
        ["MYPROC"],
    )

    assert unparsed == []
    assert result["kind"] == "proc"
    assert result["id"] == "proc:MYPROC"
    assert result["steps"][0]["dds"][0]["dsn"] == "&HLQ..DATA"
    assert result["steps"][0]["dds"][0]["kind"] == "input"


def test_missing_jcl_statements_is_partial(tmp_path):
    """Mark files without JCL statements as partially parsed."""
    _, unparsed = build(["plain text"], tmp_path)

    assert unparsed == [
        {"start": 1, "end": 1, "reason": "no JCL statements"}
    ]
